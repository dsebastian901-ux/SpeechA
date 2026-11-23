"""Lote nuevo: reglas, copia única, etiquetas, contadores y reportes."""
import hashlib
import json
from pathlib import Path
from openpyxl import Workbook,load_workbook
from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service
from app.services.corrected_label_export import export_corrected_labels
from tests.test_integrated_operational_policy_r53 import SHORT_AGREEMENT


def test_short_normal_and_corrected_label_are_copied_once_and_reported(tmp_path,monkeypatch):
    texts={'short.wav':SHORT_AGREEMENT,'retag.wav':SHORT_AGREEMENT,
        'rejected.wav':'Habla MRS. Soy su madre. Tiene una deuda de 500 pesos. No le voy a pasar el recado.'}
    original=tmp_path/'original';original.mkdir()
    excel=tmp_path/'accounts.xlsx';w=Workbook();s=w.active;s.title='Relacion_Audios'
    headers=['archivo_original','numero_de_tarjeta','nombre_final','estatus_grabacion','asignacion','fecha','corte','vencimiento','pago_minimo','saldo_total','gestor','supervisor']
    s.append(headers)
    for n,name in enumerate(texts):
        (original/name).write_bytes(b'synthetic audio copy fixture '+name.encode())
        code='TH'if name=='retag.wav'else'PP'if name=='short.wav'else'3EROS'
        s.append([name,'1234567890123456',f'1234567890123456_1PV_352_{code}_PERSONA{n}_MRS_20261115',
            'NO DEFINE FECHA DE PAGO'if code=='TH'else'CONVENIO'if code=='PP'else'MENSAJE CON FAMILIAR',
            '1PV','2026-11-15',23,'2026-11-23',1000,3000,'Persona Ejemplo','Supervisión Ejemplo'])
    w.save(excel);w.close();excel_bytes=excel.read_bytes();called=[]
    def controlled_asr(audio_path,output_directory):
        name=Path(audio_path).name;called.append(name)
        path=Path(output_directory)/(Path(name).stem+'.json');path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'archivo':name,'texto':texts[name],'duracion_segundos':40,'segmentos':[]}),encoding='utf-8')
        return {'ruta_json':str(path)}
    monkeypatch.setattr(whisper_service,'transcribe_audio',controlled_asr)
    b=BatchService();b.set_files([str(original/name)for name in texts]);b.set_relation_excel(excel)
    b.process_all(output_directory=tmp_path/'project/02_Audios/Transcripciones')
    assert len(called)==3 and excel.read_bytes()==excel_bytes
    for item in b.items:
        d=item['classification'];copy=Path(item['classified_audio_path'])
        assert hashlib.sha256(copy.read_bytes()).digest()==hashlib.sha256((original/item['file_name']).read_bytes()).digest()
        if item['file_name']!='rejected.wav':
            assert d['clasificacion']=='APROBADO_DURACION_MENOR'
            assert copy.parent.name=='APROBADAS_DURACION_MENOR'
            assert copy.name.split('_')[3]=='PP'
        else:
            # 23/11: el rechazo del tercero no prueba falta del gestor.
            # Privacidad sin atribución sigue bloqueando aprobación.
            assert d['clasificacion']=='REVISAR' and not d['calidad_aprobada']
            assert item['analytics_metadata']['privacy_validation']['review_required']
            assert item['analytics_metadata']['status_validation']['detected_status']=='SE NIEGAN A TOMAR RECADO'
            assert copy.parent.name=='REVISAR'
    stats=b.get_classification_summary()
    assert stats['aprobadas_duracion_menor']==2 and stats['revisar']==1
    wb=load_workbook(b.last_report_path,data_only=True)
    try:
        rows=[dict(zip(next(wb['RESULTADOS'].values),v))for v in list(wb['RESULTADOS'].values)[1:]]
        corrected=next(r for r in rows if r['Nombre antes de reetiquetar']and r['Código de salida']=='PP')
        assert corrected['Carpeta de etiqueta corregida']=='APROBADAS_DURACION_MENOR'
        assert wb['REVISION_PENDIENTE'].max_row>1
    finally:wb.close()
    # Exportar un checkpoint de lote vuelve a validar; no ejecuta Whisper.
    checkpoint=tmp_path/'saved.json';checkpoint.write_text(json.dumps({'items':b.items},ensure_ascii=False),encoding='utf-8')
    before=len(called)
    exported=export_corrected_labels(checkpoint,original,tmp_path/'exported')
    assert len(called)==before
    root=Path(exported['output_directory'])
    assert len(list((root/'APROBADAS_DURACION_MENOR').glob('*.wav')))==1
