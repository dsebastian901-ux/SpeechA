"""Respuestas de pago, importes y quejas conservan su objeto de conversación."""
import pytest
from app.services.payment_dialogue_frames import payment_replies
from app.services.conversation_evidence import completed_payment
from app.services.reported_payment_amounts import reported_amounts
from app.services.balance_context_evidence import balance_scope,attached_balance_amount
from app.services.treatment_evidence import mistreatment_reports
from app.services.conversation_evidence import payment_commitment


@pytest.mark.parametrize('reply',['Para mañana.','Para el día de mañana.','Mañana.','El día de mañana sí.'])
def test_choosing_date_in_future_payment_question_is_an_answer(reply):
    text='¿Podemos contar con su pago de 1800 pesos hoy o mañana? '+reply
    events=payment_replies(text)
    assert any(e['accepted']for e in events)


@pytest.mark.parametrize('reply',[
    'Para mañana no.', 'Para mañana creo que sí.', 'Para mañana si consigo el dinero.',
    'Gestor: Para mañana.', 'Para mañana no podría pagar.',
])
def test_condition_refusal_or_agent_answer_does_not_accept_payment(reply):
    events=payment_replies('¿Podemos contar con su pago hoy o mañana? '+reply)
    assert not any(e['accepted']for e in events)


def test_date_of_sending_receipt_is_not_date_of_payment():
    assert not payment_replies('¿Podría enviar el comprobante hoy o mañana? Para mañana.')


def test_past_payment_answer_ya_requires_past_followup_and_keeps_amount():
    text='¿Ya realizó algún pago? Ya, yo también. ¿Cuándo realizó el pago? Ayer. ¿De qué cantidad? 5000 pesos.'
    report=completed_payment(text)
    assert report['confirmed']
    assert reported_amounts(text,report)['total']==5000
    assert not completed_payment('¿Ya realizó algún pago? Ya, mañana lo voy a hacer.')['confirmed']


def test_bare_saldo_number_without_money_determinant_is_not_certified_as_amount():
    text='Presenta un saldo 22, señora, su tarjeta terminación 1234, una cantidad de 9790.'
    start=text.index('22')
    assert balance_scope(text,[],start,start+2)=='CIFRA_SIN_DETERMINANTE_MONETARIO'
    assert attached_balance_amount(text,text.index('9790'))
    other='Su saldo es 9790. Puede pagar una cantidad de 7000.'
    assert not attached_balance_amount(other,other.index('7000'))


@pytest.mark.parametrize('text', ['Su saldo de 22 pesos.', 'Su saldo 22 pesos.','Su saldo es de 22.'])
def test_small_explicit_balance_is_still_checked(text):
    start=text.index('22')
    assert balance_scope(text,[],start,start+2)=='SALDO_ACTUAL_DECLARADO'


@pytest.mark.parametrize('text',[
    'Me comuniqué al banco y me cortaron. Luego marqué y me cortan.',
    'Me comuniqué al banco y la señorita muy grosera me dijo que hiciera como quisiera.',
])
def test_concrete_prior_service_complaints_are_found(text):
    assert mistreatment_reports(text,[],[])


@pytest.mark.parametrize('text',[
    'No es cierto que me comuniqué al banco y me cortaron.',
    'Mi vecino me corta el pelo.',
    'Tengo dudas de los intereses y de la comisión del banco.',
    'Gestor: Me comuniqué al banco y me cortaron.',
])
def test_negations_others_and_bank_fee_questions_do_not_become_service_complaints(text):
    assert not mistreatment_reports(text,[],[])


@pytest.mark.parametrize('text,accepted,declined',[
    ('No puedo pagar hoy, pero voy a pagar el viernes.',True,False),
    ('Voy a pagar mañana, pero no tengo la cantidad.',False,True),
    ('Si consigo dinero, voy a pagar mañana.',False,False),
    ('Voy a pagar mañana, pero si consigo el dinero.',False,False),
    ('No voy a pagar mañana.',False,True),
    ('Claro, sí, pero no lo voy a pagar, imagínese lo que debía.',False,True),
    ('No les voy a pagar mañana.',False,True),
    ('Me comprometo a pagar mañana. No puedo confirmar su pago si no puede tomar nota del WhatsApp.',True,False),
])
def test_payment_decisions_follow_positions_and_their_object_not_first_match_in_long_asr_unit(text,accepted,declined):
    event=payment_commitment(text)
    assert event['accepted']is accepted
    assert event['declined']is declined


def test_affirmative_current_payment_is_not_conditional_si():
    assert payment_commitment('El banco solicita su pago. Sí, hoy lo puedo dejar.')['accepted']
    assert not payment_commitment('El banco solicita su pago. Si hoy lo puedo dejar, les aviso.')['accepted']


@pytest.mark.parametrize('text,expected',[
    ('El banco solicita un pago de 2000 pesos. No puedo hasta el fin de semana.',True),
    ('Le ofrecemos un pago de 2000 pesos. No podría, sinceramente puedo hasta el 21.',True),
    ('Le dictaré el número de WhatsApp. No puedo hasta el fin de semana.',False),
    ('Solicita pago de 2000 pesos. Gestor: No puedo hasta el fin de semana.',False),
    ('El banco solicita pago. Diga que no puedo hasta el 21.',False),
])
def test_explicit_personal_payment_limit_without_asr_question_mark_is_scoped_to_money(text,expected):
    events=[e for e in payment_replies(text)if e['method']=='LIMITACION_PERSONAL_DE_PAGO_CON_PLAZO_EXPLICITO']
    assert bool(events)is expected
