"""Escenarios de decisiones sucesivas y cambio de objeto en conversación."""
import pytest
from app.services.conversation_evidence import payment_commitment
from app.services.payment_lifecycle import financial_response_events, payment_decision_events,active_paid_followup

@pytest.mark.parametrize('text,accepted,declined',[
 ('No puedo pagar hoy, voy a pagar mañana, pero no voy a pagar nada.',False,True),
 ('No puedo pagar hoy, no tengo dinero, pero me comprometo a pagar mañana.',True,False),
 ('Voy a pagar hoy, no tengo la cantidad, pero pagaré mañana sin falta.',True,False),
 ('Voy a pagar hoy, pero no voy a estar pagando una cantidad que no reconozco.',False,True),
 ('No voy a pagar hoy, pero si consigo dinero voy a pagar mañana.',False,False),
 ('Si consigo dinero voy a pagar mañana, pero no me comprometo.',False,True),
 ('Voy a pagar mañana, pero si consigo el dinero.',False,False),
 ('No les voy a pagar mañana.',False,True),
])
def test_last_financial_decision_is_preserved_even_inside_one_asr_window(text,accepted,declined):
 result=payment_commitment(text)
 assert result['accepted']is accepted and result['declined']is declined

@pytest.mark.parametrize('offer',[
 'Confirmo su pago de 2000 pesos para mañana.',
 'El banco le requiere un pago de 2000 pesos para el día 12.',
 'Quedamos con su pago de 2000 pesos mañana.',
 'Generamos su convenio por un pago de 2000 pesos mañana.',
])
def test_explicit_confirmation_of_immediately_previous_current_proposal(offer):
 events=financial_response_events(offer+' Sí, está muy bien.')
 assert len(events)==1 and events[0]['accepted']

@pytest.mark.parametrize('text',[
 'Confirmo su pago de 2000 pesos mañana. Sí, pero no puedo confirmarlo.',
 'Confirmo su pago de 2000 pesos mañana. Sí, si consigo el dinero.',
 'Confirmo su pago de 2000 pesos mañana. Gestor: Sí, está muy bien.',
 'Titular: Confirmo su pago de 2000 pesos mañana. Sí, está muy bien.',
 'Usted dijo que confirmo su pago de 2000 pesos mañana. Sí, está muy bien.',
 'Por ejemplo, confirmo su pago de 2000 pesos mañana. Sí, está muy bien.',
 'Ya recibí su pago de 2000 pesos ayer. Sí, está muy bien.',
 'Puede enviar su comprobante del pago de 2000 pesos mañana. Sí, está muy bien.',
 'Confirmo su pago de 2000 pesos mañana. El número de WhatsApp es 5512345678. Sí, está muy bien.',
 'Confirmo su pago de 2000 pesos mañana. ¿Está muy bien?',
 'Confirmo su pago de 2000 pesos mañana. Sí, tomo el teléfono.',
])
def test_document_phone_reported_speech_and_conditions_do_not_create_a_new_agreement(text):
 assert not financial_response_events(text)

def test_prior_payment_report_does_not_override_later_payment_refusal():
 text='Ya pagué 1000 pesos. No voy a pagar lo que no gasté.'
 events=payment_decision_events(text)
 assert not active_paid_followup(events,{'confirmed':True,'evidence':[{'text_start':0,'text_end':8}]})
 assert active_paid_followup(events,{'confirmed':True,'evidence':[{'text_start':80,'text_end':90}]})

@pytest.mark.parametrize('phrase',[
 'Este pago lo puede realizar a más tarde del día 12.',
 'Su pago sería el día 12.',
 'Para el pago de 2000 pesos, confirme día 12.',
])
def test_day_of_current_payment_does_not_need_month_repeated(phrase):
 from app.services.analytics_service import AnalyticsService as A
 assert A._extract_payment_promise_date_details(phrase,'2026-11-09')['date'].isoformat()=='2026-11-12'


def test_bank_due_date_and_cancellation_callback_do_not_replace_agreed_payment_date():
 from app.services.analytics_service import AnalyticsService as A
 text=('Su fecha límite de pago es el día 16, este pago lo puede realizar a más tarde del día 12, '
       'yo le sugiero para que se comunique usted del día 13-14 y ya se vea reflejado su pago. '
       'Sí, está muy bien, entonces realizo el pago.')
 event=financial_response_events(text)[0]
 assert A._extract_payment_promise_date_details(event['date_evidence'],'2026-11-09')['date'].isoformat()=='2026-11-12'


@pytest.mark.parametrize('reply',[
 'Si lo realiza de esta manera, señorita, no le genera intereses.',
 'Sí no, no podría, puedo hasta el día 21.',
 'Sí, pero no podría confirmarlo.',
])
def test_conditional_instruction_or_refusal_is_not_a_payment_acceptance(reply):
 assert not financial_response_events('Confirmo su pago de 2000 pesos mañana. '+reply)


def test_payment_from_other_period_is_not_the_terminal_result_when_current_payment_is_refused():
 from app.services.analytics_service import AnalyticsService as A
 from app.models.transcriptions import TranscriptionModel
 text=('¿Me puede comunicar con Persona Ejemplo? Sí, soy yo. Habla MRS. '
       'Ya pagué 500 pesos el mes pasado. El banco solicita un pago mínimo de 2000 pesos. '
       'No voy a seguir pagando lo que no reconozco. No voy a pagar nada.')
 m=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'ejemplo.ogg','texto':text,
     'duracion_segundos':100,'segmentos':[]}),{'estatus_grabacion':'NEGATIVA DE PAGO',
     'pago_minimo':2000,'saldo_total':5000,'asignacion':'4PV','fecha':'2026-11-09'}).metadata
 assert not m['negotiation_validation']['payment_confirmation_case']
 assert not m['negotiation_validation']['followup_coverage_validation']['applies']
 assert m['status_validation']['detected_status']=='NEGATIVA DE PAGO'


def test_future_hoped_confirmation_is_not_current_commitment():
    from app.services.conversation_evidence import payment_commitment
    text='No tengo para pagar. Llámeme pasado mañana esperando tener noticias y poder decirte sí, lo voy a cubrir.'
    assert not payment_commitment(text)['accepted']


def test_two_payment_recap_binds_both_amounts_and_dates_without_excel():
    from datetime import date
    from app.services.accepted_schedule_evidence import accepted_two_part_schedule
    text='Entonces confirmaría así como te menciono 500 es el 10 y 1956 es el 15. Ajá.'
    result=accepted_two_part_schedule(text,[],date(2026,11,9))
    assert result['confirmed']
    assert result['amounts']==[500,1956]
    assert [d['date']for d in result['dates']]==['2026-11-10','2026-11-15']


import pytest
@pytest.mark.parametrize('suffix', ['Ajá, pero no puedo.', 'Sí, si consigo el dinero.', 'No.', 'Sí. Mejor no, no me comprometo.'])
def test_two_payment_recap_does_not_override_refusal_or_condition(suffix):
    from datetime import date
    from app.services.accepted_schedule_evidence import accepted_two_part_schedule
    text='Confirmaría 500 es el 10 y 1956 es el 15. '+suffix
    assert not accepted_two_part_schedule(text,[],date(2026,11,9))['confirmed']


def test_administrative_unavailability_does_not_cancel_payment_commitment():
    from app.services.conversation_evidence import payment_commitment
    text='Voy a pagar mañana. Hoy no puedo hablar, estoy trabajando.'
    assert payment_commitment(text)['accepted']


def test_past_action_does_not_replace_current_future_date():
    events=payment_decision_events('Lo realizo el viernes. Y lo realizó el día de hoy, se actualiza en cuatro horas.')
    assert not any(e['accepted'] and 'hoy' in e['date_evidence'] for e in events)
