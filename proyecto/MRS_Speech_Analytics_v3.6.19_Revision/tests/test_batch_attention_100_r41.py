"""Lote controlado de 100; valida el flujo, no la precisión acústica de ASR."""
from collections import Counter
import json
from pathlib import Path
import wave

from openpyxl import Workbook, load_workbook

from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service
from app.services.nonpayment_report_service import NonpaymentReportService as N
from test_attention_wait_r41 import PAID


def test_batch_of_100_routes_high_scores_and_generates_both_final_reports(tmp_path, monkeypatch):
    excel = tmp_path / 'cuentas.xlsx'
    book = Workbook()
    sheet = book.active
    sheet.title = 'Relacion_Audios'
    sheet.append(['archivo_original', 'nombre_final', 'estatus_grabacion', 'gestor',
                  'numero_de_tarjeta', 'pago_minimo', 'Campo extra'])
    sources, payloads = [], {}
    for index in range(100):
        name = 'audio_' + chr(97 + index // 26) + chr(97 + index % 26) + '.wav'
        source = tmp_path / 'audios' / name
        source.parent.mkdir(exist_ok=True)
        with wave.open(str(source), 'wb') as audio:
            audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            audio.writeframes(b'\0\0' * 160)
        sources.append(source)
        sheet.append([name, name, 'CONVENIO', 'Gestor de prueba',
                      '0123456789012345', 700, f'original {index}'])
        units = [{'inicio': 0, 'fin': 20, 'texto': PAID}]
        if index % 4 == 1:
            units.append({'inicio': 25, 'fin': 35, 'texto': 'En la llamada anterior me atendieron de mala manera.',
                          'speaker_role': 'TITULAR'})
        if index % 4 == 2:
            units.append({'inicio': 20, 'fin': 25, 'texto': 'Un momento, permítame verificar.',
                          'speaker_role': 'GESTOR'})
        final_start = {0: 50, 1: 50, 2: 90, 3: 85}[index % 4]
        units.append({'inicio': final_start, 'fin': final_start + 5,
                      'texto': 'Gracias por su tiempo. Hasta luego.', 'speaker_role': 'GESTOR'})
        payloads[name] = {'archivo': name, 'texto': ' '.join(u['texto'] for u in units),
                          'segmentos': units, 'duracion_segundos': 150}
    book.save(excel)
    asr_calls = []

    def controlled_asr(audio_path, output_directory):
        source = Path(audio_path)
        output = Path(output_directory) / (source.stem + '.json')
        assert not output.exists(), 'No debe haber transcripciones recuperadas en esta prueba'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payloads[source.name]), encoding='utf-8')
        asr_calls.append(source.name)
        return {'ruta_json': str(output)}

    monkeypatch.setattr(whisper_service, 'transcribe_audio', controlled_asr)
    original_generate = N.generate_report
    companion_calls = []

    def final_companion(items, quality_report):
        assert len(asr_calls) == len(items) == 100
        assert all(i['status'] == 'completado' for i in items)
        companion_calls.append(quality_report)
        return original_generate(items, quality_report)

    monkeypatch.setattr(N, 'generate_report', final_companion)
    batch = BatchService()
    batch.set_files([str(p) for p in sources])
    batch.set_relation_excel(str(excel))
    output = tmp_path / 'project' / '02_Audios' / 'Transcripciones'
    assert len(batch.process_all(output_directory=str(output))) == 100
    assert len(companion_calls) == 1
    assert not batch.nonpayment_report_error
    assert Counter(i['classification']['clasificacion'] for i in batch.items) == {'APROBADO': 25, 'REVISAR': 75}
    for index, item in enumerate(batch.items):
        expected = 'APROBADO' if index % 4 == 0 else 'REVISAR'
        assert item['status'] == 'completado', item.get('message')
        assert item['compliance_score'] >= 80
        assert item['result'] == payloads[item['file_name']], 'Conservar ASR original'
        assert item['classification']['clasificacion'] == expected
        copied = Path(item['classified_audio_path'])
        assert copied.parent.name == ('APROBADOS' if expected == 'APROBADO' else 'REVISAR')
        assert copied.read_bytes() == sources[index].read_bytes()
    checkpoint = json.loads(Path(batch.checkpoint_path).read_text(encoding='utf-8'))
    assert checkpoint['completed'] and len(checkpoint['items']) == 100
    quality = load_workbook(batch.last_report_path, read_only=True, data_only=True)
    try:
        rows = list(quality['RESULTADOS'].values)
        assert len(rows) == 101
        headers = rows[0]
        classifications = Counter(row[headers.index('Clasificación física')] for row in rows[1:])
        assert classifications == {'APROBADO': 25, 'REVISAR': 75}
        assert sum(row[headers.index('Queja de atención/maltrato')] == 'SI' for row in rows[1:]) == 25
        assert sum(str(row[headers.index('Validación espera 65 s')]).startswith('REVISAR') for row in rows[1:]) == 50
    finally:
        quality.close()
    motives = load_workbook(batch.last_nonpayment_report_path, read_only=True, data_only=True)
    try:
        assert motives['DETALLE_LLAMADAS'].max_row == 101
        assert motives['DATOS_EXCEL'].max_row == 101
        assert list(motives['RESUMEN_MOTIVOS'].values)[-1][1] == 100
    finally:
        motives.close()
