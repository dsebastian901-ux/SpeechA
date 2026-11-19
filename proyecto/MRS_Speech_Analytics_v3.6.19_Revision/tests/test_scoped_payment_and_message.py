import pytest
from app.services.conversation_evidence import payment_places,assess_recado,payment_commitment
from app.services.message_exchange import exchange_receipts,polite_return_request
from app.services.definitive_rejection import explicit_message_refusal

CAT={'TIENDA':['tienda'],'FARMACIAS':['farmacias del ahorro'],'7ELEVEN':['7-eleven']}
@pytest.mark.parametrize('phrase',[
 'El pago se puede aplicar directamente en tienda o en Farmacias del Ahorro.',
 'Puede hacer su pago en tienda o en Farmacias del Ahorro.',
 'Puedes hacer tu pago en tienda o en Farmacias del Ahorro.',
 'Los pagos los pueden realizar en tienda o en Farmacias del Ahorro.',
 'Para pagar puede acudir a Farmacias del Ahorro o a 7-Eleven.',
 'Anote el número de WhatsApp para mandar su comprobante, el pago se puede aplicar en tienda o en Farmacias del Ahorro.',
 'Puede consultar su aclaración; el pago se puede aplicar en tienda o en Farmacias del Ahorro.',
])
def test_current_payment_destinations_are_scoped_after_real_instruction(phrase):
 assert len(payment_places(phrase,[],CAT))>=2

@pytest.mark.parametrize('phrase',[
 'Yo pagué en Farmacias del Ahorro y en 7-Eleven.',
 'Compré en tienda o en Farmacias del Ahorro.',
 'Me dijeron que puede pagar en tienda o en Farmacias del Ahorro.',
 'No pague en tienda o en Farmacias del Ahorro.',
 'Titular: Puede pagar en tienda o en Farmacias del Ahorro.',
])
def test_prior_payment_purchase_quote_denial_and_customer_do_not_offer_current_places(phrase):
 assert not payment_places(phrase,[],CAT)


def test_purchase_destination_is_not_credited_but_later_explicit_payment_destination_is():
 result=payment_places('Puede pagar en Farmacias del Ahorro, pero comprar en 7-Eleven.',[],CAT)
 assert {e['place']for e in result}=={'FARMACIAS'}


def test_ready_response_is_linked_to_contact_offer_and_real_dictation():
 text=('No se encuentra. Le puedo dejar un número para que nos contacte. Permítame. '
       'Sí, gracias. A ver, dígame. Sí, el número es 5512345678.')
 assert exchange_receipts(text)
 assert assess_recado(text)['acceptance']
 assert polite_return_request(text+' Si se pudiera comunicar conmigo, por favor.')

@pytest.mark.parametrize('text',[
 'Le puedo dejar un número para que nos contacte. Gestor: A ver, dígame. El número es 5512345678.',
 'Le puedo dejar un número para que nos contacte. Gracias por tomar el recado.',
 'Diga que le puedo dejar un número para que nos contacte. A ver, dígame. El número es 5512345678.',
])
def test_agent_instruction_and_thanks_do_not_confirm_receipt(text):
 assert not exchange_receipts(text)

@pytest.mark.parametrize('ending',[
 'No, no, así déjelo.', 'Entonces no me lo deje.',
])
def test_terminal_refusal_of_offered_message_is_a_clear_refusal(ending):
 text='¿Le puedo dejar un recado? Le dejo un número telefónico para que se comunique. '+ending
 assert explicit_message_refusal(text)['confirmed']
 assert not explicit_message_refusal(text+' Sí, le paso el recado.',acceptance=[{'text':'Sí, le paso el recado.'}])['confirmed']


def test_bank_effect_on_remainder_is_not_the_customers_payment_decision():
 assert not payment_commitment('Le ofrecemos liquidar la cuenta; el restante ya no lo pagaría.').get('conditional',False)


import pytest
@pytest.mark.parametrize('text',[
 'Tiene dónde anotar un número de WhatsApp para que pueda mandarme foto de su pago?',
 'Agregue comprobante de su pago y su nombre completo para actualizar la información.',
 'Por favor adjunte su ticket de pago.',
 'Que nos hagan llegar el comprobante de pago.',
])
def test_explicit_receipt_request_conjugations_are_not_ambiguous(text):
 from app.services.operational_script_evidence import receipt_request_evidence
 r=receipt_request_evidence(text)
 assert r['requested'] and not r['review_required']


def test_question_about_habitual_transfer_does_not_dictate_destination():
 from app.services.payment_instruction_validation import transfers_only_reported_or_asked
 assert transfers_only_reported_or_asked('¿Usted hace sus pagos vía transferencia?')


def test_reported_old_transfer_offer_does_not_become_current_instruction():
 from app.services.payment_instruction_validation import future_transfer_discussion
 assert not future_transfer_discussion('Yo le dije que lo puedo hacer por transferencia, pero jamás me dijeron cuándo se refleja.')
 assert future_transfer_discussion('Me dijeron otra cosa, pero ahora puede hacer transferencia por el resto.')
