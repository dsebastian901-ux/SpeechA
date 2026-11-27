"""Comparación reproducible de fronteras ASR controladas, NO inferencia real.

Ejecutar con el proyecto deseado en PYTHONPATH. No usa audios de clientes,
modelos, red ni credenciales; los bytes WAV son únicamente un identificador
para probar la vinculación de evidencia y nunca pasan a un decodificador.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services import context_audio_recovery as C
from app.services.context_evidence_policy import confirmed_fact
from app.services.context_fact_consensus import consensus
from app.services.context_recovery_report import trace_rows
from app.services.quality_decision import evaluate_quality

REL={'estatus_grabacion':'CONVENIO','asignacion':'1PV','fecha':'2026-11-20',
     'vencimiento':'2026-11-30','corte':'28','pago_minimo':500,'saldo_total':2000}
CLOSE=' Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.'
PLAN='Me indica el monto y la fecha de su pago. Sería el monto es 900, el día 22 de noviembre.'


def analyze(text,path='sample.wav',segments=None,record=None):
    t=TranscriptionModel(Path(path).name,str(path),text,duration_seconds=120,segments=segments or[])
    if record:t.metadata['context_asr_recovery']=record
    return A.analyze_transcription(t,REL)


def run():
    result={'scope':'CONTROLLED_DECODER_BOUNDARIES_NOT_REAL_ASR','asr_output_doubles':True,
            'human_verified':False,'client_data':False,'engine':A.ENGINE_REVISION,'cases':{}}
    d=evaluate_quality({'quality_contact_type':'TITULAR'},79.999,minimum_score=60)
    result['cases']['exact_80_floor']={'classification':d['clasificacion'],'approved':d['aprobado'],'score':d['score']}
    a=analyze('Habla MRS. Soy yo. Le propongo un pago de 900 pesos. '
        '¿Qué día haría el pago? El día 1 de diciembre.'+CLOSE)
    result['cases']['date_without_accepted_amount']={'classification':a.metadata['shared_classification']['clasificacion'],
        'score':a.compliance_score,'status':a.metadata['status_validation']['detected_status']}
    with TemporaryDirectory()as directory:
        path=Path(directory)/'sample.wav';path.write_bytes(b'controlled binding fixture - not decoded')
        text='¿Me puede comunicar con Persona Ejemplo? Sí, soy yo. Habla MRS. Su respuesta no se entiende.'+CLOSE
        segments=[{'inicio':50,'fin':65,'texto':'Su respuesta no se entiende.'}]
        data={'archivo':path.name,'texto':text,'segmentos':segments,'duracion_segundos':120}
        m={'quality_contact_type':'TITULAR','negotiation_validation':{'commitment_evidence':{'evidence':'Su respuesta no se entiende.'}},
           'shared_classification':{'clasificacion':'REVISAR','decision_findings':[
               {'code':'CONVENIO_OUTCOME_CONFLICT','severity':'REVIEW','reasons':['Confirmar respuesta actual']} ]}}
        record=C.collect(path,data,REL,m,lambda *args:{'text':PLAN,'segments':[]},'Faster-Whisper:medium',focused=True)
        a=analyze(text,path,segments,record)
        result['cases']['corroborated_own_plan']={'classification':a.metadata['shared_classification']['clasificacion'],
            'score':a.compliance_score,'status':a.metadata['status_validation']['detected_status'],
            'decoder_calls':sum(len(g['attempts'])for g in record['groups'])}
        receipt='Gestor: Envíe el comprobante de pago por WhatsApp.'
        queue=iter([receipt,receipt,RuntimeError('controlled failed third')])
        def reader(*args):
            value=next(queue)
            if isinstance(value,Exception):raise value
            return {'text':value,'segments':[]}
        record=C.collect(path,data,REL,m,reader,'Faster-Whisper:medium',focused=True)
        c=C.validate(record,data,REL,path)
        result['cases']['required_third_failed']={'favorable_receipt_fact_consumable':bool(confirmed_fact(c,'RECEIPT_REQUEST')),
            'third_pending':bool(c.get('third_listening_pending')),'third_error':record['groups'][0]['attempts'][2].get('error')}
    groups=[];validations=[]
    for text in ['Gestor: Envíe el comprobante de pago por WhatsApp.','Gestor: No es necesario enviar el comprobante.']:
        attempts=[{'text':text,'segments':[],'start':1,'end':10,'beam_size':b}for b in [5,10]]
        groups.append({'purpose':'financial','attempts':attempts});validations.append(consensus('financial',attempts,REL))
    rows=trace_rows({'context_asr_recovery':{'groups':groups},'analytics_metadata':{
        'context_audio_validation':{'present':True,'valid':True,'fact_validations':validations}}})
    states=[r['Estado de evidencia']for r in rows if r['Regla']=='RECEIPT_REQUEST']
    result['cases']['separate_window_trace']={'states':states}
    return result


if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
