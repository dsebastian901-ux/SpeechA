"""Anonymized financial exchanges from 27/Nov and adversarial variations.

No customer names, account numbers, audio names or complete calls. Decoder
boundary tests are controlled, not evidence of listening to customer audio.
"""
from copy import deepcopy
from datetime import date
import pytest
from app.services.conversation_evidence import payment_commitment
from app.services.negotiation_chronology import validation_terms,payment_purpose,handoffs
from app.services.listening_lifecycle import third_state,primary_fact_conflict
from app.services.accepted_schedule_evidence import accepted_two_part_schedule
from app.services.context_fact_consensus import consensus
from app.services.context_evidence_policy import confirmed_fact
from app.services import context_audio_recovery as C
from test_r66_listening_and_deadlines import REL,PLAN,analysis,CLOSE,collect

# C22: initial uncertainty followed by a validation exchange with date first.
VALIDATION=('Posiblemente entre hoy y mañana. Si me llega el dinero ya lo hago. '
 'La voy a pasar al departamento de convenios. '
 '¿Me confirma fecha para pagar, por favor? Mañana. A más tardar mañana. '
 '¿Qué cantidad va a aplicar, perdón? Cuatro mil ciento once.')
# C01: uncertainty about route after an accepted payment.
ROUTE=('¿Me indica el monto y la fecha de su pago? 900 pesos el día 22 de noviembre. '
       'Igual creo que lo voy a realizar por medio de transferencia por la aplicación.')
# C23: information about cancellation procedure, not a settlement offer.
CANCEL=('Una vez que su cuenta esté en cero, usted revise su estado de cuenta, '
        'si ya permanece en cero, entonces ya puede hacer el trámite de cancelación.')


def attempts(*texts):
    return [{'text':text,'start':10.,'end':30.+i,'beam_size':[5,10,8][i]}for i,text in enumerate(texts)]


def test_real_c22_later_firm_terms_supersede_initial_condition():
    event=validation_terms(VALIDATION)[0]
    c=payment_commitment(VALIDATION)
    assert c['accepted']and not c['conditional']and c['position']==event['position']
    assert event['amount']==4111 and event['date_evidence']=='manana.'
    a=analysis('Habla MRS. Soy yo. '+VALIDATION+CLOSE,dict(REL,saldo_total=8000))
    n=a.metadata['negotiation_validation']
    assert n['monto_detectado']==4111 and n['promise_date']=='2026-11-21'
    assert n['agreement_amount_confirmed']


def test_real_c01_route_uncertainty_does_not_erase_accepted_terms():
    c=payment_commitment(ROUTE)
    assert c['accepted']and not c['conditional']


@pytest.mark.parametrize('tail',[' No me comprometo a pagar.',' Si consigo dinero voy a pagar.'])
def test_later_refusal_or_condition_still_replaces_acceptance(tail):
    assert not payment_commitment(ROUTE+tail)['accepted']


@pytest.mark.parametrize('replacement',[
    'Quizás mañana.', 'No sé si mañana.', 'Mañana o el lunes.',
    'Gestor: Mañana.', 'Mañana si consigo dinero.',
])
def test_validation_does_not_invent_firm_acceptance(replacement):
    assert not validation_terms(VALIDATION.replace('Mañana. A más tardar mañana.',replacement))


@pytest.mark.parametrize('object',['teléfono','comprobante','folio','vencimiento','corte'])
def test_terms_do_not_cross_another_question(object):
    text=VALIDATION.replace('A más tardar mañana.',f'¿Cuál es el {object}?')
    assert not validation_terms(text)


def test_handoff_is_recorded_and_terms_not_joined_between_areas():
    assert len(handoffs(VALIDATION))==1
    changed=VALIDATION.replace('A más tardar mañana.',
        'Le voy a pasar al departamento de convenios.')
    assert not validation_terms(changed)


@pytest.mark.parametrize('text,kind',[
    (CANCEL,'EXPLICACION_TRAMITE_CANCELACION'),
    ('Con este pago liquida la cuenta.','LIQUIDACION'),
    ('Con este pago se pone al corriente.','REGULARIZACION'),
    ('Es el pago de su mensualidad.','MENSUALIDAD'),
    ('Le ofrecemos liquidar su cuenta y hacer la cancelación.','LIQUIDACION'),
])
def test_financial_purpose_has_distinct_objects(text,kind):
    assert payment_purpose(text)==kind


def schedule_text(amount=300,reply='Sí, de acuerdo.'):
    return f'No puedo pagar hoy. Confirmamos tres pagos de {amount} pesos los días 21, 22 y 23 de noviembre. '+reply


def test_installment_count_unit_price_dates_and_later_acceptance_are_bound():
    s=accepted_two_part_schedule(schedule_text(),[],date(2026,11,20))
    assert s['confirmed']and s['amounts']==[300]*3 and s['total']==900
    assert [d['date']for d in s['dates']]==['2026-11-21','2026-11-22','2026-11-23']
    a=analysis('Habla MRS. Soy yo. '+schedule_text()+CLOSE)
    assert a.metadata['negotiation_validation']['agreement_amount_confirmed']
    assert a.metadata['negotiation_validation']['total_multipago']==900


@pytest.mark.parametrize('reply',['No puedo pagar.','Sí, si consigo dinero.','Gestor: Sí, de acuerdo.'])
def test_installment_proposal_without_customer_acceptance_is_not_confirmed(reply):
    assert not accepted_two_part_schedule(schedule_text(reply=reply),[],date(2026,11,20))['confirmed']


def test_missing_installment_dates_are_not_filled_in():
    assert not accepted_two_part_schedule(schedule_text().replace('21, 22 y 23','21 y 23'),[],date(2026,11,20))['confirmed']


@pytest.mark.parametrize('amount,expected',[(100,'NO_APROBADO'),(300,None)])
def test_installment_financial_rules_still_run(amount,expected):
    a=analysis('Habla MRS. Soy yo. '+schedule_text(amount)+CLOSE)
    if expected:assert a.metadata['shared_classification']['clasificacion']==expected
    assert not(a.compliance_score<80 and a.metadata['shared_classification']['aprobado'])


@pytest.mark.parametrize('variant,state',[
    ('pending','PENDIENTE'),('failed','FALLIDA'),('empty','INSUFICIENTE'),
    ('conflict','CONTRADICTORIA'),('good','EJECUTADA'),
])
def test_third_lifecycle_distinguishes_execution_and_resolution(variant,state):
    readings=attempts(PLAN,PLAN)
    if variant!='pending':
        readings+=attempts(PLAN)[0:1]
        if variant=='failed':readings[-1]['error']='RuntimeError'
        if variant=='empty':readings[-1]['text']=''
        if variant=='conflict':readings[-1]['text']=PLAN.replace('900','1200')
    assert third_state(True,readings,consensus('financial',readings,REL))==state


def test_matching_terms_do_not_trigger_third_for_punctuation_or_missing_primary_words():
    assert not primary_fact_conflict('financial','No se entiende la respuesta.',attempts(PLAN,PLAN),REL)
    assert not primary_fact_conflict('financial',PLAN.upper(),attempts(PLAN,PLAN),REL)
    assert primary_fact_conflict('financial',PLAN.replace('900','1200'),attempts(PLAN,PLAN),REL)


def test_recovered_installments_enter_same_financial_policy(tmp_path):
    text=schedule_text().replace('No puedo pagar hoy. ','')
    path,data,record,calls=collect(tmp_path,[text]*3)
    a=analysis(data['texto'],path=path,record=record,segments=data['segmentos'])
    n=a.metadata['negotiation_validation']
    assert n['reviewed_payment_plan']and n['montos_multipago']==[300]*3
    assert n['total_multipago']==900 and n['promise_date']=='2026-11-23'
    assert n['source']=='LOCAL_AUDIO_CONTEXT'


def test_window_follows_final_question_response_not_only_initial_refusal():
    from app.services.medium_review_plan import plan_for_item
    text='No puedo pagar hoy. ¿Me indica el monto y la fecha de su pago? 900 pesos el día 22 de noviembre.'
    parts=['No puedo pagar hoy.','¿Me indica el monto y la fecha de su pago?','900 pesos el día 22 de noviembre.']
    data={'texto':text,'duracion_segundos':160,'segmentos':[
        {'texto':v,'inicio':a,'fin':b}for v,a,b in zip(parts,[10,100,110],[15,109,120])]}
    rows=plan_for_item({'result':data,'classification':{'clasificacion':'REVISAR','decision_findings':[
        {'code':'CONVENIO_OUTCOME_CONFLICT','severity':'REVIEW'}]}})
    assert any(r['start']<=100 and r['end']>=120 for r in rows)
    assert all(r['start']>15 for r in rows)


def test_contextual_receipt_is_local_request_and_response_not_a_voice_label():
    from app.services.operational_script_evidence import receipt_request_evidence
    text='Este número es de WhatsApp. ¿Nos puede enviar su comprobante de pago? Sí, de acuerdo.'
    r=receipt_request_evidence(text)
    assert any(e.get('contextual_request_attribution')for e in r['request_evidence'])
    facts=consensus('financial',attempts(text,text),REL)['rules']
    assert next(f for f in facts if f['rule']=='RECEIPT_REQUEST')['state']=='CONFIRMADO'
    assert all(e['speaker_role']=='NO DETERMINADO'for e in r['request_evidence'])


def test_receipt_customer_report_or_agent_thanks_does_not_forge_reception():
    text='Titular: Ya envié el comprobante. Gestor: Gracias por recibir el recado.'
    facts=consensus('callback',attempts(text,text),REL)['rules']
    assert next(f for f in facts if f['rule']=='MESSAGE_RECEIPT')['state']!='CONFIRMADO'


def test_required_unusable_third_does_not_enable_favorable_fact():
    context={'valid':True,'third_listening_insufficient':['financial']}
    assert confirmed_fact(context,'PAYMENT_PLAN')is None


def test_identical_pcm_configuration_is_cached_and_timed(monkeypatch,tmp_path):
    import numpy as np
    from types import SimpleNamespace
    from faster_whisper import audio
    from app.services.whisper_service import WhisperService
    monkeypatch.setattr(audio,'decode_audio',lambda *a,**k:np.zeros(16000*40))
    invocations=[]
    class Decoder:
        def transcribe(self,samples,**kwargs):
            invocations.append(kwargs)
            return iter([SimpleNamespace(text=PLAN,start=0,end=10)]),None
    def collector(path,data,relation,metadata,reader,label,**kwargs):
        a=reader(1.,20.,5);b=reader(1.,20.,5);c=reader(1.,20.,10)
        assert not a['cache_hit']and b['cache_hit']and not c['cache_hit']
        return {'groups':[]}
    monkeypatch.setattr(C,'collect',collector)
    result=WhisperService()._collect_context(tmp_path/'sample.wav',{}, {},{},Decoder(),'Faster-Whisper:medium')
    assert len(invocations)==2
    assert result['stage_seconds']['cache_hits']==1
    assert result['stage_seconds']['decoder_calls']==2
    assert all(result['stage_seconds'][key]>=0 for key in ['audio_decode','inference','lock_wait','context_total'])


def test_final_plan_does_not_consume_a_later_refusal_in_another_window(tmp_path):
    path,data,record,_=collect(tmp_path,[PLAN]*3)
    from app.services.reviewed_payment_plan import confirmed_payment_plan
    context=C.validate(record,data,REL,path)
    context['source_decision_end']=100.
    assert confirmed_payment_plan(context,contact_type='TITULAR',commitment={'declined':True})is None


def test_already_accepted_but_unparsed_terms_can_use_corroborated_complete_plan(tmp_path):
    path,data,record,_=collect(tmp_path,[PLAN]*3)
    from app.services.reviewed_payment_plan import confirmed_payment_plan
    context=C.validate(record,data,REL,path)
    assert confirmed_payment_plan(context,contact_type='TITULAR',commitment={'accepted':True})['amount']==900


def test_earlier_rejection_may_be_superseded_only_by_located_later_terms(tmp_path):
    path,data,record,_=collect(tmp_path,[PLAN]*3)
    from app.services.reviewed_payment_plan import confirmed_payment_plan
    context=C.validate(record,data,REL,path)
    context['source_decision_end']=20.
    assert confirmed_payment_plan(context,contact_type='TITULAR',commitment={'declined':True})['amount']==900


def test_conflicting_original_terms_are_never_outvoted_by_three_favorable_reads(tmp_path):
    path,data,record,_=collect(tmp_path,[PLAN]*3,data={
        'archivo':'sample.wav','texto':PLAN.replace('900','1200'),'duracion_segundos':120,
        'segmentos':[{'inicio':50,'fin':65,'texto':PLAN.replace('900','1200')}]})
    context=C.validate(record,data,REL,path)
    assert context['primary_conflicting_fact_rules']
    assert confirmed_fact(context,'PAYMENT_PLAN')is None


def test_contextual_recado_reception_is_consumed_without_inventing_phone(tmp_path):
    text='¿Le puedo dejar un recado para que se comunique? Sí, dígame, yo le aviso cuando lo vea.'
    fact=next(f for f in consensus('callback',attempts(text,text),REL)['rules']if f['rule']=='MESSAGE_RECEIPT')
    assert fact['state']=='CONFIRMADO'
    assert not any(f['rule']=='CALLBACK'and f['state']=='CONFIRMADO'
                   for f in consensus('callback',attempts(text,text),REL)['rules'])


def test_same_installment_calendar_with_different_punctuation_is_same_fact():
    a=schedule_text().replace('No puedo pagar hoy. ','')
    b=a.replace('21, 22 y 23','21-22-23')
    facts=consensus('financial',attempts(a,b),REL)['rules']
    assert all(f['state']=='CONFIRMADO'for f in facts if f['rule']in{'PAYMENT_PLAN','PAYMENT_DATE'})


def test_real_c22_directed_payment_photo_request_survives_document_asr_typo():
    from app.services.operational_script_evidence import receipt_request_evidence
    text='Por favor, nos va a compartir la fotografía del comprovento de pago para ingresar al sistema.'
    assert receipt_request_evidence(text)['requested']
    for prefix in ['No nos va a compartir','Dice que nos va a compartir','Yo voy a compartir']:
        assert not receipt_request_evidence(text.replace('Por favor, nos va a compartir',prefix))['requested']


def test_medium_focused_opening_is_accepted_by_same_global_window_budget(tmp_path):
    path=tmp_path/'sample.wav';path.write_bytes(b'controlled decoder boundary')
    text='¿Me puede comunicar con Persona Ejemplo? Sí, soy yo. Habla MRS.'
    data={'archivo':path.name,'texto':text,'duracion_segundos':120,
          'segmentos':[{'texto':text,'inicio':0,'fin':30}]}
    meta={'quality_contact_type':'CONTACTO NO DETERMINADO','shared_classification':{
        'clasificacion':'REVISAR','decision_findings':[{'code':'UNIDENTIFIED_CONTACT','severity':'REVIEW'}]}}
    record=C.collect(path,data,REL,meta,lambda *a:{'text':text,'segments':[]},'Faster-Whisper:medium',focused=True)
    assert len(record['groups'])==1
    assert [a['end']for a in record['groups'][0]['attempts']]==[38.,40.]
    assert C.validate(record,data,REL,path)['holder']


def test_new_area_own_terms_replace_previous_area_without_mixing_amounts():
    text=('¿Me indica el monto y la fecha de su pago? 900 pesos el día 22 de noviembre. '
          'Lo voy a pasar al departamento de convenios. '
          '¿Me confirma fecha para pagar? Mañana. ¿Qué cantidad va a aplicar? 1200 pesos.')
    a=analysis('Habla MRS. Soy yo. '+text+CLOSE)
    n=a.metadata['negotiation_validation']
    assert n['monto_detectado']==1200 and n['promise_date']=='2026-11-21'
    assert len(n['handoffs'])==1


def test_phone_review_window_contains_current_dictation_and_reply():
    from app.services.medium_review_plan import plan_for_item
    parts=['¿Este es su teléfono?','Sí.','¿Tiene dónde anotar el número?','Sí, dígame.',
           'Le dicto el teléfono de contacto.','Ya lo tengo, le aviso.']
    times=[(0,5),(5,7),(200,206),(206,210),(210,218),(218,225)]
    data={'texto':' '.join(parts),'duracion_segundos':240,'segmentos':[
        {'texto':v,'inicio':a,'fin':b}for v,(a,b)in zip(parts,times)]}
    plan=plan_for_item({'result':data,'classification':{'clasificacion':'REVISAR','decision_findings':[
        {'code':'CALLBACK_NOT_DELIVERED','severity':'REVIEW'}]}})
    assert any(r['start']<=200 and r['end']>=225 for r in plan)
    assert all(r['start']>7 for r in plan)


def test_executed_diagnostic_third_does_not_invent_an_ordinary_violation(tmp_path):
    from test_second_listening_20261123 import _sample,_metadata
    path,data,relation=_sample(tmp_path)
    values=iter(['Se informa un pago pendiente del mes','Se informa un pago pendiente para mañana',
                 'Se informa un pago pendiente del mes'])
    record=C.collect(path,data,relation,_metadata('PAYMENT_OUTCOME_NOT_CONFIRMED'),
        lambda *a:{'text':next(values),'segments':[]},'small')
    result=C.validate(record,data,relation,path)
    assert result['third_listening_states'][0]['state']=='INSUFICIENTE'
    assert not result['review_required']and not result.get('third_listening_pending')
    assert not result['holder']and result['callback']is None
