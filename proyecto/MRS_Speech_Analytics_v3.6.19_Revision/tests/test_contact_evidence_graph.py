"""Identificación contextual completa, sin convertirla en pago o promesa."""
import pytest
from app.services.contact_evidence_graph import contextual_contact,own_payment_responses
from app.services.conversation_evidence import holder_confirmation,completed_payment,payment_commitment

OPEN='¿Me puede comunicar, por favor, con Laura Ejemplo? Sí. Habla MRS. '
@pytest.mark.parametrize('question,answer',[
 ('¿Ya pudo realizar su pago?','No, aún no he podido.'),
 ('¿Ya pudo efectuar su pago?','No, todavía no lo he podido realizar.'),
 ('¿Podríamos contar con su pago?','No señorita, estoy en el hospital y no tengo dinero.'),
 ('¿Podemos contar con su pago?','Yo les proponía ir abonando dos mil pesos al mes.'),
 ('¿Ya tendrá usted el pago para hoy?','Estoy sin trabajo y no cuento con esa cantidad.'),
 ('¿Puede realizar su pago?','No puedo, estoy enferma y no tengo trabajo.'),
])
def test_nominal_reply_and_personal_financial_response_identify_holder(question,answer):
 text=OPEN+question+' '+answer
 assert own_payment_responses(text)
 assert contextual_contact(text)['confirmed']
 assert holder_confirmation(text)['confirmed']

@pytest.mark.parametrize('answer',[
 'No.', 'Sí.', 'Gracias.', 'Estoy ocupado.',
 'Gestor: No, aún no he podido.',
 'No tengo su reporte de pago en sistema.',
 'No tengo el comprobante de su pago.',
 'Diga que no he podido pagar.',
 'Si pudiera, no tendría que pagar.',
])
def test_isolated_reply_agency_report_and_quotes_do_not_prove_own_account(answer):
 assert not contextual_contact(OPEN+'¿Ya pudo realizar su pago? '+answer)['confirmed']

@pytest.mark.parametrize('marker',[
 'Soy su esposa.', 'No lo conozco.', 'No se encuentra.',
 'Esa persona dejó mi número como referencia.', 'Le paso al titular.',
 '¿Por qué me habla por otra persona?', '¿Le puedo dejar un recado para otra persona? Sí.',
])
def test_third_party_unknown_and_transfer_have_priority(marker):
 assert not contextual_contact(OPEN+marker+' ¿Ya pudo realizar su pago? No, aún no he podido.')['confirmed']

@pytest.mark.parametrize('question',[
 '¿Puede enviar el comprobante de su pago?',
 '¿Sabe si el señor ya realizó su pago?',
 '¿Puede anotar el número para reportar el pago?',
])
def test_response_must_be_to_the_persons_own_payment(question):
 assert not own_payment_responses(question+' No, aún no he podido.')


def test_contextual_identity_does_not_certify_a_completed_payment_or_future_agreement():
 text=OPEN+'¿Ya pudo realizar su pago? No, aún no he podido.'
 assert holder_confirmation(text)['confirmed']
 assert not completed_payment(text)['confirmed']
 assert not payment_commitment(text)['accepted']

@pytest.mark.parametrize('greeting',[
 'Sí, qué tal. Buen día. Mucho gusto.', 'Sí, qué tal. Bueno día. Mucho gusto.',
])
def test_greeting_after_routing_question_requires_personal_account_context(greeting):
 assert not holder_confirmation('¿Me puede comunicar con Laura Ejemplo? '+greeting)['confirmed']

@pytest.mark.parametrize('title',['señorita','señora','señor'])
def test_honorific_without_name_is_not_a_named_identity(title):
 assert not holder_confirmation('¿Me podría comunicar con la '+title+'? Lo hice ayer, el pago de mi tarjeta.')['confirmed']


def test_payment_bank_reference_is_not_third_party_contact():
    from app.services.contact_evidence_graph import nonholder_context
    text='¿Me podría comunicar con la señorita María Pérez? Ella habla. Como referencia son los 16 dígitos de su tarjeta.'
    assert not nonholder_context(text)


def test_explicit_identity_after_asr_preposition_variant():
    from app.services.conversation_evidence import holder_confirmation
    assert holder_confirmation('Me podré a comunicar con la señorita María Pérez. Ella habla.')['confirmed']


def test_payment_instruction_reference_does_not_block_own_account_identity():
    text=OPEN+'Mi tarjeta no la he utilizado. Para pagar use como referencia los 16 dígitos de su tarjeta.'
    assert contextual_contact(text)['confirmed']


def test_absence_confirmed_after_nominal_request_identifies_intermediary():
    from app.services.contact_dialogue_resolution import declared_intermediary
    text='¿Me puede comunicar con la señora Laura Ejemplo? ¿No está en este momento? Correcto. ¿Le puedo dejar un mensaje? Sí.'
    assert declared_intermediary(text)['confirmed']


def test_personal_refusal_to_make_agreement_is_own_financial_context():
    text=OPEN+'¿Podemos realizar un convenio? No puedo hacer algún convenio porque no tengo trabajo.'
    assert contextual_contact(text)['confirmed']


def test_known_family_in_contact_answer_does_not_identify_holder():
    from app.services.contact_dialogue_resolution import contact_dialogue_evidence
    text='¿Conoce usted a la señora Laura Ejemplo? Sí, es mi hermana.'
    assert contact_dialogue_evidence(text)['family']
