import json
import wave
from pathlib import Path

import pytest
from openpyxl import load_workbook, Workbook

from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service


def test_new_audio_batch_generates_nonpayment_report_once_after_all_calls(tmp_path, monkeypatch):
    """ASR controlado; lote, Excel, análisis, copias y exportaciones reales."""
    from app.services.nonpayment_report_service import NonpaymentReportService as N

    sources = [tmp_path / name for name in ('one.wav', 'two.wav')]
    for source in sources:
        with wave.open(str(source), 'wb') as audio:
            audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            audio.writeframes(b'\0\0' * 160)
    excel = tmp_path / 'cuentas.xlsx'
    book = Workbook()
    sheet = book.active
    sheet.title = 'Relacion_Audios'
    sheet.append(['archivo_original', 'gestor', 'supervisor', 'estatus_grabacion',
                  'nombre_final', 'numero_de_tarjeta', 'asignacion', 'Campo operativo extra'])
    for index, source in enumerate(sources):
        sheet.append([source.name, 'Gestor ejemplo', 'Supervisor ejemplo', 'CONVENIO',
                      source.name, f'012345678901234{index}', '1PV', f'original {index}'])
    book.save(excel)
    output = tmp_path / 'project' / '02_Audios' / 'Transcripciones'
    asr_calls = []

    def controlled_asr(audio_path, output_directory):
        source = Path(audio_path)
        path = Path(output_directory) / (source.stem + '.json')
        assert not path.exists(), 'La prueba debe empezar sin transcripción recuperada'
        path.parent.mkdir(parents=True, exist_ok=True)
        text = ('Titular: No tengo dinero.' if source == sources[0]
                else 'Titular: Me quedé sin trabajo.')
        path.write_text(json.dumps({'archivo': source.name, 'texto': text,
                        'duracion_segundos': 60, 'segmentos': []}), encoding='utf-8')
        asr_calls.append(source.name)
        return {'ruta_json': str(path)}

    monkeypatch.setattr(whisper_service, 'transcribe_audio', controlled_asr)
    batch = BatchService()
    batch.set_files([str(p) for p in sources])
    batch.set_relation_excel(str(excel))
    original_generate = N.generate_report
    companion_calls = []

    def final_companion(items, quality_report):
        assert len(asr_calls) == len(items) == 2
        assert all(i['status'] == 'completado' for i in items)
        companion_calls.append(str(quality_report))
        return original_generate(items, quality_report)

    monkeypatch.setattr(N, 'generate_report', final_companion)
    assert len(batch.process_all(output_directory=str(output))) == 2
    assert len(companion_calls) == 1, 'No generar motivos por cada reporte parcial'
    assert all(not i['transcription_recovered'] for i in batch.items)
    assert batch.nonpayment_report_error is None
    assert Path(batch.last_nonpayment_report_path).parent == Path(batch.last_report_path).parent
    checkpoint = json.loads(Path(batch.checkpoint_path).read_text(encoding='utf-8'))
    assert checkpoint['completed']
    assert checkpoint['last_nonpayment_report_path'] == batch.last_nonpayment_report_path
    book = load_workbook(batch.last_nonpayment_report_path, data_only=True)
    try:
        reasons = dict((r[0], r[1]) for r in list(book['RESUMEN_MOTIVOS'].values)[1:-1])
        assert reasons['FALTA_DE_LIQUIDEZ'] == reasons['DESEMPLEO'] == 1
        assert book['DETALLE_LLAMADAS'].max_row == 3
        rows = list(book['DATOS_EXCEL'].values)
        column = rows[0].index('Campo operativo extra')
        assert [r[column] for r in rows[1:]] == ['original 0', 'original 1']
    finally:
        book.close()


@pytest.mark.parametrize("text,expected", [
    ("Habla MRS. Soy su madre. Dígale que se comunique al número de contacto. Le paso el recado.", "APROBADO"),
    ("Habla MRS. Soy su madre. Tiene una deuda de 1500 pesos.", "REVISAR"),
    ("Familiar: Soy su madre.\nGestor: Tiene una deuda de 1500 pesos.", "FALLA_GRAVE"),
    ("Habla MRS. Referencia de pago 1234567890123456.", "REVISAR"),
    ("Habla MRS. Gracias por su tiempo. Mierda.", "REVISAR"),
])
def test_reanalysis_reuses_json_and_preserves_report_and_folders(tmp_path, monkeypatch, text, expected):
    source = tmp_path / "input" / "synthetic.wav"
    source.parent.mkdir()
    with wave.open(str(source), "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\0\0" * 160)
    output = tmp_path / "project" / "02_Audios" / "Transcripciones"
    output.mkdir(parents=True)
    payload = {"archivo": source.name, "ruta_audio": str(source), "texto": text,
               "duracion_segundos": 90, "segmentos": []}
    transcript = output / "synthetic.json"
    transcript.write_text(json.dumps(payload), encoding="utf-8")

    def must_not_transcribe(*args, **kwargs):
        pytest.fail("Una transcripción existente no debe volver a pasar por Whisper")
    monkeypatch.setattr(whisper_service, "transcribe_audio", must_not_transcribe)
    batch = BatchService()
    batch.set_files([str(source)])
    results = batch.process_all(output_directory=str(output))
    assert len(results) == 1, batch.items
    item = batch.items[0]
    assert item["status"] == "completado", item.get("message")
    assert item["transcription_recovered"] is True
    assert item["classification"]["clasificacion"] == expected
    assert Path(item["classified_audio_path"]).exists()
    assert Path(item["classified_audio_path"]).parent.name == ("APROBADOS" if expected == "APROBADO" else expected)
    assert source.read_bytes() == Path(item["classified_audio_path"]).read_bytes()
    assert json.loads(transcript.read_text(encoding="utf-8")) == payload
    checkpoint = json.loads(Path(batch.checkpoint_path).read_text(encoding="utf-8"))
    assert checkpoint["completed"] is True
    assert checkpoint["items"][0]["classification"]["clasificacion"] == expected
    assert batch.last_report_path, item.get("report_error")
    book = load_workbook(batch.last_report_path, read_only=True, data_only=True)
    try:
        found = False
        for sheet in book:
            rows = list(sheet.values)
            for index, row in enumerate(rows):
                if "Clasificación física" in row:
                    column = row.index("Clasificación física")
                    found = any(r[column] == expected for r in rows[index+1:] if len(r)>column)
                    if found:
                        break
            if found:
                break
        assert found, "El Excel debe contener el dictamen físico correcto"
    finally:
        book.close()
    # Un lote ya terminado no reprocesa sus llamadas.
    assert batch.process_all(output_directory=str(output)) == []


def test_excel_recado_with_uncertain_disclosure_cannot_be_approved(tmp_path, monkeypatch):
    source = tmp_path / "synthetic.wav"
    source.write_bytes(b"synthetic copy fixture")
    output = tmp_path / "project" / "02_Audios" / "Transcripciones"
    output.mkdir(parents=True)
    text = ("Habla MRS. Soy su madre. Dígale que se comunique al número de contacto. "
            "Le paso el recado. Tiene una deuda de 1500 pesos.")
    (output/"synthetic.json").write_text(json.dumps({"archivo": source.name, "texto": text,
        "duracion_segundos": 90, "segmentos": []}), encoding="utf-8")
    excel = tmp_path/"relation.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Relacion_Audios"
    sheet.append(["archivo_original", "gestor", "estatus_grabacion", "nombre_final"])
    sheet.append([source.name, "Gestor sintético", "RECADO REF1", "resultado.wav"])
    book.save(excel)
    batch = BatchService()
    batch.set_files([str(source)])
    batch.set_relation_excel(str(excel))
    monkeypatch.setattr(whisper_service, "transcribe_audio", lambda **kw: pytest.fail("No retranscribir"))
    assert len(batch.process_all(output_directory=str(output))) == 1
    item = batch.items[0]
    m = item["analytics_metadata"]
    assert m["status_validation"]["matches"] is True
    assert m["privacy_validation"]["review_required"] is True
    assert item["compliance_score"] >= 80
    assert item["classification"]["clasificacion"] == "REVISAR"
    assert Path(item["classified_audio_path"]).parent.name == "REVISAR"
