"""Negaciones, trámites y denuncias: no crear decisiones desde otra voz."""
import pytest
from app.services.dialogue_evaluation import full_payment_refusal,scan_dialogue,pending_status
from app.services.conversation_evidence import completed_payment
from app.services.contextual_identity_evidence import contextual_holder_confirmation
from app.services.treatment_evidence import mistreatment_reports

@pytest.mark.parametrize('text',[
 'No es que no voy a pagar, voy a pagar cuando consiga trabajo.',
 'Si se vuelve a hacer una compra, ya no voy a pagar nada.',
 'No voy a pagar esta cantidad porque no la debo, voy a pagar lo que debo.',
 'No voy a pagar esos intereses.',
])
def test_partial_conditional_or_negated_refusal_is_not_full_refusal(text):
 assert not full_payment_refusal({'declined':True,'accepted':False,'evidence':text})

@pytest.mark.parametrize('text',['No voy a pagar nada.','No pienso pagar.'])
def test_actual_full_refusal_remains_full_refusal(text):
 assert full_payment_refusal({'declined':True,'accepted':False,'evidence':text})

@pytest.mark.parametrize('text',[
 'Su pago no se ve reflejado. Hasta ahorita no se ha reflejado el pago.',
 '¿Tiene dónde anotar el número de WhatsApp para enviar el comprobante? Ahorita no.',
 'Ese pago se requiere hoy, no se le podría esperar hasta el martes.',
 'Hoy no puedo hablar, estoy trabajando. Mi pago está pendiente.',
])
def test_administrative_negative_does_not_determine_payment_status(text):
 assert pending_status(scan_dialogue(text),{}) is None

@pytest.mark.parametrize('text',[
 'Mi pago está pendiente. Ahorita no tengo dinero.',
 'Necesito hacer el pago. Hoy no lo tengo previsto.',
])
def test_actual_payment_readiness_remains_pending(text):
 assert pending_status(scan_dialogue(text),{})['detected_status']=='NO DEFINE FECHA DE PAGO'

def test_today_payment_instruction_does_not_report_completed_payment():
 assert not completed_payment('La otra opción sería que para el día de hoy realice un pago de mil pesos.')['confirmed']
 assert completed_payment('Ayer realicé un pago de mil pesos.')['confirmed']

def test_self_identified_collections_agent_does_not_confirm_cardholder():
 result=contextual_holder_confirmation('¿Me comunica con Persona Ejemplo? Yo soy de cobranza y necesito que me mande el comprobante de pago.',[],r'me comunica con')
 assert not result['confirmed']

@pytest.mark.parametrize('text',[
 'Ayer me hablaba una persona súper grosera.',
 'Me cortaba la llamada cuando intentaba arreglar mi cuenta.',
 'Ya me tienen inundada de llamadas cuando yo ya pagué.',
])
def test_prior_service_complaint_is_preserved(text):
 assert mistreatment_reports(text,[],[])

@pytest.mark.parametrize('text',[
 'Gestor: Ayer me hablaba una persona súper grosera.',
 'No es cierto que me cortaba la llamada.',
 'Gestor: Ya me tienen inundada de llamadas cuando yo ya pagué.',
])
def test_quoted_denied_or_agent_complaint_is_not_attributed_to_customer(text):
 assert not mistreatment_reports(text,[],[])
