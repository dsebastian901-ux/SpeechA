"""Objetos de pregunta y decisión: cubrir positivos y límites de seguridad."""
import pytest
from app.services.payment_intent_frames import payment_frames
from app.services.conversation_evidence import payment_commitment,holder_confirmation
from app.services.dialogue_evaluation import pending_status,scan_dialogue
OPEN='¿Me puede comunicar con Laura Ejemplo? Sí. Habla MRS. '

@pytest.mark.parametrize('question,answer',[
 ('¿Confirma su pago hoy?','Sí, ahorita lo hago.'),
 ('¿Cuándo lo estaría abonando?','El día siete.'),
 ('¿Qué día puede realizar su pago?','El viernes.'),
 ('¿En qué fecha estaría haciendo su pago?','Mañana.'),
 ('¿Entonces cuento con su pago?','Sí.'),
 ('¿Qué monto va a realizar y qué día?','1800 el viernes.'),
])
def test_explicit_financial_response_confirms_current_payment(question,answer):
 text='El pago sería de 1800 para el viernes. '+question+' '+answer
 frames=payment_frames(text)
 assert frames and frames[-1]['accepted']
 assert payment_commitment(text)['accepted']

@pytest.mark.parametrize('reply',['Por el momento no, señorita.','No me es posible.','No, no me es posible.','No creo que pueda.','No sé si puedo.'])
def test_negative_or_conditional_reply_is_pending_not_a_firm_commitment(reply):
 text='¿Cuenta con su pago para hoy? '+reply
 assert not payment_commitment(text)['accepted']
 assert pending_status(scan_dialogue(text),payment_commitment(text))

@pytest.mark.parametrize('question,reply',[
 ('¿Qué fecha de corte aparece?','El viernes.'),
 ('¿Qué día tiene su cita en el hospital?','El viernes.'),
 ('¿Puede enviar el comprobante hoy?','Sí, ahorita lo hago.'),
 ('¿Tiene el número de WhatsApp?','Sí, ahorita lo hago.'),
 ('¿Qué día realizó su pago?','El viernes.'),
 ('¿Ya hizo el pago ayer?','Sí.'),
 ('¿Sabe si su mamá puede pagar?','Mañana lo hace.'),
])
def test_administrative_or_past_responses_do_not_create_future_payment(question,reply):
 frames=payment_frames(question+' '+reply)
 assert not any(f['accepted']and not f['history']for f in frames)

@pytest.mark.parametrize('text',[
 'Gestor: ¿Qué día puede realizar su pago? Gestor: El viernes.',
 'Titular: ¿Qué día tengo que pagar? Gestor: El viernes.',
 '¿Qué día puede realizar su pago? El viernes, si consigo dinero.',
 '¿Cuándo hará su pago? El miércoles o jueves.',
 'Dice que ¿cuándo puede pagar? El viernes.',
])
def test_roles_conditions_and_reported_speech_do_not_invent_agreement(text):
 assert not any(f['accepted']for f in payment_frames(text))

@pytest.mark.parametrize('reply',[
 'No tengo su reporte en sistema.', 'No tengo el comprobante de su pago.',
 'No tengo su registro.', 'No he podido validar su pago en sistema.',
])
def test_agency_records_do_not_identify_the_holder(reply):
 assert not holder_confirmation(OPEN+'¿Ya pudo realizar su pago? '+reply)['confirmed']


def test_nominal_context_with_personal_dated_plan_identifies_holder():
 assert holder_confirmation(OPEN+'¿Qué día podría realizar su pago? El viernes.')['confirmed']


def test_single_yes_to_routing_and_payment_question_does_not_invent_holder():
 assert not holder_confirmation(OPEN+'¿Puede realizar su pago? Sí.')['confirmed']


def test_third_party_context_has_priority_even_if_a_payment_date_is_given():
 assert not holder_confirmation(OPEN+'Soy su hermana. ¿Qué día podría realizar su pago? El viernes.')['confirmed']


@pytest.mark.parametrize('question,reply',[
 ('¿Cuándo fue el pago de los tres mil?','El 30, el día 30.'),
 ('¿Qué día fue?','El 30.'),
 ('¿Cuándo le dan su aguinaldo?','El día 16 de diciembre.'),
 ('¿Qué cantidad ha cubierto?','1800 pesos.'),
])
def test_payday_and_prior_payment_date_are_not_future_commitments(question,reply):
 text='El pago sería de 1800. '+question+' '+reply
 assert not any(f['accepted']for f in payment_frames(text))


def test_named_month_in_reply_is_not_replaced_with_current_month():
 frames=payment_frames('¿Qué día puede pagar? El día 16 de diciembre.')
 assert frames[0]['accepted']
 assert frames[0]['day_of_month']is None


def test_personal_payment_ability_is_account_context_even_without_literal_yo():
 text=OPEN+'¿Puede realizar el pago hoy? Sí, hoy lo puedo dejar.'
 assert holder_confirmation(text)['confirmed']

@pytest.mark.parametrize('question,reply',[
 ('¿Cuándo se venció el pago?','El 18.'),
 ('¿Qué día aplicó su pago?','El día de hoy.'),
 ('¿El cliente no realizó el pago como acordamos?','No, señorita, no.'),
 ('¿Ya realizó algún pago?','Sí, no, estamos en pláticas.'),
 ('¿Cuánto es mi pago que requiere ahorita?','El pago es de 300, no sé si usted puede realizarlo.'),
 ('¿Cuánto es el pago que tengo que dar?','El pago es 300, creo que podemos contar con él.'),
 ('¿Pago?','Eh, fui y era noventa y seis creo.'),
 ('¿Puede realizar su pago?','Sí, si me alcanza el dinero.'),
])
def test_past_payment_self_question_and_condition_do_not_create_a_new_decision(question,reply):
 frames=payment_frames(question+' '+reply)
 assert not any(f['accepted']for f in frames)
 if question in ['¿El cliente no realizó el pago como acordamos?','¿Ya realizó algún pago?','¿Pago?']:
  assert not any((f['declined']or f['conditional'])and not f['history']for f in frames)


def test_future_deposit_noun_is_not_mistaken_for_a_past_tense():
 assert payment_frames('¿Qué día puede hacer el depósito? El viernes.')[0]['accepted']
