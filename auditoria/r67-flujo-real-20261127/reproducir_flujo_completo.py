"""Full BatchService + Excel + persistence, with explicitly controlled ASR boundary.
Not acoustic verification. Original WAV fixtures contain silence.
"""
from pathlib import Path
import sys,json,hashlib,wave
from openpyxl import Workbook,load_workbook
from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service,WhisperService
from app.services.reviewed_payment_plan import extract_payment_plans
from app.services.context_fact_consensus import consensus
from app.services.conversation_evidence import payment_commitment
from app.services import context_audio_recovery as C
P=Path(sys.argv[1]);P.mkdir(parents=True,exist_ok=False)
REL={'estatus_grabacion':'CONVENIO','asignacion':'1PV','fecha':'2026-11-20','vencimiento':'2026-11-30','corte':28,'pago_minimo':500,'saldo_total':5000}
SCHEDULE='Confirmamos tres pagos de 300 pesos los días 21, 22 y 23 de noviembre. Sí, de acuerdo.'
FINAL='¿Me indica el monto y la fecha de su pago? 1200 pesos el día 22 de noviembre.'
CLOSE=' Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.'
CASES=[('promesa_personal',SCHEDULE+' Me comprometo a pagar 1300 pesos el día 22 de noviembre.'),('parcialidad_modificada',SCHEDULE+' ¿Me indica el monto y la fecha del segundo pago? 1200 pesos el día 22 de noviembre.'),('recapitulacion_posterior',SCHEDULE+' ¿Puede realizar un pago de 1200 pesos mañana? Sí.'),('nuevo_importe',SCHEDULE+' '+FINAL),('nuevo_importe_fuera_plazo',SCHEDULE+' '+FINAL.replace('22 de noviembre','1 de diciembre')),('nuevo_importe_inferior_minimo',SCHEDULE+' '+FINAL.replace('1200','200')),('revocado',SCHEDULE+' No me comprometo a pagar.'),('nuevo_importe_maltrato',SCHEDULE+' '+FINAL+' Me habló una señorita y me trató muy mal.'),('sin_cambio',SCHEDULE),('rechazo_inicial_superado','No puedo pagar hoy. '+FINAL),('medium_resuelve_cierre','¿Me indica el monto y la fecha de su pago? No se entiende la respuesta.'),('medium_contradictorio','¿Me indica el monto y la fecha de su pago? No se entiende la respuesta.')]
CASES.extend([('oferta_incompleta', 'Podemos ofrecer dos pagos por 900 pesos. Me comprometo a pagar 600 pesos mañana.'), ('dos_pagos_coordinados', 'Me comprometo a pagar mil pesos hoy y dos mil pesos mañana.')])
audio=P/'originales';audio.mkdir();out=P/'project/02_Audios/Transcripciones';payloads={};files=[]
w=Workbook();ws=w.active;ws.title='Relacion_Audios';keys=['archivo_original','gestor','supervisor','nombre_final','numero_de_tarjeta',*REL];ws.append(keys)
for index,(key,body)in enumerate(CASES):
 path=audio/(key+'.wav')
 with wave.open(str(path),'wb')as f:f.setparams((1,2,16000,0,'NONE',''));f.writeframes(b'\0\0'*16000*120)
 text='Habla MRS. Soy yo. '+body+CLOSE
 pieces=[s.strip()+'.'for s in text.split('.')if s.strip()];segments=[];cursor=0.
 # Controlled temporal anchors, evenly separated, no acoustic attribution.
 for value in pieces:
  segments.append({'texto':value,'inicio':cursor,'fin':cursor+120./len(pieces)});cursor+=120./len(pieces)
 payloads[path.name]={'archivo':path.name,'ruta_audio':str(path),'texto':text,'duracion_segundos':120,'segmentos':segments}
 row=dict(REL,archivo_original=path.name,gestor='GESTOR DE PRUEBA',supervisor='SUPERVISOR DE PRUEBA',numero_de_tarjeta='0000111122223333',nombre_final=f'0000111122223333_1PV_352_PP_GESTOR_MRS_20261120_{index}')
 ws.append([row[k]for k in keys]);files.append(path)
excel=P/'relacion_sintetica.xlsx';w.save(excel);w.close()
def asr(audio_path,output_directory):
 path=Path(output_directory)/(Path(audio_path).stem+'.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payloads[Path(audio_path).name]),encoding='utf-8');return {'ruta_json':str(path)}
whisper_service.transcribe_audio=asr
# Prevent real decoding of deliberately silent fixtures. The acoustic path is
# separately exercised with full, historical recordings and actual models.
def recover(path,data,relation,metadata):
 if not Path(path).stem.startswith('medium_'):return None
 count=[0]
 def reader(*args):
  count[0]+=1
  value=SCHEDULE+' '+FINAL
  if Path(path).stem=='medium_contradictorio'and count[0]==2:value=value.replace('1200','1500')
  return {'text':value,'segments':[]}
 return C.collect(path,data,relation,metadata,reader,'Faster-Whisper:medium',focused=True)
whisper_service.recover_review_context=recover
WhisperService.has_local_medium_review=property(lambda self:True)
whisper_service.load_model=lambda *a,**k:None
b=BatchService();b.set_files([str(p)for p in files]);b.set_relation_excel(excel);b.process_all(out)
saved=json.loads(Path(b.checkpoint_path).read_text());book=load_workbook(b.last_report_path,read_only=True);values=list(book['RESULTADOS'].values);headers=values[0];rows=[]
for n,i in enumerate(b.items):
 m=i['analytics_metadata'];terms=m.get('negotiation_validation',{});text=i['result']['texto'];relation=i['relation'];facts=extract_payment_plans(text,i['result']['segmentos'],relation)
 row={'case':CASES[n][0],'status':i['status'],'score':i['compliance_score'],'classification':i['classification']['clasificacion'],'amount':terms.get('monto_detectado'),'date':terms.get('promise_date'),'status_detected':m['status_validation'].get('detected_status'),'plan_facts':[p['value']for p in facts],'folder':Path(i['classified_audio_path']).parent.name,'metadata_classification':m['shared_classification']['clasificacion'],'checkpoint_classification':saved['items'][n]['classification']['clasificacion'],'excel_classification':values[n+1][headers.index('Clasificación física')],'source_copy_sha256_equal':hashlib.sha256(files[n].read_bytes()).digest()==hashlib.sha256(Path(i['classified_audio_path']).read_bytes()).digest(),'codes':[f['code']for f in i['classification']['decision_findings']if f['severity']in{'REVIEW','CRITICAL','PENDING_ALERT'}],'reason_matches_canonical':i['classification']['motivo']==m['shared_classification']['motivo'],'recovered_plan':terms.get('reviewed_payment_plan'),'medium_attempts':sum(len(g['attempts'])for g in (i.get('context_asr_recovery')or{}).get('groups',[]))}
 rows.append(row)
book.close();(P/'summary.json').write_text(json.dumps({'scope':'CONTROLLED_ASR_BOUNDARY_FULL_PRODUCT_PIPELINE_NOT_REAL_RECOGNITION','rows':rows,'checkpoint_generated':Path(b.checkpoint_path).is_file(),'quality_excel_generated':True,'nonpayment_excel_generated':Path(b.last_nonpayment_report_path).is_file()},ensure_ascii=False,indent=2));print(json.dumps(rows,ensure_ascii=False,indent=2))
