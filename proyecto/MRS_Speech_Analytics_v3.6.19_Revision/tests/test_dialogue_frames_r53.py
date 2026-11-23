import pytest
from app.services.payment_dialogue_frames import payment_replies
from app.services.conversation_evidence import payment_commitment,assess_recado
from app.services.message_dialogue_evidence import existing_callback_confirmation
from app.services.definitive_rejection import explicit_message_refusal
from tests.test_integrated_operational_policy_r53 import analyze,SHORT_AGREEMENT

@pytest.mark.parametrize('text',[
 '¿Podemos confirmar su pago de 1000 pesos para mañana? Sí.',
 'El mínimo es 1000 pesos. ¿Sería hoy o mañana? Mañana a las diez.',
 '¿Contamos con su pago mañana? Sí, lo realizo.',
])
def test_local_reply_accepts_the_payment_object(text):
 assert payment_replies(text)[-1]['accepted']
 assert payment_commitment(text)['accepted']

@pytest.mark.parametrize('text',[
 '¿Puede enviar el comprobante de pago mañana? Sí.',
 '¿Podemos confirmar el número de WhatsApp para el pago? Sí.',
 '¿Ya realizó su pago ayer? Sí.',
 '¿Podemos confirmar su pago para mañana? Gestor: Sí, le ofrecemos ese convenio.',
 'Usted dijo que ¿podemos confirmar su pago para mañana? Sí.',
 'El comprobante se entrega mañana. ¿Sería hoy o mañana? Mañana.',
 '¿Podemos confirmar su pago mañana? ¿De cuánto?',
])
def test_other_objects_quotes_questions_and_agent_do_not_accept_payment(text):
 assert not any(e['accepted']for e in payment_replies(text))

@pytest.mark.parametrize('reply',['No, no puedo pagar.','Yo creo que mañana.','Si consigo el dinero.','Voy a ver cuánto junto.'])
def test_pending_decision_does_not_become_agreement(reply):
 assert not payment_commitment('¿Podemos confirmar su pago de 1000 pesos para mañana? '+reply)['accepted']

@pytest.mark.parametrize('phrase',['No estoy de acuerdo con los intereses que me cobra el banco.',
 'La comisión de la tarjeta es demasiado alta.','No pedí esa tarjeta.',
 'No reconozco esos cargos y quiero una aclaración.'])
def test_bank_disputes_alone_are_not_bad_attention(phrase):
 a=analyze('Habla MRS. Soy yo. '+phrase)
 assert not a.metadata['treatment_validation']['mistreatment_report_evidence']

@pytest.mark.parametrize('phrase',['Su compañero me insultó en la llamada anterior.',
 'Ya pagué y mandé el comprobante, pero me siguen llamando a cada rato.',
 'No me dieron solución y me colgaron la llamada.'])
def test_actual_service_complaints_still_block(phrase):
 a=analyze('Habla MRS. Soy yo. '+phrase)
 assert not a.metadata['shared_classification']['calidad_aprobada']
 assert a.metadata['treatment_validation']['mistreatment_report_evidence']


def test_later_receipt_replaces_temporary_inability_but_not_final_refusal():
 text=('Habla MRS. Soy su hermana. ¿Le puedo dejar un recado? Sí. '
       '¿Tiene donde anotar? No tengo donde anotar. Espere. Ya, dígame. '
       'Dígale que se comunique al teléfono 5512345678. Ya lo anoté, yo le aviso cuando lo vea.')
 r=assess_recado(text)
 assert not explicit_message_refusal(text,acceptance=r['acceptance'])['confirmed']
 a=analyze(text,estatus_grabacion='MENSAJE CON FAMILIAR')
 assert a.metadata['message_workflow_validation']['complete']
 b=analyze(text+' No le voy a pasar el recado.',estatus_grabacion='MENSAJE CON FAMILIAR')
 # 23/11: conservar la revocación del recado y calificar pasos ejecutados.
 assert b.metadata['status_validation']['detected_status']=='SE NIEGAN A TOMAR RECADO'
 assert not b.metadata['message_workflow_validation']['complete']
 assert b.metadata['shared_classification']['clasificacion']=='APROBADO_SIN_ETIQUETAR'


def test_known_contact_must_be_confirmed_by_recipient_not_agent():
 text='Tercero: Soy su hermana.\nGestor: Dígale que se comunique al número de teléfono.\nTercero: Ya tengo ese número, yo le aviso.'
 assert existing_callback_confirmation(text)
 assert not existing_callback_confirmation(text.replace('Tercero: Ya','Gestor: Ya'))


def test_short_and_retagged_has_both_dimensions():
 a=analyze(SHORT_AGREEMENT,seconds=40)
 d=a.metadata['shared_classification']
 assert d['clasificacion']=='APROBADO_DURACION_MENOR'
 assert d['output_label_correction']['valid'] and d['output_label_correction']['corrected_code']=='PP'

@pytest.mark.parametrize('prompt',['¿Usted es Persona Ejemplo?','¿Es usted Persona Ejemplo?','Busco a Persona Ejemplo.','Encuentro a Persona Ejemplo.'])
def test_explicit_personal_identification(prompt):
 from app.services.conversation_evidence import holder_confirmation
 answer='Sí.'if prompt.startswith('¿')else'Con ella habla.'
 assert holder_confirmation(prompt+' '+answer)['confirmed']

@pytest.mark.parametrize('prompt',['¿Es usted mayor de edad?','¿Es usted de MRS?','¿Usted es su familiar?','¿Es usted responsable del pago?'])
def test_non_nominal_yes_does_not_become_holder_identity(prompt):
 from app.services.conversation_evidence import holder_confirmation
 assert not holder_confirmation(prompt+' Sí.')['confirmed']


def test_chosen_alternative_date_is_not_the_first_date_in_offer():
 a=analyze(SHORT_AGREEMENT.replace('¿Podemos confirmar su pago de 1000 pesos para mañana?\nTitular: Sí.',
  'El pago es de 1000 pesos. ¿Sería hoy o mañana?\nTitular: Mañana a las 10.'))
 n=a.metadata['negotiation_validation']
 assert n['monto_detectado']==1000
 assert n['promise_date']=='2026-11-16'


def test_ready_reply_before_actual_dictation_is_reception_without_certifying_digits():
 text=('Habla MRS. Soy su hermano. Le puede mencionar cuando se encuentra su familiar que nos estamos comunicando de MRS. '
       '¿Con qué anota para dejarle un número telefónico? Claro. Sí, dígame. Es el cincuenta y cinco, doce, treinta y cuatro, cincuenta y seis, setenta y ocho. '
       'El horario es de ocho a nueve para llegar a una conciliación de pago.')
 a=analyze(text,estatus_grabacion='MENSAJE CON FAMILIAR')
 assert a.metadata['message_workflow_validation']['complete']
 assert a.metadata['shared_classification']['aprobado']
 assert not analyze(text.replace('Claro. Sí, dígame.','Gestor: Claro. Sí, dígame.'),estatus_grabacion='MENSAJE CON FAMILIAR').metadata['shared_classification']['aprobado']

@pytest.mark.parametrize('phrase',['Le comento que no tengo dónde anotar.','Le comento que hablo de MRS.','Yo le comento que se cobra el saldo.'])
def test_generic_le_comento_statement_is_not_recipient_relay(phrase):
 from app.services.message_workflow import receipt_events
 assert not receipt_events('Le dejo un número telefónico para que se comunique. '+phrase)


def test_received_message_with_incomplete_callback_has_its_actual_pending_reason():
 a=analyze('Habla MRS. Soy su hermana. Le dejo un recado. Dígale que se comunique. Yo le aviso. El número telefónico es 55, 12.',
  estatus_grabacion='MENSAJE CON FAMILIAR')
 m=a.metadata;d=m['shared_classification']
 assert d['clasificacion']=='REVISAR'
 assert m['message_workflow_validation']['recipient_accepted']
 assert any(f['code']=='CALLBACK_NOT_DELIVERED'and 'recepción' in f['reasons'][0]for f in d['decision_findings'])
