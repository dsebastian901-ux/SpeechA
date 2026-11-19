"""Decisiones completas: no cambiar revisión por aprobación sin sus pruebas."""
from copy import deepcopy
import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import holder_confirmation,completed_payment,payment_places
from app.services.reported_payment_amounts import reported_amounts
from app.services.context_rules import prohibited_threat
from app.services.definitive_rejection import definitive_rejection


def analyze(text,**context):
 return A.analyze_transcription(TranscriptionModel('synthetic.ogg','synthetic.ogg',text,duration_seconds=120),context)

@pytest.mark.parametrize('nominal',[
 'Me estoy comunicando con Ana Pérez.',
 'Estoy comunicando con Ana Pérez.',
 '¿Se encontrará Ana Pérez?',
 '¿Se encontraba Ana Pérez?',
 'Con la señorita Ana Pérez, por favor.',
])
def test_nominal_variants_still_require_a_personal_account_response(nominal):
 assert holder_confirmation(nominal+' Sí, dígame. Enseguida hago el pago de mi tarjeta.')['confirmed']
 assert not holder_confirmation(nominal+' Sí. Gracias.')['confirmed']
 assert not holder_confirmation(nominal+' Soy su hermana. Voy a pagar mi tarjeta.')['confirmed']
 assert not holder_confirmation('Gestor: '+nominal+' Gestor: Enseguida hago el pago de mi tarjeta.')['confirmed']

@pytest.mark.parametrize('question',[
 '¿Qué cantidad fue lo que pagó el día de ayer?',
 '¿Me podrá dar la cantidad de que pagó?',
])
def test_reported_amount_question_is_bound_to_report_not_bank_balance(question):
 text='Ya pagué, el día de ayer. '+question+' Ah, 477 pesos.'
 assert reported_amounts(text,completed_payment(text))['total']==477
 assert reported_amounts('Su saldo es de 477. '+question+' 477.',{'evidence':[]})['total']is None


def test_asr_puedo_requires_unambiguous_past_followup_and_coverage():
 text='Habla MRS. Soy yo. ¿Ya puedo realizar su pago? Sí, ya el día de ayer. ¿Qué cantidad fue lo que pagó ayer? Ah, 2152 pesos. Envíe su comprobante por WhatsApp.'
 a=analyze(text,estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='473',saldo_total='3000')
 n=a.metadata['negotiation_validation']
 assert n['payment_confirmation_case'] and n['prior_payment_total']==2152
 assert n['prior_payment_covers_minimum']
 assert not n['missing_collection_attempt_penalty']
 assert not completed_payment('¿Ya puedo realizar su pago? Sí, mañana lo hago.')['confirmed']


def test_today_reply_does_not_move_current_payment_to_next_recurring_payday():
 text='Soy yo. Habla MRS. ¿Qué día lo estaría realizando el pago? Hoy, y el domingo voy a empezar con otros pagos cada domingo.'
 a=analyze(text,estatus_grabacion='CONVENIO',pago_minimo='500',saldo_total='3000',fecha='2026-11-02',asignacion='1PV')
 assert a.metadata['negotiation_validation']['promise_date']=='2026-11-02'


def test_current_payment_stores_with_cuento_con_context_are_offers():
 cat={'KIOSKO':['kiosk'],'SIX':['tiendas 6'],'FARMACIA':['farmacias del ahorro']}
 text='¿Dónde puede hacer el pago? No hay bancos. Pero sí puede contar con Kiosk y tiendas 6.'
 assert {e['place']for e in payment_places(text,[],cat)}=={'KIOSKO','SIX'}
 for t in ['Para sus compras puede contar con Kiosk y tiendas 6.',
           'Titular: Para el pago puede contar con Kiosk y tiendas 6.',
           'No puede contar con Kiosk y tiendas 6 para el pago.']:
  assert not payment_places(t,[],cat)


def test_asset_seizure_threat_is_not_a_suggestion_to_sell_property():
 assert prohibited_threat('Sus bienes muebles son lo primero que va a ir a cobrar el banco.',mora='2PV')
 for text in ['Puede vender sus bienes muebles para reunir el pago.',
              'No, sus bienes muebles no son lo primero que va a cobrar el banco.',
              'Titular: Sus bienes muebles son lo primero que va a ir a cobrar el banco.']:
  assert not prohibited_threat(text,mora='2PV')


def test_clear_invalid_accepted_amount_is_rejection_with_other_doubts_retained():
 n={'is_negotiation':True,'valid':False,'amount_invalid':True,'hard_invalid':True,
    'review_required':False,'amount_confirmed':True,'payment_date_confirmed':True,
    'commitment_confirmed':True,'evidencia_monto':'pago de 300 pesos',
    'commitment_evidence':{'accepted':True,'evidence':'Sí, hoy pago 300 pesos'},
    'motivo_validacion_monto':'Compromiso de 300 menor al mínimo de 1000.'}
 m={'quality_contact_type':'TITULAR','negotiation_validation':n}
 assert definitive_rejection(m,[],120)['code']=='CONFIRMED_INVALID_PAYMENT_AMOUNT'
 for field,value in [('review_required',True),('commitment_confirmed',False),('amount_confirmed',False),('datos_saldo_inconsistentes',True),('multipago_detectado',True)]:
  other=deepcopy(m);other['negotiation_validation'][field]=value
  assert definitive_rejection(other,[],120)is None
 assert definitive_rejection(m,[{'severity':'CRITICAL'}],120)is None


def test_receipt_doubt_does_not_impose_a_new_agreement_on_explicit_pending_decision():
 a=analyze('Habla MRS. Soy yo. ¿Puede realizar su pago hoy? No puedo, no tengo dinero. Ya tengo un ticket anterior y WhatsApp.',
           estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='500',saldo_total='3000')
 r=a.metadata['convenio_payment_validation']
 assert r['receipt_required_for_management']is False
 assert not r['receipt_request_review_required']
 assert not r['receipt_requested']


def test_final_partial_offer_overrides_a_historical_larger_proposal():
 a=analyze('Soy yo. Habla MRS. Ya me habían pedido un pago de 6300 pesos. No lo completé. Puede realizar el pago de 3000 el día de hoy, solamente que va a ser tomado como parcial. Sí, así es. Este pago no regulariza la cuenta. Envíe su comprobante por WhatsApp. Puede pagar en tienda o en Farmacias del Ahorro.',
           estatus_grabacion='CONVENIO',pago_minimo='6171',saldo_total='41000',asignacion='C2',fecha='2026-10-31')
 n=a.metadata['negotiation_validation']
 assert n['commitment_confirmed']
 assert n['monto_detectado']==3000
 assert n['promise_date']=='2026-10-31'


def test_paid_followup_cannot_escape_coverage_from_a_no_to_a_past_question():
 a=analyze('Habla MRS. Soy yo. Ya hice el pago de 95 pesos ayer. ¿El cliente no realizó el pago como acordamos? No, señorita, no. Ya mandé el comprobante por WhatsApp.',
           estatus_grabacion='CONVENIO',pago_minimo='150',saldo_total='500')
 assert not a.metadata['final_result'].startswith('APROBADO')


def test_unilateral_termination_of_conversation_does_not_approve():
 a=analyze('Habla MRS. Soy yo. ¿Contaremos con su pago hoy? No, no tengo dinero. Voy a finalizar con la llamada, señorita, ya que no llegamos a un acuerdo.',
           estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='500',saldo_total='1000')
 assert not a.metadata['final_result'].startswith('APROBADO')

@pytest.mark.parametrize('greeting',['Buenas tardes, señor Luis Ejemplo.','Buen día, señora Laura Ejemplo.'])
def test_named_greeting_and_personal_payment_are_context_not_excel(greeting):
 assert holder_confirmation(greeting+' Sí. Yo no he podido pagar mi tarjeta.')['confirmed']
 assert not holder_confirmation(greeting+' Sí. Gracias.')['confirmed']
 assert not holder_confirmation(greeting+' Soy su hermana. Yo no he podido pagar mi tarjeta.')['confirmed']


def test_own_account_question_identifies_context_without_accepting_a_new_payment():
 text='¿Me puede comunicar con Ana Ejemplo? Sí. Habla MRS. ¿Cuánto es mi pago pendiente? El pago es 300 pesos, no sé si usted lo puede realizar.'
 assert holder_confirmation(text)['confirmed']
 from app.services.payment_intent_frames import payment_frames
 assert not any(f['accepted']or f['conditional']for f in payment_frames(text))
 assert not holder_confirmation('¿Me puede comunicar con Ana Ejemplo? Sí. Gestor: ¿Cuánto es mi pago pendiente?')['confirmed']


def test_selected_operation_amount_is_not_lost_next_to_card_reference():
 a=analyze('Habla MRS. Soy yo. Hoy voy a pagar. Su saldo de la cuenta es de 1659 pesos. Ingrese a su aplicación del banco, elige el monto 1659 y en concepto agrega los 16 dígitos de su tarjeta. Envíe comprobante por WhatsApp. Puede pagar en tienda o en Farmacias del Ahorro.',
           estatus_grabacion='CONVENIO',pago_minimo='294',saldo_total='1659',asignacion='1PV',fecha='2026-11-02')
 assert a.metadata['negotiation_validation']['monto_detectado']==1659
 assert not a.metadata['negotiation_validation']['review_required']


def test_agreed_amount_has_priority_over_old_higher_offer_and_excel_range():
 a=analyze('Habla MRS. Soy yo. El pago mínimo es 1900 pesos. ¿Confirma pago de 1800 pesos para hoy? Sí. Envíe su ticket por WhatsApp. Puede pagar en tienda o en Farmacias del Ahorro.',
           estatus_grabacion='CONVENIO',pago_minimo='1900',saldo_total='5000',asignacion='1PV',fecha='2026-11-02')
 assert a.metadata['negotiation_validation']['monto_detectado']==1800
 assert a.metadata['shared_classification']['clasificacion']=='NO_APROBADO'


def test_different_instruction_after_agreement_requires_confirmation():
 a=analyze('Habla MRS. Soy yo. ¿Confirma pago de 1800 pesos para hoy? Sí. Ingrese a su aplicación del banco, elija el monto 1700. Envíe su ticket por WhatsApp. Puede pagar en tienda o en Farmacias del Ahorro.',
           estatus_grabacion='CONVENIO',pago_minimo='1000',saldo_total='5000',asignacion='1PV',fecha='2026-11-02')
 n=a.metadata['negotiation_validation']
 assert n['payment_instruction_amount_conflicts']
 assert a.metadata['shared_classification']['clasificacion']=='REVISAR'

@pytest.mark.parametrize('reply',['Sí, pero no tengo dinero.','Sí, pero no puedo pagar.','Sí, si me alcanza.'])
def test_yes_does_not_erase_the_customers_payment_condition(reply):
 from app.services.conversation_evidence import payment_commitment
 assert not payment_commitment('¿Confirma su pago hoy? '+reply)['accepted']


def test_ordinary_hesitation_before_yes_can_confirm_a_current_offer():
 from app.services.conversation_evidence import payment_commitment
 assert payment_commitment('¿Contamos con su pago hoy? Este, sí.')['accepted']
 assert not payment_commitment('¿No podemos contar con su pago hoy? Sí.')['accepted']

@pytest.mark.parametrize('phrase',['No mames.','A la verga.','Jodi, jodi, jodi.'])
def test_offensive_expressions_cannot_silently_approve(phrase):
 a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe su comprobante por WhatsApp. '+phrase,
           estatus_grabacion='CONVENIO',pago_minimo='700',saldo_total='3000')
 assert not a.metadata['shared_classification']['aprobado']


def test_background_speech_does_not_confirm_return_from_announced_hold():
 from app.services.call_wait_evidence import assess_call_wait
 units=[{'text':'Permítame revisar.','start':0,'end':5},
        {'text':'No me cuelga, para que le dé la información.','start':5,'end':8},
        {'text':'Voy a buscar mis cosas y comprar algo para mi niña.','start':10,'end':40},
        {'text':'¿Dónde está mi papá?','start':45,'end':55},
        {'text':'Mi suegra me dijo que ya iba a salir.','start':65,'end':75},
        {'text':'Gracias por esperar, le comento el resultado.','start':90,'end':95}]
 w=assess_call_wait(' '.join(u['text']for u in units),units,95)
 assert w['review_required']
 assert any(e['start']==5 and e['end']==90 for e in w['intervals'])

@pytest.mark.parametrize('instruction',[
 'Cuando lo realice me envía su comprobante.',
 'Es importante que realice el pago.',
 'Le pido que lo realice hoy.',
])
def test_agency_future_instruction_is_not_personal_account_evidence(instruction):
 assert not holder_confirmation('¿Me puede comunicar con Ana Ejemplo? Sí. Habla MRS. '+instruction)['confirmed']


def test_courtesy_in_question_is_not_the_requested_persons_name():
 from app.services.contact_evidence_graph import nominal_requests,contextual_contact
 text='¿Quién es usted, perdón? Sí. Mi tarjeta es de otra tienda.'
 assert not list(nominal_requests(text))
 assert not contextual_contact(text)['confirmed']
 assert not holder_confirmation(text)['confirmed']


def test_generic_family_reply_identifies_third_party_without_inventing_exact_kinship():
 from app.services.contact_dialogue_resolution import contact_dialogue_evidence
 e=contact_dialogue_evidence('¿Quién es usted, perdón? Familiar, ¿por qué?')['family']
 assert e and e[0]['phrase']=='familiar'
 assert not contact_dialogue_evidence('¿Quién es usted, perdón? Gestor: Familiar.')['family']

@pytest.mark.parametrize('question',['¿No aplica el pago aún?','¿Señor, no puede realizar el pago hoy?'])
def test_bare_no_to_negative_question_is_not_a_new_payment_refusal(question):
 from app.services.conversation_evidence import payment_commitment
 from app.services.dialogue_evaluation import scan_dialogue,pending_status
 t=question+' No, señorita.'
 c=payment_commitment(t)
 assert not c['accepted'] and not c['declined']
 assert pending_status(scan_dialogue(t),c)is None


def test_refusing_to_clarify_payment_does_not_create_an_approved_no_date_status():
 a=analyze('Soy yo. Habla MRS. ¿Ya aplicó el pago a su tarjeta? No. ¿No aplica el pago aún? No. El pago se solicita hoy. ¿También ya lo sabe? Sí. Le doy el número para reportar el pago. Le dije que no. ¿No qué? No.',
           estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='1000',saldo_total='3000')
 assert not a.metadata['shared_classification']['aprobado']


def test_unavailable_day_is_not_accepted_as_a_promise_date():
 from app.services.payment_intent_frames import payment_frames
 frames=payment_frames('¿Qué día no puede realizar el pago? El viernes.')
 assert not any(f['accepted']for f in frames)
 assert not any(f['accepted']for f in payment_frames('¿Qué día no lo estaría realizando el pago? El viernes.'))
