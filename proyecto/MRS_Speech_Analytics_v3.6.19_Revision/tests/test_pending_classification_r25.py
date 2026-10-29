"""Regresión de interlocutor y respuesta condicionada; ejemplos sintéticos."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import associate_relationship, payment_commitment
from app.services.conversation_evidence import completed_payment
from app.services.reported_payment_amounts import reported_amounts


def analyze(text, **context):
    return A.analyze_transcription(TranscriptionModel('example.ogg','example.ogg',text,
        duration_seconds=120), {'fecha':'2026-10-22','asignacion':'1PV',
        'pago_minimo':'1200','saldo_total':'5000', **context})


@pytest.mark.parametrize('reply', ['Somos conocidos.', 'Pues somos conocidas.',
    'Solo somos amigos.', 'Bueno, somos solo amigas.'])
def test_plural_association_identifies_a_third_party_without_inventing_family(reply):
    a=analyze('Habla MRS. ¿Qué relación tiene con la persona? '+reply,
              estatus_grabacion='RECADO REF1')
    assert a.metadata['quality_contact_type']=='TERCERO'
    assert a.metadata['associate_contact_validation']['confirmed']
    assert a.metadata['status_validation']['relationship']=='TERCERO'
    assert not a.metadata['status_validation']['recado_evidence']['confirmed_recado']
    assert a.metadata['final_result']=='REVISAR'


@pytest.mark.parametrize('reply', ['¿Somos conocidos?', 'No somos conocidos.',
    'Diga que somos amigos.', 'Él dice que somos conocidos.',
    'Gestor: Somos conocidos.', 'Titular: Somos amigos.'])
def test_question_negation_quote_and_other_roles_do_not_identify_a_third_party(reply):
    assert not associate_relationship(reply)['confirmed']


def test_plural_association_does_not_displace_explicit_holder_identity():
    a=analyze('Habla MRS. Soy yo. Somos amigos.')
    assert a.metadata['quality_contact_type']=='TITULAR'


def test_plural_association_with_unknown_disclosure_does_not_invent_pen003():
    a=analyze('Habla MRS. Pues somos conocidos. Tiene una mensualidad vencida.',
              estatus_grabacion='RECADO REF1')
    assert a.metadata['privacy_validation']['review_required']
    assert not a.metadata['privacy_validation']['confirmed_disclosure']
    assert 'PEN003' not in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['final_result']=='REVISAR'


def test_confirmed_agent_disclosure_to_an_associate_keeps_its_critical_failure():
    a=analyze('Gestor: Habla MRS.\nInterlocutor: Somos conocidos.\n'
              'Gestor: Tiene una mensualidad vencida.',estatus_grabacion='RECADO REF1')
    assert a.metadata['privacy_validation']['confirmed_disclosure']
    assert any(p['id']=='PEN003' and p['invalidates'] for p in a.metadata['penalties'])
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('answer', [
    'Primero voy a analizar porque sí di los pagos dentro de la fecha.',
    'Primero voy a revisar el adeudo.',
    'Antes de pagar necesito consultar los cargos.',
    'Si corresponde, pagaré mañana.',
    'Pagaré mañana si procede.',
    'Si me aclaran los cargos, voy a pagar.',
    'Si es necesario, pagaré mañana.',
])
def test_reviewing_charges_before_paying_is_conditional_not_a_commitment(answer):
    c=payment_commitment('¿Podemos contar con su pago de 1200 pesos? '+answer)
    assert not c['accepted'] and c.get('conditional')


@pytest.mark.parametrize('text', [
    '¿Podemos confirmar su pago de 1200 pesos? Sí, si corresponde.',
    '¿Podemos contar con su pago para mañana? Sí, si procede.',
    'Confirmo el pago de 1200. Sí, si es necesario.',
    '¿Qué cantidad puede pagar? 1200, si me aclaran los cargos.',
    'Puede pagar mañana. ¿Cuánto me dice? 1200 pesos. Ok, está bien, si corresponde.',
])
def test_affirmative_prefix_does_not_hide_a_condition_on_the_payment(text):
    c=payment_commitment(text)
    assert not c['accepted'] and c.get('conditional')


@pytest.mark.parametrize('text', [
    'Voy a pagar mañana. Primero voy a revisar el comprobante del pago.',
    'Voy a pagar mañana. Primero voy a consultar el número de WhatsApp.',
    'Voy a pagar mañana. ¿Primero reviso los cargos?',
    'Voy a pagar mañana. Gestor: Primero voy a revisar el adeudo.',
    'Primero voy a revisar el adeudo. Ya me explicaron, voy a pagar mañana.',
    'Primero voy a revisar mi estado de cuenta y mañana pago.',
    'Si corresponde un reembolso, me avisa; mañana pago.',
])
def test_receipt_preparation_agent_question_or_later_firm_payment_keeps_acceptance(text):
    assert payment_commitment(text)['accepted']


def test_explicit_charge_review_detects_no_date_without_overriding_other_blockers():
    a=analyze('Habla MRS. Soy yo. Puede realizar un pago de 1200 pesos hoy. '
              'Primero voy a revisar los cargos. Si corresponde, pagaré.',
              estatus_grabacion='NO DEFINE FECHA DE PAGO')
    assert a.metadata['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'
    assert a.metadata['status_validation']['matches']
    assert not a.metadata['negotiation_validation']['commitment_confirmed']
    assert a.metadata['final_result']=='APROBADO'


def test_historical_payment_does_not_hide_the_conditional_answer_to_a_new_proposal():
    a=analyze('Habla MRS. Soy yo. Ya pagué 1200 pesos. Puede realizar un pago de 1500 pesos hoy. '
              'Primero voy a analizar porque sí di los pagos dentro de la fecha.',
              estatus_grabacion='NO DEFINE FECHA DE PAGO')
    n=a.metadata['negotiation_validation'];s=a.metadata['status_validation']
    assert n['payment_confirmation_case'] and n['prior_payment_with_current_condition']
    assert n['prior_payment_total']==1200
    assert not n['commitment_confirmed']
    assert s['detected_status']=='NO DEFINE FECHA DE PAGO' and s['matches']


def test_convenio_with_unaccepted_new_payment_still_requires_review_after_a_historical_payment():
    a=analyze('Habla MRS. Soy yo. Ya pagué 1200 pesos. Envíe el comprobante por WhatsApp. '
              'Tiene que realizar un pago de 1500 pesos hoy. Primero voy a revisar el adeudo.',
              estatus_grabacion='CONVENIO')
    n=a.metadata['negotiation_validation']
    assert n['prior_payment_with_current_condition'] and n['unaccepted_new_payment_instruction']
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('instruction', [
    'Puede realizar un pago de 1500 pesos hoy.',
    'Podría aplicar un pago de 1500 pesos hoy.',
    'Necesita cubrir un pago de 1500 pesos hoy.',
    'Puede usted hacer un pago de 1500 pesos hoy.',
    'Puede depositar un pago de 1500 pesos hoy.',
])
def test_a_new_payment_instruction_does_not_contaminate_the_historical_paid_total(instruction):
    text='Ya pagué 1200 pesos. '+instruction
    p=reported_amounts(text,completed_payment(text))
    assert p['total']==1200 and p['amounts']==[1200]
    assert not p['review_required']


def test_monthly_calendar_does_not_hide_the_current_deposit_or_reuse_a_historical_amount():
    a=analyze('Habla MRS. Soy yo. Pagué 1200 pesos. '
              'Como ya pasó su fecha de pago, que sería el dos de cada mes, '
              'tendríamos que realizar un depósito de 1760 pesos. '
              'Primero voy a revisar los cargos porque sí di los pagos dentro de la fecha.',
              estatus_grabacion='NO DEFINE FECHA DE PAGO',pago_minimo='1355',saldo_total='2352')
    n=a.metadata['negotiation_validation']
    assert n['prior_payment_total']==1200
    assert n['monto_detectado']==1760 and n['validacion_monto']=='VALIDA'
    assert not n['commitment_confirmed']
    assert a.metadata['status_validation']['matches']
    assert a.metadata['final_result']=='APROBADO'


@pytest.mark.parametrize('fee', [
    'La anualidad genera un pago de 85 pesos cada mes.',
    'Es un cargo mensual de 85 pesos.',
    'Ese pago es de 85 pesos al mes.',
])
def test_actual_recurring_fees_do_not_replace_the_current_payment_offer(fee):
    a=analyze('Habla MRS. Soy yo. '+fee+' '
              'Por la falta de pago puede realizar un depósito de 1760 pesos hoy. '
              'Primero voy a revisar los cargos.',estatus_grabacion='NO DEFINE FECHA DE PAGO',
              pago_minimo='1355',saldo_total='2352')
    assert a.metadata['negotiation_validation']['monto_detectado']==1760


def test_a_deposit_below_minimum_keeps_review_even_after_a_conditional_answer():
    a=analyze('Habla MRS. Soy yo. Su fecha de pago es el dos de cada mes. '
              'Tiene que realizar un depósito de 500 pesos hoy. '
              'Primero voy a revisar los cargos.',estatus_grabacion='NO DEFINE FECHA DE PAGO',
              pago_minimo='1355',saldo_total='2352')
    n=a.metadata['negotiation_validation']
    assert n['monto_detectado']==500 and n['review_required']
    assert not a.metadata['shared_classification']['aprobado']


def test_a_new_deposit_request_is_not_approved_as_only_a_receipt_followup():
    a=analyze('Habla MRS. Soy yo. Ya pagué 1200 pesos. Envíe su comprobante por WhatsApp. '
              'Tendríamos que realizar un depósito de 1500 pesos hoy. Primero voy a revisar el adeudo.',
              estatus_grabacion='CONVENIO')
    n=a.metadata['negotiation_validation']
    assert n['payment_followup_case'] and n['negotiation_attempt_detected']
    assert n['unaccepted_new_payment_instruction']
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('problem', [
    'Me trataron mal.',
    'La tarjeta termina en 9999.',
    'Puede realizar una transferencia.',
])
def test_correct_no_date_status_does_not_exempt_treatment_reference_or_payment_security(problem):
    a=analyze('Habla MRS. Soy yo. Puede realizar un pago de 1200 pesos hoy. '
              'Primero voy a revisar los cargos. '+problem,
              estatus_grabacion='NO DEFINE FECHA DE PAGO',numero_de_tarjeta='1234567890123456')
    assert a.metadata['status_validation']['matches']
    assert not a.metadata['shared_classification']['aprobado']
