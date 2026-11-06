"""Calibración con ejemplos sintéticos; no copiar aprobaciones históricas."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import completed_payment, holder_confirmation, payment_commitment, assess_recado
from app.services.reported_payment_amounts import reported_amounts


def analyze(text, **context):
    return A.analyze_transcription(TranscriptionModel('synthetic.ogg','synthetic.ogg',text,
        duration_seconds=95),context)


@pytest.mark.parametrize('text,amount',[
    ('Ya pagué 900 pesos el día 18.',900),
    ('Hoy lo hice y se reflejará en 72 horas. ¿De qué cantidad realizó su pago? De 2900 pesos.',2900),
    ('Ya lo hice. ¿Qué día? El 16. ¿Por qué cantidad? El sábado pasado por cinco mil.',5000),
    ('Ya lo hice el día de ayer. El día de ayer de qué cantidad fue disculpe de dos mil ochocientos cincuenta y cuatro algo así.',2854),
    ('Hoy lo hice por la cantidad que era el pago total de dos mil cuarenta.',2040),
    ('Hice un pago el día 15. Hice un pago mínimo de 880 pesos el jueves 5.',880),
    ('Ya pagué 900 pesos. Ya hice mi pago de 900 pesos.',900),
])
def test_prior_payment_has_amount_not_date_or_waiting_time(text,amount):
    result=reported_amounts(text,completed_payment(text))
    assert result['total']==amount
    assert result['amounts']==[amount]


@pytest.mark.parametrize('text',[
    'El pago ya está hecho. Fue el día 20, o más bien el 19.',
    'Hoy lo hice, en 72 horas se refleja.',
    'Ya pagué. Su saldo total es de 8000 pesos.',
    'Ya pagué. Tiene que realizar un pago de 900 pesos mañana.',
    'Hice un pago el día 18. Envíe el comprobante al WhatsApp 5512345678.',
])
def test_unknown_paid_amount_stays_unknown(text):
    assert reported_amounts(text,completed_payment(text))['total'] is None


def test_different_prior_payment_amounts_are_not_automatically_added():
    text='Ya pagué 900 pesos. Ya hice un pago de 1200 pesos.'
    result=reported_amounts(text,completed_payment(text))
    assert result['review_required'] and result['total'] is None
    assert {e['amount'] for e in result['evidence']}=={900,1200}


def test_two_explicit_dated_payments_are_added_once():
    text='Ya le di un abono y otro ayer. El viernes fue 300 y el día ayer de 315. Ayer realizó un pago de 315.'
    result=reported_amounts(text,completed_payment(text))
    assert result['total']==615 and result['amounts']==[300,315]
    assert not result['review_required']


@pytest.mark.parametrize('text',[
    'El pago ya está hecho, pero no se ha reflejado.',
    'Ayer pagamos.', 'Ya pagamos.',
])
def test_passive_and_plural_payment_reports(text):
    assert completed_payment(text)['confirmed']


@pytest.mark.parametrize('text',[
    'Cuando el pago ya está hecho, debe enviar comprobante.',
    'Si el pago ya está hecho, envíe comprobante.',
    'El pago no está hecho.', 'Mañana pagamos.',
    'Gestor: El pago ya está hecho.',
])
def test_conditional_future_negative_or_agent_is_not_a_paid_report(text):
    assert not completed_payment(text)['confirmed']


@pytest.mark.parametrize('status',['CONVENIO','NO DEFINE FECHA DE PAGO'])
def test_user_policy_retains_original_status_in_verified_payment_followup(status):
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe su comprobante por WhatsApp.',
        estatus_grabacion=status,pago_minimo='700',saldo_total='3000')
    s=a.metadata['status_validation'];n=a.metadata['negotiation_validation']
    assert s['matches'] and s['policy_source']=='ACLARACION_USUARIO_20261028'
    assert s['detected_status']=='PAGO REPORTADO / ACLARACION'
    assert n['payment_followup_case'] and not n['commitment_confirmed']
    assert a.metadata['final_result']=='APROBADO'
    assert not any(p['id'] in {'PEN_CONV_LUGARES','PEN009'} for p in a.metadata['penalties'])


def test_payment_receipt_followup_does_not_claim_unknown_amount_covers_minimum():
    a=analyze('Habla MRS. Soy yo. El pago ya está hecho. ¿Tiene captura del pago?',
              estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='700',saldo_total='3000')
    n=a.metadata['negotiation_validation']
    assert n['reported_payment_amount_pending'] and not n['prior_payment_covers_minimum']
    assert a.metadata['final_result']=='APROBADO'
    assert n['prior_payment_total'] is None
    assert 'PEN_SIN_INTENTO_NEGOCIACION' not in {p['id'] for p in a.metadata['penalties']}


def test_unknown_paid_amount_without_receipt_followup_stays_for_review():
    a=analyze('Habla MRS. Soy yo. El pago ya está hecho.',
              estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='700',saldo_total='3000')
    assert a.metadata['final_result']=='REVISAR'


@pytest.mark.parametrize('text',[
    'Es importante que ella realice un pago inmediatamente.',
    'Sería que realice el pago de 900 pesos.',
    'Es necesario que lo realice por esa cantidad.',
    'Realice el pago de 900 pesos.',
])
def test_subjunctive_instruction_is_not_a_prior_payment(text):
    assert not completed_payment(text)['confirmed']


def test_prior_payment_does_not_exempt_a_new_payment_instruction_without_acceptance():
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe comprobante por WhatsApp. '
              'Tiene que aplicar un pago de 50 pesos hoy.',
              estatus_grabacion='CONVENIO',pago_minimo='905',saldo_total='3000')
    assert a.metadata['negotiation_validation']['unaccepted_new_payment_instruction']
    assert a.metadata['final_result']=='REVISAR'


def test_explicit_arrears_in_a_family_message_are_not_silently_approved():
    a=analyze('Habla MRS. ¿Qué parentesco tiene con él? Hermana. '
              '¿Puedo dejar un recado? Sí, claro. Dígale que se comunique por el atraso de la tarjeta.',
              estatus_grabacion='RECADO REF1')
    assert a.metadata['privacy_validation']['review_required']
    assert a.metadata['final_result']=='REVISAR'


@pytest.mark.parametrize('problem',[
    'Me trataron mal.',
    'Puede realizar una transferencia.',
    'La tarjeta termina en 9999.',
])
def test_payment_followup_does_not_waive_other_requested_rules(problem):
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe su comprobante por WhatsApp. '+problem,
              estatus_grabacion='CONVENIO',pago_minimo='700',saldo_total='3000',numero_de_tarjeta='1234567890123456')
    assert a.metadata['final_result']!='APROBADO'


@pytest.mark.parametrize('opening',[
    '¿Se encuentra Persona de Ejemplo? Ella habla.',
    '¿Se encuentra Persona de Ejemplo? Ella habla de Otra Ciudad.',
    'Tengo el gusto con el señor. Persona de Ejemplo. Sí.',
])
def test_natural_holder_identity_and_split_honorific(opening):
    assert holder_confirmation(opening)['confirmed']


def test_named_call_and_explicit_own_account_response_can_identify_holder():
    r=holder_confirmation('Me comunica con Persona de Ejemplo. ¿De dónde? De MRS. Yo tengo una cuenta de 2000 pesos y mi tarjeta está bloqueada.')
    assert r['confirmed'] and r['method']=='AUTORREFERENCIA_CUENTA_TRAS_IDENTIFICACION'


@pytest.mark.parametrize('text',[
    'Me comunica con Persona de Ejemplo. ¿De dónde? De MRS. No tengo dinero.',
    'Me comunica con Persona de Ejemplo. Soy su madre. Mi tarjeta está bloqueada.',
    'Me comunica con Persona de Ejemplo. No está aquí. Mi cuenta es otra.',
    'Me comunica con Persona de Ejemplo. Gestor: Mi tarjeta está bloqueada.',
])
def test_generic_reply_family_absence_and_agent_do_not_get_holder_identity(text):
    assert not holder_confirmation(text)['confirmed']


@pytest.mark.parametrize('answer',['Hermana.','No la escuché. Hermana.','Madre.'])
def test_kinship_response_and_actual_message_acceptance(answer):
    text=('Habla MRS. ¿Qué parentesco tiene con él? '+answer+
          ' ¿Puedo dejar un recado con usted? Sí, claro. Dígale que se comunique al número de contacto.')
    a=analyze(text,estatus_grabacion='RECADO REF1')
    assert a.metadata['status_validation']['recado_evidence']['confirmed_recado']
    assert a.metadata['final_result']=='APROBADO'


@pytest.mark.parametrize('answer',['Le paso el dato.','Yo le aviso igual.'])
def test_other_recipient_message_acceptance_forms(answer):
    assert assess_recado('Es mi sobrino. Dígale que se comunique. '+answer)['acceptance']


@pytest.mark.parametrize('text',[
    '¿Qué parentesco tiene con él? Gestor: Hermana.',
    'Es mi sobrino. Gracias por recibir el recado.',
    'Es mi sobrino. ¿Puedo dejar un recado? Sí, pero no le voy a decir nada.',
])
def test_agent_or_refusal_does_not_invent_a_received_recado(text):
    a=analyze(text,estatus_grabacion='RECADO REF1')
    assert a.metadata['final_result']=='REVISAR'


@pytest.mark.parametrize('text',[
    '¿De qué cantidad va a realizar su pago hoy? De mil pesos.',
    '¿Ya tendrá usted el pago para hoy? Sí, ya lo tengo para hoy.',
])
def test_firm_future_answers_are_recognized(text):
    assert payment_commitment(text)['accepted']


def test_uncertainty_about_posting_does_not_cancel_a_firm_future_promise():
    r=payment_commitment('Me comprometo a pagar 900 pesos mañana. Yo creo que no se ha reflejado el pago anterior.')
    assert r['accepted']


def test_phone_ending_for_receipt_does_not_become_wrong_card():
    text=('Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe el comprobante por WhatsApp. '
          '¿Me confirma la terminación? ¿De cuál número? De WhatsApp. Termina en 0880.')
    a=analyze(text,estatus_grabacion='CONVENIO',numero_de_tarjeta='1234567890123456',pago_minimo='700')
    assert a.metadata['card_validation']['result']=='NO SE PROPORCIONO TARJETA'
    assert a.metadata['final_result']=='APROBADO'


def test_card_suffix_after_phone_context_is_still_compared_when_explicit():
    r=A.calculate_basic_compliance('Envíe comprobante por WhatsApp. Su tarjeta termina en 9999.',
                                  {'numero_de_tarjeta':'1234567890123456'})
    assert r['card_validation']['result']=='TARJETA INCORRECTA'


def test_clipped_tail_expletive_stays_for_review_without_asserting_a_critical_fault():
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe comprobante por WhatsApp. Gracias. Hasta luego. ¡Uta!',
              estatus_grabacion='CONVENIO',pago_minimo='700')
    assert a.metadata['quality_checks']['posible_groseria_recortada_cierre']
    assert a.metadata['final_result']=='REVISAR'
    assert not a.metadata['critical_failures']


@pytest.mark.parametrize('complaint',['Se puso muy grosera.', 'Fue muy grosera.',
                                     'Me está hablando muy fuerte.', 'Me estaba insultando.'])
def test_receipt_followup_does_not_approve_new_complaint_variants(complaint):
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe comprobante por WhatsApp. '+complaint,
              estatus_grabacion='CONVENIO',pago_minimo='700')
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert a.metadata['final_result']=='REVISAR'


def test_negated_mistreatment_complaint_is_not_an_actual_complaint():
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe comprobante por WhatsApp. Nunca me trataron mal.',
              estatus_grabacion='CONVENIO',pago_minimo='700')
    assert not a.metadata['quality_checks']['queja_maltrato_detectada']
    assert a.metadata['final_result']=='APROBADO'


def test_unconfirmed_status_preserves_penalty_score_and_independent_review():
    a=analyze('Habla MRS. Buenos días.',estatus_grabacion='NO DEFINE FECHA DE PAGO')
    assert a.compliance_score==100
    assert a.metadata['status_validation']['matches'] is None
    assert a.metadata['final_result']=='REVISAR'


def test_regression_approval_exception_requires_the_new_user_policy_and_evidence():
    from copy import deepcopy
    from tools.regression_checkpoints import verified_followup_approval
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe comprobante por WhatsApp.',
              estatus_grabacion='CONVENIO',pago_minimo='700')
    assert verified_followup_approval(a.metadata)
    for field,value in [('policy_source','OTHER_POLICY'),('evidence',''),('matches',None)]:
        modified=deepcopy(a.metadata);modified['status_validation'][field]=value
        assert not verified_followup_approval(modified)
    modified=deepcopy(a.metadata)
    modified['negotiation_validation']['unaccepted_new_payment_instruction']=True
    assert not verified_followup_approval(modified)


@pytest.mark.parametrize('opening',[
    'Me voy a comunicar con Persona de Ejemplo. Sí, dígame.',
    '¿Puede comunicar con Persona de Ejemplo? Sí, dígame. Él habla.',
    '¿Tengo gusto con Persona de Ejemplo? Sí.',
])
def test_nominal_opening_variants_keep_identity(opening):
    assert holder_confirmation(opening)['confirmed']


def test_agent_not_being_customer_service_does_not_deny_holder_identity():
    text=('¿Me comunique con Persona de Ejemplo? Sí, ¿con quién tengo el gusto? Habla MRS. '
          '¿Me pueden enviar mi estado de cuenta por correo? No soy atención a clientes.')
    assert holder_confirmation(text)['confirmed']


def test_first_person_account_response_is_not_rejected_by_payment_not_being_posted():
    text=('Me comunica con Persona de Ejemplo. ¿De dónde? De MRS. Mi tarjeta está bloqueada. '
          'El pago no está reflejado. Le paso el número para su comprobante.')
    assert holder_confirmation(text)['confirmed']


def test_declining_confirmation_after_offer_is_not_silence_or_accepted_promise():
    a=analyze('Habla MRS. Soy yo. Le ofrecemos una opción de pago de 900 pesos. '
              '¿Lo confirmo? No, no lo confirmo.',estatus_grabacion='NO DEFINE FECHA DE PAGO')
    assert a.metadata['status_validation']['matches'] is True
    assert a.metadata['final_result']=='APROBADO'


def test_historical_payment_does_not_hide_declining_a_new_negotiation():
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos el mes pasado. '
        'Le ofrecemos una opción de pago mínimo de 1200 pesos hoy. No voy a poder pagar más dinero.',
        estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='1200',saldo_total='4000')
    assert a.metadata['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'
    assert a.metadata['status_validation']['matches'] is True
    assert a.metadata['final_result']=='APROBADO'


def test_historical_payment_with_later_different_firm_amount_is_not_automatically_no_date():
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. Le ofrecemos una opción de pago mínimo de 1200 pesos hoy. '
        'No voy a poder pagar 1200, pero yo lunes pago 1000 pesos.',
        estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='1200',saldo_total='4000')
    assert a.metadata['final_result']!='APROBADO'


def test_unrelated_uncertainty_does_not_negate_explicit_message_transmission():
    text='Es mi sobrino. Dígale que se comunique. No sé si se comunicó, le paso el dato y que se comunique.'
    assert assess_recado(text)['acceptance']
    a=analyze('Habla MRS. '+text,estatus_grabacion='RECADO REF1')
    assert a.metadata['status_validation']['recado_evidence']['confirmed_recado']


def test_directly_negated_message_transmission_is_not_acceptance():
    assert not assess_recado('Es mi sobrino. No le paso el dato.')['acceptance']


def test_payment_offer_ending_in_question_is_still_a_collection_attempt():
    a=analyze('Habla MRS. Soy yo. Ya pagué. Tendría que depositar 1200 pesos mañana, ¿cuento con su pago? '
              '¿De dónde sale esa cantidad?',estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='2000')
    n=a.metadata['negotiation_validation']
    assert n['negotiation_attempt_detected']
    assert 'PEN_SIN_INTENTO_NEGOCIACION' not in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['final_result']=='REVISAR'


def test_known_holder_request_for_someone_else_payment_is_not_agent_negotiation():
    a=analyze('Gestor: Habla MRS.\nTitular: Soy yo. ¿Cuento con su pago?',
              estatus_grabacion='NO DEFINE FECHA DE PAGO')
    assert not a.metadata['negotiation_validation']['negotiation_attempt_detected']
