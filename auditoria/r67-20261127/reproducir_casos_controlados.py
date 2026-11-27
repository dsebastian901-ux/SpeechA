"""Fronteras controladas, no ASR real. PYTHONPATH=proyecto/... python este.py salida.json."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,sys
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import payment_commitment
from app.services.accepted_schedule_evidence import accepted_two_part_schedule
from app.services import context_audio_recovery as C
from app.models.transcriptions import TranscriptionModel
from datetime import date
REL={'estatus_grabacion':'CONVENIO','asignacion':'1PV','fecha':'2026-11-20','vencimiento':'2026-11-30','corte':'28','pago_minimo':500,'saldo_total':8000}
CLOSE=' Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.'
PLAN='Me indica el monto y la fecha de su pago. Sería el monto es 900, el día 22 de noviembre.'
VALIDATION=('Posiblemente entre hoy y mañana. Si me llega el dinero ya lo hago. La voy a pasar al departamento de convenios. ¿Me confirma fecha para pagar, por favor? Mañana. A más tardar mañana. ¿Qué cantidad va a aplicar, perdón? Cuatro mil ciento once.')
def analyze(text):
 t=TranscriptionModel('synthetic.wav','synthetic.wav',text,duration_seconds=120)
 a=A.analyze_transcription(t,REL);n=a.metadata['negotiation_validation'];return {'classification':a.metadata['shared_classification']['clasificacion'],'score':a.compliance_score,'accepted':n['commitment_evidence']['accepted'],'amount':n.get('monto_detectado'),'date':n.get('promise_date'),'status':a.metadata['status_validation'].get('detected_status')}
def collect(reads):
 with TemporaryDirectory()as d:
  path=Path(d)/'synthetic.wav';path.write_bytes(b'controlled decoder boundary, not real audio')
  data={'archivo':path.name,'texto':'Habla MRS. Soy yo. Su respuesta no se entiende.'+CLOSE,'duracion_segundos':120,'segmentos':[{'texto':'Su respuesta no se entiende.','inicio':50,'fin':65}]}
  meta={'quality_contact_type':'TITULAR','negotiation_validation':{'commitment_evidence':{'evidence':'Su respuesta no se entiende.'}},'shared_classification':{'clasificacion':'REVISAR','decision_findings':[{'code':'CONVENIO_OUTCOME_CONFLICT','severity':'REVIEW'}]}}
  it=iter(reads)
  def reader(*a):
   v=next(it)
   if isinstance(v,Exception):raise v
   return {'text':v,'segments':[]}
  r=C.collect(path,data,REL,meta,reader,'Faster-Whisper:medium',focused=True);v=C.validate(r,data,REL,path)
  return {'attempts':sum(len(g['attempts'])for g in r['groups']),'third_states':v.get('third_listening_states',[]),'pending':v.get('third_listening_pending',[]),'failed':v.get('third_listening_failed',[]),'insufficient':v.get('third_listening_insufficient',[]),'contradictions':v.get('contradictory_fact_rules',[])}
result={'engine':A.ENGINE_REVISION,'scope':'CONTROLLED_DECODER_BOUNDARY_NOT_REAL_ASR_ANONYMIZED_EXCHANGES_AND_VARIATIONS','cases':{}}
result['cases']['C22_date_then_amount_final_acceptance']=analyze('Habla MRS. Soy yo. '+VALIDATION+CLOSE)
result['cases']['later_decline_blocks']=analyze('Habla MRS. Soy yo. '+VALIDATION+' No me comprometo a pagar.'+CLOSE)
result['cases']['equal_installments_complete']=analyze('Habla MRS. Soy yo. No puedo pagar hoy. Confirmamos tres pagos de 300 pesos los días 21, 22 y 23 de noviembre. Sí, de acuerdo.'+CLOSE)
result['cases']['matching_financial_facts']=collect([PLAN]*3)
result['cases']['third_decoder_failure']=collect([PLAN,PLAN.replace('900','1200'),RuntimeError()])
result['cases']['third_empty']=collect([PLAN,PLAN.replace('900','1200'),''])
result['cases']['third_contradiction_not_voted_out']=collect([PLAN,PLAN.replace('900','1200'),PLAN])
print(json.dumps(result,indent=2));Path(sys.argv[1]).write_text(json.dumps(result,indent=2))
