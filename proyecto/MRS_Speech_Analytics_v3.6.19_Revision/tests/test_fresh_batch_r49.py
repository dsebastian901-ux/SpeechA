"""Cierre ordinario, carpetas y contadores desde el lote inicial."""
from pathlib import Path
import json,wave
from openpyxl import Workbook,load_workbook
from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service


def test_initial_batch_separates_approved_review_rejection_and_severe_failure(tmp_path,monkeypatch):
    safe='Habla MRS. Soy su hermana. ¿Tiene dónde escribir? Claro, la escucho. El número telefónico es 5551234567. Dígale que se comunique.'
    cases=[('approved',safe,'APROBADO'),
      ('rejected','Habla MRS. Soy su hermana. No quiero recibir el recado.','NO_APROBADO'),
      ('declined_note','Habla MRS. Soy su hermana. Le dejo un número de teléfono. No puedo anotar. Nos comunicamos después.','NO_APROBADO'),
      ('unsafe',safe+' Tiene una deuda de 1500 pesos.','REVISAR'),
      ('severe','Tercero: Soy su hermana.\nGestor: Habla MRS. Tiene una deuda de 1500 pesos.','FALLA_GRAVE')]
    wb=Workbook();ws=wb.active;ws.title='Relacion_Audios';ws.append(['archivo_original','nombre_final','numero_de_tarjeta','estatus_grabacion','gestor','supervisor','asignacion','fecha']);raw={};paths=[]
    for name,text,outcome in cases:
        path=tmp_path/(name+'.wav')
        with wave.open(str(path),'wb')as w:w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*160)
        paths.append(str(path));raw[path.name]={'archivo':path.name,'texto':text,'segmentos':[],'duracion_segundos':130}
        ws.append([path.name,'0000111122223333_C1_352_3EROS_GESTOR_MRS_20261108','0000111122223333','MENSAJE CON FAMILIAR','Gestor ejemplo','Supervisor ejemplo','C1','2026-11-08'])
    excel=tmp_path/'cuentas.xlsx';wb.save(excel);wb.close();original=excel.read_bytes();calls=[]
    def asr(audio_path,output_directory):
        name=Path(audio_path).name;p=Path(output_directory)/(Path(name).stem+'.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(raw[name]));calls.append(name);return{'ruta_json':str(p)}
    monkeypatch.setattr(whisper_service,'transcribe_audio',asr)
    batch=BatchService();batch.set_files(paths);batch.set_relation_excel(excel);batch.process_all(output_directory=tmp_path/'proyecto/02_Audios/Transcripciones')
    assert len(calls)==5 and excel.read_bytes()==original
    for item,(_,_,expected)in zip(batch.items,cases):
        assert item['classification']['clasificacion']==expected,item['classification']
        assert item['result']==raw[item['file_name']]
        assert Path(item['classified_audio_path']).read_bytes()==Path(item['path']).read_bytes()
        if expected=='NO_APROBADO':assert Path(item['classified_audio_path']).parent.name=='NO_APROBADOS'
    stats=batch.get_classification_summary()
    assert stats['aprobados']==1 and stats['revisar']==1 and stats['no_aprobados']==2 and stats['fallas_graves']==1
    wb=load_workbook(batch.last_report_path,data_only=True)
    try:
        assert wb['NO_APROBADOS'].max_row==3
        summary=dict(wb['RESUMEN'].values)
        assert summary['Revisión manual']==1 and summary['No aprobados por incumplimiento confirmado']==2
    finally:wb.close()
    assert Path(batch.last_nonpayment_report_path).is_file()
