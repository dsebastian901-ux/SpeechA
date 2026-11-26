"""Causas compartidas; entradas sintéticas sin audios ni cuentas de clientes."""
import pytest
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel
from app.services.payment_lifecycle import financial_response_events
from app.services.conversation_evidence import payment_commitment
from app.services.treatment_evidence import asset_pressure_evidence
from app.services.context_audio_recovery import needs_recovery,_focused_windows
from app.services.medium_review_plan import plan_for_item
from app.services.balance_context_evidence import callback_dictation_spans


def analyze(text):
    t=TranscriptionModel('sample.wav','sample.wav',text,duration_seconds=120)
    return A.analyze_transcription(t,{'estatus_grabacion':'CONVENIO','asignacion':'1PV',
        'fecha':'2026-11-20','vencimiento':'2026-11-30','pago_minimo':500,'saldo_total':2000}).metadata


@pytest.mark.parametrize('text',[
    'Gestor: Tiene muebles. Puede venderlas o empeñarlas.',
    'Gestor: Los bienes son para remediar los males.',
    'Gestor: La penalización sería otros quinientos pesos más.',
])
def test_asset_risk_keeps_position_and_role_without_declaring_critical(text):
    r=asset_pressure_evidence(text)
    assert r['review_required']
    assert all(e['speaker_role']=='GESTOR'and not e['human_verified']for e in r['evidence'])


@pytest.mark.parametrize('text',[
    'Titular: Son mis cosas y quiero venderlas.',
    'Gestor: No venda sus muebles.',
    'Gestor: No tiene que venderlas.',
    'Gestor: Por ejemplo, si le dijera que venda sus muebles.',
])
def test_own_choices_denials_and_hypotheses_do_not_create_current_coercion(text):
    assert not asset_pressure_evidence(text)['review_required']


def test_prior_report_is_preserved_as_report_without_blame_of_current_agent():
    r=asset_pressure_evidence('Titular: La gestora en la llamada anterior me dijo que venda sus muebles.')
    assert r['review_required']and r['evidence'][0]['scope']=='REPORTE_PREVIO'


def test_combined_own_amount_and_date_answer_is_bound_before_status():
    m=analyze('Habla MRS. Soy yo. Me podría indicar el monto y la fecha de su pago, por favor. '
        'Sería el monto es 900, el día 20 de noviembre. '
        'Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.')
    n=m['negotiation_validation']
    assert n['commitment_confirmed']and n['amount_confirmed']
    assert n['monto_detectado']==900 and n['promise_date']=='2026-11-20'
    assert m['status_validation']['detected_status']=='CONVENIO'


def test_two_immediate_answers_bind_amount_to_replied_day_not_question_alternative():
    m=analyze('Habla MRS. Soy yo. Me notifican que estaría realizando un movimiento de pago. '
        '¿Qué cantidad fue la que estaría aplicando? 900. '
        '¿Estaría aplicando para el día de hoy o mañana? El día de hoy. '
        'Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.')
    assert m['status_validation']['detected_status']=='CONVENIO'
    assert m['negotiation_validation']['promise_date']=='2026-11-20'
    assert m['negotiation_validation']['monto_detectado']==900


@pytest.mark.parametrize('tail',[
    'Gestor: Sería el monto es 900, el día 20 de noviembre.',
    'Titular: Sería el monto es 900, el día 20 de noviembre, si consigo dinero.',
    'Titular: Solo me está leyendo la propuesta, no confirmo pago.',
    'SPEAKER_00: 900, el día 20 de noviembre.',
])
def test_qa_never_accepts_an_operator_quote_condition_or_unassigned_speaker_tag(tail):
    events=financial_response_events('Gestor: Me indica el monto y la fecha de su pago. '+tail)
    assert not any(e['method']=='RESPUESTA_ACTUAL_DE_IMPORTE_Y_FECHA'for e in events)


def test_whatsapp_question_breaks_the_amount_date_pair():
    text=('Me indica la cantidad que estaría aplicando de pago? 900. '
          '¿Tiene WhatsApp? Sí. ¿Qué día aplicaría el pago? Hoy.')
    assert not any(e['method']=='RESPUESTA_ACTUAL_DE_IMPORTE_Y_FECHA'for e in financial_response_events(text))


def test_due_date_question_is_not_the_payment_date():
    text='Me indica la cantidad que estaría aplicando de pago? 900. ¿Qué día vence su tarjeta? El día de hoy.'
    assert not any(e['method']=='RESPUESTA_ACTUAL_DE_IMPORTE_Y_FECHA'for e in financial_response_events(text))


@pytest.mark.parametrize('route',['Creo que lo voy a realizar en la tienda.','No, creo que lo voy a realizar por transferencia.'])
def test_method_uncertainty_does_not_cancel_the_financial_agreement(route):
    c=payment_commitment('¿Puede pagar 900 pesos mañana? Sí. '+route)
    assert c['accepted']and not c.get('conditional')


def test_long_contact_introduction_does_not_turn_phone_chunks_into_money():
    text=('Le voy a dejar un número para que me pueda mandar la foto de su pago, '
          '¿tiene dónde anotar? Sí. 7.22. 2.101. 08.80. Ahí me envía la foto.')
    spans=callback_dictation_spans(text)
    from app.services.conversation_evidence import normalize
    s=normalize(text);at=s.index('08.80')
    assert any(a<=at and at+5<=b for a,b in spans)


def test_payment_amount_after_money_prompt_keeps_its_financial_object():
    text='El monto de su pago, ¿tiene dónde anotar? 2000 pesos.'
    assert not callback_dictation_spans(text)


def test_asset_window_uses_treatment_and_safety_decoder_not_unrelated_finance():
    data={'texto':'Pago 900 pesos. Venda sus muebles.','duracion_segundos':120,
          'segmentos':[{'inicio':0,'fin':10,'texto':'Pago 900 pesos.'},
                       {'inicio':100,'fin':110,'texto':'Venda sus muebles.'}]}
    metadata={'treatment_validation':{'asset_pressure_details':[{'text':'Venda sus muebles.'}]},
        'shared_classification':{'clasificacion':'REVISAR','decision_findings':[
            {'code':'ASSET_COERCION_REVIEW','severity':'REVIEW','reasons':['Confirmar contexto y voz']} ]}}
    rows=plan_for_item({'result':data,'analytics_metadata':metadata})
    assert [(r['start'],r['end'])for r in rows]==[(97.,113.)]
    assert rows[0]['speaker_assignment_required']
    assert 'safety'in needs_recovery(metadata)
    assert all(purpose=='safety'for purpose,_ in _focused_windows(data,metadata))


def test_brief_repair_does_not_detach_the_current_amount_from_its_date():
    m=analyze('Habla MRS. Soy yo. Me notifican que estaría realizando movimiento de pago. '
        '¿Qué cantidad fue la que estaría aplicando? Perdón. 900. '
        '¿Estaría aplicando para el día de hoy o mañana, perdón? El día de hoy. '
        'Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.')
    assert m['status_validation']['detected_status']=='CONVENIO'
    assert m['negotiation_validation']['promise_date']=='2026-11-20'
    assert m['negotiation_validation']['monto_detectado']==900


def test_unicode_expansion_before_contact_keeps_phone_chunks_out_of_money():
    m=analyze('Habla MRS. Soy yo. Le explico… puede pagar en tienda. '
        'Le voy a dejar un número para que me pueda mandar la foto de su pago, '
        '¿tiene dónde anotar? Sí. 7.22. 2.101. 08.80. Ahí me envía la foto.')
    n=m['negotiation_validation']
    assert n['monto_detectado'] is None
    assert not n['amount_confirmed']


@pytest.mark.parametrize('phrase',[
    'Recuerde el comprobante de pago para que pudieras llegar.',
    'Recuerden, recuerda el ticket de pago.',
])
def test_unintelligible_receipt_reminder_is_uncertainty_not_proven_omission(phrase):
    from app.services.operational_script_evidence import receipt_request_evidence
    r=receipt_request_evidence('Gestor: '+phrase)
    assert r['review_required']
    assert not r['requested']


@pytest.mark.parametrize('text',[
    'Titular: Recuerde el comprobante de pago.',
    'Gestor: No recuerde el comprobante de pago.',
    'Gestor: Por ejemplo, si le dijera recuerde el comprobante de pago.',
    'Gestor: Recuerde el comprobante de domicilio.',
])
def test_reminder_pending_requires_current_payment_document_instruction(text):
    from app.services.operational_script_evidence import receipt_request_evidence
    assert not receipt_request_evidence(text)['review_required']


def test_clear_receipt_request_resolves_an_incomplete_reminder():
    from app.services.operational_script_evidence import receipt_request_evidence
    r=receipt_request_evidence('Gestor: Recuerde el comprobante de pago. Envíeme su comprobante por WhatsApp.')
    assert r['requested']and not r['review_required']
