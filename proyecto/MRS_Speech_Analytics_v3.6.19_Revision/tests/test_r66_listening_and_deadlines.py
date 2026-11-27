"""Regresión r66: conversaciones y fronteras ASR sintéticas sin clientes."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from openpyxl import load_workbook
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services import context_audio_recovery as C
from app.services.context_evidence_policy import confirmed_fact
from app.services.context_recovery_report import trace_rows
from app.services.batch_service import BatchService
from app.services.batch_report_service import BatchReportService

REL={'estatus_grabacion':'CONVENIO','asignacion':'1PV','fecha':'2026-11-20',
     'vencimiento':'2026-11-30','corte':'28','pago_minimo':500,'saldo_total':2000}
CLOSE=' Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.'
PLAN='Me indica el monto y la fecha de su pago. Sería el monto es 900, el día 22 de noviembre.'


def analysis(text,relation=None,path='sample.wav',record=None,duration=120,segments=None):
    t=TranscriptionModel(Path(path).name,str(path),text,duration_seconds=duration,segments=segments or[])
    if record:t.metadata['context_asr_recovery']=record
    return A.analyze_transcription(t,relation or REL)


@pytest.mark.parametrize('mora,promise,due,excel',[
    ('1PV','24 de noviembre','2026-11-30','CONVENIO'),
    ('1PV','1 de diciembre','2026-11-30','CONVENIO'),
    ('1PV','1 de diciembre','2026-11-30','NO DEFINE FECHA DE PAGO'),
    ('C4','1 de diciembre','2026-12-10','CONVENIO'),
    ('C4','11 de diciembre','2026-12-10','CONVENIO'),
])
def test_real_engine_keeps_convenio_grave_classification_and_operational_folder(tmp_path,mora,promise,due,excel):
    r=dict(REL,asignacion=mora,vencimiento=due,estatus_grabacion=excel)
    text=f'Habla MRS. Soy yo. Me comprometo a pagar 900 pesos el {promise}.'+CLOSE
    a=analysis(text,r);m=a.metadata;d=m['shared_classification']
    assert m['status_validation']['detected_status']=='CONVENIO'
    assert d['clasificacion']=='FALLA_GRAVE'and not d['aprobado']
    assert d['operational_folder']=='NEGOCIACION_INVALIDA'
    source=tmp_path/'sample.wav';source.write_bytes(b'controlled copy fixture, not decoded')
    item={'path':str(source),'file_name':source.name,'analytics_metadata':m}
    output=Path(BatchService.__new__(BatchService)._copy_classified_audio(item,None,d,tmp_path/'project/Transcripciones'))
    assert output.parent.name=='NEGOCIACION_INVALIDA'
    assert output.read_bytes()==source.read_bytes()
    row=BatchReportService._row_from_item({**item,'relation':r,'classification':d,'compliance_score':a.compliance_score})
    assert row['Clasificación física']=='FALLA_GRAVE'and row['Carpeta operativa']=='NEGOCIACION_INVALIDA'


@pytest.mark.parametrize('day',[20,21,22,23])
def test_payment_within_both_limits_is_not_grave_for_date(day):
    a=analysis(f'Habla MRS. Soy yo. Me comprometo a pagar 900 pesos el día {day} de noviembre.'+CLOSE)
    assert not any(f['code'].startswith('CRITICAL_')for f in a.metadata['shared_classification']['decision_findings'])


def collect(tmp_path,reads,*,data=None):
    path=tmp_path/'sample.wav';path.write_bytes(b'controlled decoder boundary')
    data=data or {'archivo':path.name,'ruta_audio':str(path),'texto':'¿Me puede comunicar con Persona Ejemplo? Sí, soy yo. Habla MRS. Su respuesta no se entiende.'+CLOSE,
        'duracion_segundos':120,'segmentos':[{'inicio':50,'fin':65,'texto':'Su respuesta no se entiende.'}], 'modelo':'small'}
    meta={'quality_contact_type':'TITULAR','negotiation_validation':{'commitment_evidence':{'evidence':'Su respuesta no se entiende.'}},'shared_classification':{'clasificacion':'REVISAR','decision_findings':[
        {'code':'CONVENIO_OUTCOME_CONFLICT','severity':'REVIEW','reasons':['Confirmar aceptación final']} ]}}
    queue=iter(reads);calls=[]
    def reader(a,b,beam):
        calls.append((a,b,beam));v=next(queue)
        if isinstance(v,Exception):raise v
        return {'text':v,'segments':[]}
    record=C.collect(path,data,REL,meta,reader,'Faster-Whisper:medium',focused=True)
    return path,data,record,calls


def test_two_matching_terms_and_third_contrast_resolve_before_scoring(tmp_path):
    path,data,record,calls=collect(tmp_path,[PLAN]*3)
    original=deepcopy(data)
    a=analysis(data['texto'],path=path,record=record,segments=data.get('segmentos'));m=a.metadata
    assert len(calls)==3 and [c[2]for c in calls]==[5,10,8]
    assert m['status_validation']['detected_status']=='CONVENIO'
    assert m['negotiation_validation']['monto_detectado']==900
    assert m['negotiation_validation']['promise_date']=='2026-11-22'
    assert m['negotiation_validation']['source']=='LOCAL_AUDIO_CONTEXT'
    assert m['shared_classification']['aprobado']
    assert data==original and record['human_verified']is False
    assert all(x['text_sha256']==C.digest(x['text'])for x in record['groups'][0]['attempts'])


@pytest.mark.parametrize('third',[PLAN,RuntimeError('local decoder failed')])
def test_real_contradiction_is_not_outvoted_or_hidden_by_error(tmp_path,third):
    changed=PLAN.replace('900','1200')
    path,data,record,calls=collect(tmp_path,[PLAN,changed,third])
    c=C.validate(record,data,REL,path)
    assert len(calls)==3 and c['contradictory_fact_rules']
    assert confirmed_fact(c,'PAYMENT_PLAN')is None
    assert not analysis(data['texto'],path=path,record=record,segments=data.get('segmentos')).metadata['shared_classification']['aprobado']


def test_missing_required_third_never_enables_matching_facts(tmp_path):
    path,data,record,_=collect(tmp_path,[PLAN]*3)
    record['groups'][0]['attempts']=record['groups'][0]['attempts'][:2]
    record['record_sha256']=C.record_digest(record)
    c=C.validate(record,data,REL,path)
    assert c['valid']and c['third_listening_pending']
    assert confirmed_fact(c,'PAYMENT_PLAN')is None
    d=analysis(data['texto'],path=path,record=record,segments=data.get('segmentos')).metadata['shared_classification']
    assert not d['aprobado']and any(f['code']=='CONTEXT_AUDIO_THIRD_REQUIRED'for f in d['decision_findings'])


@pytest.mark.parametrize('suffix',[
    ' No me comprometo a pagar.',
    ' Si consigo dinero lo haré.',
    ' Soy su hermana, ella no está.',
])
def test_source_decline_condition_or_third_party_cannot_be_overridden(tmp_path,suffix):
    path,data,record,_=collect(tmp_path,[PLAN]*3,data={'archivo':'sample.wav','texto':'Habla MRS. Soy yo.'+suffix+CLOSE,
        'duracion_segundos':120,'segmentos':[{'inicio':50,'fin':65,'texto':suffix}]})
    a=analysis(data['texto'],path=path,record=record,segments=data.get('segmentos'))
    assert not a.metadata['negotiation_validation'].get('reviewed_payment_plan')


@pytest.mark.parametrize('tail',[
    'Gestor: Sería el monto es 900, el día 22 de noviembre.',
    'Sería el monto es 900, el día 22 de noviembre, si consigo dinero.',
    'Me están diciendo 900 el día 22 de noviembre.',
])
def test_unilateral_conditional_or_reported_terms_do_not_create_plan(tail):
    from app.services.reviewed_payment_plan import extract_payment_plans
    assert not extract_payment_plans('Me indica el monto y la fecha de su pago. '+tail,relation=REL)


def test_consensus_trace_keeps_each_window_separate():
    from app.services.context_fact_consensus import consensus
    groups=[];valid=[]
    for text in ['Gestor: Envíe su comprobante por WhatsApp.','Gestor: No es necesario enviar el comprobante.']:
        attempts=[{'text':text,'start':1,'end':10,'beam_size':beam}for beam in [5,10]]
        groups.append({'purpose':'financial','attempts':attempts});valid.append(consensus('financial',attempts,REL))
    rows=trace_rows({'context_asr_recovery':{'groups':groups},'analytics_metadata':{
        'context_audio_validation':{'present':True,'valid':True,'fact_validations':valid}}})
    found={r['Grupo de fragmento']:r['Estado de evidencia']for r in rows if r['Regla']=='RECEIPT_REQUEST'}
    assert found=={1:'CONFIRMADO',2:'DESCARTADO_CON_EVIDENCIA'}


def test_date_without_acceptance_of_offered_amount_is_not_confirmed_grave():
    m=analysis('Habla MRS. Soy yo. Le propongo un pago de 900 pesos. '
        '¿Qué día haría el pago? El día 1 de diciembre.'+CLOSE).metadata
    assert not m['negotiation_validation']['agreement_amount_confirmed']
    assert m['shared_classification']['clasificacion']=='REVISAR'
    assert not any(f['severity']=='CRITICAL'for f in m['shared_classification']['decision_findings'])


@pytest.mark.parametrize('amount,day,expected',[(900,'25 de noviembre','FALLA_GRAVE'),
                                               (900,'1 de diciembre','FALLA_GRAVE'),
                                               (300,'22 de noviembre','NO_APROBADO')])
def test_recovered_plan_still_passes_through_financial_and_date_rules(tmp_path,amount,day,expected):
    text=f'Me indica el monto y la fecha de su pago. Sería el monto es {amount}, el día {day}.'
    path,data,record,_=collect(tmp_path,[text]*3)
    d=analysis(data['texto'],path=path,record=record,segments=data['segmentos']).metadata['shared_classification']
    assert d['clasificacion']==expected and not d['aprobado']
    if expected=='FALLA_GRAVE':assert d['operational_folder']=='NEGOCIACION_INVALIDA'


def test_recovered_plan_does_not_approve_a_score_under_80(tmp_path):
    path,data,_,_=collect(tmp_path,[PLAN]*3)
    data['texto']='¿Me puede comunicar con Persona Ejemplo? Sí, soy yo. Habla MRS. Su respuesta no se entiende.'
    path,data,record,_=collect(tmp_path,[PLAN]*3,data=data)
    a=analysis(data['texto'],path=path,record=record,segments=data['segmentos'])
    assert a.compliance_score==70 and not a.metadata['shared_classification']['aprobado']


def test_failed_or_unavailable_third_keeps_its_reason_and_error(tmp_path):
    path,data,record,calls=collect(tmp_path,[PLAN,PLAN,RuntimeError('controlled decoder failure')])
    g=record['groups'][0]
    assert g['third_read_required']and g['third_read_reason']
    assert g['attempts'][2]['error']=='RuntimeError'
    assert C.validate(record,data,REL,path)['third_listening_pending']


def test_excel_and_checkpoint_keep_each_reading_and_date_folder(tmp_path):
    path,data,record,_=collect(tmp_path,[PLAN]*3)
    a=analysis(data['texto'],path=path,record=record,segments=data['segmentos'])
    item={'file_name':path.name,'result':data,'relation':REL,'context_asr_recovery':record,
          'analytics_metadata':a.metadata,'classification':a.metadata['shared_classification'],
          'compliance_score':a.compliance_score,'status':'completado'}
    checkpoint=tmp_path/'checkpoint.json';checkpoint.write_text(json.dumps({'items':[item]},default=str))
    restored=json.loads(checkpoint.read_text())['items'][0]['context_asr_recovery']
    assert restored==record
    report=BatchReportService.generate_report([item],tmp_path/'output/Transcripciones')
    b=load_workbook(report,read_only=True);sheet=b['EVIDENCIA_RELECTURAS']
    headers=[c.value for c in next(sheet.rows)];rows=list(sheet.values)[1:]
    assert {r[headers.index('Lectura')]for r in rows}=={1,2,3}
    assert all(r[headers.index('Modelo')]=='Faster-Whisper:medium'for r in rows)
    assert all(r[headers.index('Texto')]for r in rows)
    assert 'Motivo tercera escucha'in headers
    assert 'Carpeta operativa'in [c.value for c in next(b['RESULTADOS'].rows)]
    b.close()


@pytest.mark.parametrize('middle',[
    'No me comprometo a pagar, no tengo esa cantidad.',
    'Lo voy a intentar si consigo dinero para el pago.',
])
def test_third_favorable_read_cannot_vote_out_a_real_decline_or_condition(tmp_path,middle):
    path,data,record,calls=collect(tmp_path,[PLAN,middle,PLAN])
    c=C.validate(record,data,REL,path)
    assert len(calls)==3 and 'PAYMENT_PLAN'in c['contradictory_fact_rules']
    assert confirmed_fact(c,'PAYMENT_PLAN')is None
    assert not analysis(data['texto'],path=path,record=record,segments=data['segmentos']).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('score',[0,70,79,79.99,79.995,79.999])
def test_exact_80_floor_is_not_bypassed_by_rounding_or_lower_requested_threshold(score):
    from app.services.quality_decision import evaluate_quality
    d=evaluate_quality({'quality_contact_type':'TITULAR'},score,minimum_score=60)
    assert not d['aprobado']and not d['cumple_puntaje']and d['puntaje_minimo']==80


def test_unconfirmed_but_conflicting_amounts_still_require_a_third_read():
    a=[{'text':'El pago es 900. No entiendo el resto de la respuesta.'},
       {'text':'El pago es 1200. No entiendo el resto de la respuesta.'}]
    assert C.needs_third_read('financial',a)


def test_confirmed_critical_date_does_not_hide_independent_acoustic_alerts():
    meta={'shared_classification':{'clasificacion':'FALLA_GRAVE','pending_alerts':[
        {'code':'ASSET_COERCION_REVIEW','severity':'PENDING_ALERT'}]}}
    assert 'safety'in C.needs_recovery(meta)


def test_consumed_plan_is_reported_as_corroborated_instead_of_no_consensus(tmp_path):
    path,data,record,_=collect(tmp_path,[PLAN]*3)
    a=analysis(data['texto'],path=path,record=record,segments=data['segmentos'])
    outcomes=a.metadata['context_audio_validation']['outcomes']
    assert any(o['result']=='PLAN_DE_PAGO_CORROBORADO'for o in outcomes)


def test_later_unusable_financial_window_cannot_be_ignored_for_approval(tmp_path):
    path,data,record,_=collect(tmp_path,[PLAN]*3)
    record['groups'].append({'purpose':'financial','primary_text':'','attempts':[
        {'text':'','segments':[],'start':80,'end':90,'beam_size':5},
        {'text':'','segments':[],'start':78,'end':92,'beam_size':10}]})
    record['record_sha256']=C.record_digest(record)
    a=analysis(data['texto'],path=path,record=record,segments=data['segmentos'])
    assert not a.metadata['negotiation_validation'].get('reviewed_payment_plan')
    assert not a.metadata['shared_classification']['aprobado']


def test_executed_pending_alert_is_not_reported_as_unexecuted(tmp_path):
    from app.services.medium_review_plan import execution_for_window
    path=tmp_path/'sample.wav';path.write_bytes(b'controlled decoder boundary')
    data={'archivo':path.name,'texto':'Respuesta pendiente.','duracion_segundos':12,'segmentos':[]}
    finding={'code':'UNIDENTIFIED_CONTACT','severity':'PENDING_ALERT','reasons':['Confirmar voz']}
    meta={'shared_classification':{'clasificacion':'NO_APROBADO','pending_alerts':[finding],'decision_findings':[finding]}}
    record=C.collect(path,data,REL,meta,lambda *args:{'text':'No está la titular, soy su hermana.','segments':[]},'Faster-Whisper:medium',focused=True)
    context=C.validate(record,data,REL,path)
    assert context['valid']and record['required_findings']==['UNIDENTIFIED_CONTACT']
    item={'result':data,'relation':REL,'context_asr_recovery':record,'analytics_metadata':{'context_audio_validation':context}}
    assert execution_for_window(item,'UNIDENTIFIED_CONTACT',0,12)=='MEDIUM_EJECUTADO_REGISTRO_VALIDADO'


@pytest.mark.parametrize('extra',[
    ' Con ese pago queda liquidada su cuenta.',
    ' Deposite en la cuenta personal del gestor.',
    ' La referencia de 16 dígitos es 1234567890123456.',
    ' En la llamada anterior me trataron mal.',
    ' No es necesario enviar el comprobante.',
])
def test_secondary_context_cannot_be_whitened_by_a_favorable_plan(tmp_path,extra):
    path,data,record,_=collect(tmp_path,[PLAN+extra]*3)
    a=analysis(data['texto'],path=path,record=record,segments=data['segmentos'])
    assert not a.metadata['shared_classification']['aprobado']
    assert any(r['type']=='SUPPLEMENTAL_FINANCIAL_RISK'for r in a.metadata['context_audio_validation']['risks'])
    assert any(f['code']=='CONTEXT_AUDIO_FINANCIAL_RISK'for f in a.metadata['shared_classification']['decision_findings'])


@pytest.mark.parametrize('prefix,expected',[('Gestor: ',True),('',False),('Titular: ',False)])
def test_settlement_result_state_requires_agent_attribution(prefix,expected):
    text='Habla MRS. Soy yo. '+prefix+'Con ese pago queda liquidada su cuenta.'
    m=analysis(text).metadata
    assert bool(m['negotiation_validation']['liquidation_detected']) is expected


@pytest.mark.parametrize('extra',[
    ' Con ese pago no queda liquidada su cuenta.',
    ' Me había dicho que con ese pago queda liquidada su cuenta.',
])
def test_negated_or_historical_settlement_is_not_a_new_prohibited_offer(tmp_path,extra):
    path,data,record,_=collect(tmp_path,[PLAN+extra]*3)
    a=analysis(data['texto'],path=path,record=record,segments=data['segmentos'])
    assert a.metadata['shared_classification']['aprobado']
    assert not a.metadata['context_audio_validation']['risks']
