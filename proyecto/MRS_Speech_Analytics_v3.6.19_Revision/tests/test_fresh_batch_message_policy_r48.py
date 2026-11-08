"""Recados y ARCO en lote nuevo: ASR controlado, aplicación y reportes reales."""
import json
from pathlib import Path
import wave
from collections import Counter
from openpyxl import Workbook,load_workbook

from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service
from app.config.release import APP_VERSION

CARD='0000111122223333'
RELAY=('Habla MRS. Soy su hermana. ¿Lo puede anotar? Sí. '
       'El número es 5551234567. Dígale que se comunique con nosotros por su saldo vencido.')
ARCO=('Gestor: Habla MRS. ¿Conoce al titular?\n'
      'Tercero: No lo conozco.\n'
      'Gestor: ¿Cuánto tiempo tiene con este número?\n'
      'Tercero: Más de ocho años.\n'
      'Gestor: El correo es privacidad uno arroba bradesco. Punto com. Sí. Punto mx. '
      'Escriba deseo mi derecho. ARCO. Y sea borrado mi número de su base de datos. '
      'Adjunte su INE y comprobante de la línea.')


def test_new_batch_applies_message_policy_and_safety_before_any_reanalysis(tmp_path,monkeypatch):
    cases=[
        ('generic','MENSAJE CON FAMILIAR',RELAY,'APROBADO'),
        ('amount','MENSAJE CON FAMILIAR',RELAY.replace('saldo vencido.','saldo vencido de 1500 pesos.'),'REVISAR'),
        ('confirmed','MENSAJE CON FAMILIAR','Tercero: Soy su hermana.\nGestor: Habla MRS. Tiene una deuda de 1500 pesos.','FALLA_GRAVE'),
        ('dictation','MENSAJE CON FAMILIAR',RELAY.replace('¿Lo puede anotar?','¿Podría dictarle un número de llamada para que se comunique con nosotros?'),'APROBADO'),
        ('noanswer','MENSAJE CON FAMILIAR',RELAY.replace('¿Lo puede anotar? Sí.','Le voy a dictar el número.'),'REVISAR'),
        ('arco','NO CONOCEN A DEUDOR',ARCO,'APROBADO'),
        ('nocallback','MENSAJE CON FAMILIAR','Habla MRS. Soy su hermana. Dígale que se comunique con nosotros. Le dejaré un número telefónico. ¿Tiene dónde anotar? Sí.','REVISAR'),
        ('work','MENSAJE EN TRABAJO',RELAY.replace('Soy su hermana.','¿Es su compañera de trabajo? Sí.'),'APROBADO'),
        ('relabel','MENSAJE CON FAMILIAR',RELAY.replace('Soy su hermana.','Soy su vecina.'),'APROBADO_ETIQUETA_CORREGIDA'),
        ('contactsynonym','MENSAJE CON FAMILIAR',RELAY.replace('se comunique','se contacte'),'APROBADO'),
        ('concretemora','MENSAJE CON FAMILIAR',RELAY.replace('saldo vencido.','saldo vencido. Tiene ocho mensualidades vencidas.'),'REVISAR'),
        ('arrearsperiod','MENSAJE CON FAMILIAR',RELAY.replace('saldo vencido.','saldo vencido. Tiene más de un año que no se presenta pago alguno.'),'REVISAR'),
        ('conditionalphone','MENSAJE CON FAMILIAR','Habla MRS. Soy su hermana. Dígale que se comunique. Le dictaría un número. ¿Tiene dónde anotar? Sí. Es cincuenta y cinco.','REVISAR'),
        ('coarseword','MENSAJE CON FAMILIAR',RELAY+' Está cagando.','REVISAR'),
        ('linkedamount','MENSAJE CON FAMILIAR',RELAY+' Para liquidar es por la cantidad de 941 pesos.','REVISAR'),
        ('thirdreports','MENSAJE CON FAMILIAR',RELAY+' Tercero: Mi mamá pagó 941 pesos para liquidar.','APROBADO'),
        ('contactcontradiction','MENSAJE CON FAMILIAR','¿Le conoce? No. '+RELAY,'REVISAR'),
    ]
    wb=Workbook();ws=wb.active;ws.title='Relacion_Audios'
    headers=['archivo_original','gestor','supervisor','nombre_final','numero_de_tarjeta','estatus_grabacion','asignacion','fecha']
    ws.append(headers);paths=[];raw={}
    for key,status,text,expected in cases:
        p=tmp_path/(key+'.wav')
        with wave.open(str(p),'wb') as wav:
            wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\0\0'*160)
        paths.append(p);code='NC'if status=='NO CONOCEN A DEUDOR'else'3EROS'
        ws.append([p.name,'Gestor ejemplo','Supervisor ejemplo',CARD+'_C1_352_'+code+'_GESTOR_MRS_20261108',CARD,status,'C1','2026-11-08'])
        raw[p.name]=dict(archivo=p.name,texto=text,segmentos=[],duracion_segundos=150)
    excel=tmp_path/'cuentas.xlsx';wb.save(excel);wb.close();original_excel=excel.read_bytes()
    out=tmp_path/'nuevo/02_Audios/Transcripciones';calls=[]
    def controlled_asr(audio_path,output_directory):
        name=Path(audio_path).name;p=Path(output_directory)/(Path(name).stem+'.json')
        assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(raw[name]),encoding='utf-8');calls.append(name);return {'ruta_json':str(p)}
    monkeypatch.setattr(whisper_service,'transcribe_audio',controlled_asr)
    batch=BatchService();batch.set_files([str(p)for p in paths]);batch.set_relation_excel(excel)
    assert not out.exists();assert len(batch.process_all(output_directory=out))==len(cases)
    assert len(calls)==len(cases)and not any(i['transcription_recovered']for i in batch.items)
    assert excel.read_bytes()==original_excel
    for item,case in zip(batch.items,cases):
        assert item['status']=='completado',item['message']
        assert item['classification']['clasificacion']==case[-1],(case[0],item['classification'])
        assert item['result']==raw[item['file_name']]
        assert item['analytics_metadata']['engine_revision']==APP_VERSION
        assert item['analytics_metadata']['final_result']==case[-1]
        assert Path(item['classified_audio_path']).read_bytes()==(tmp_path/item['file_name']).read_bytes()
    workbook=load_workbook(batch.last_report_path,data_only=True)
    try:
        rows=list(workbook['RESULTADOS'].values);column=rows[0].index('Clasificación física')
        assert [r[column]for r in rows[1:]]==[c[-1]for c in cases]
        assert workbook['CUENTAS_REETIQUETADAS'].max_row==2
        assert workbook['CONTROL_PROCESAMIENTO'].max_row==len(cases)+1
    finally:workbook.close()
    assert Path(batch.last_nonpayment_report_path).is_file()
    checkpoint=json.loads(Path(batch.checkpoint_path).read_text())
    assert checkpoint['completed']and checkpoint['engine_revision']==APP_VERSION
