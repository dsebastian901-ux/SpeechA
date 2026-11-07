import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import assess_recado, holder_confirmation


def analyze(text, **relation):
    return A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo':'sample.wav','texto':text,'duracion_segundos':120}), relation)


def test_phone_suffix_with_subsequent_personal_number_context_is_not_card():
    a=analyze('Me aparece un número en el sistema, es con terminación 0455. '
              '0455 la terminación perfecto, este es el número personal de Luis.',
              numero_de_tarjeta='1234567890120014')
    assert a.metadata['card_validation']['result']=='NO SE PROPORCIONO TARJETA'


def test_explicit_card_is_not_hidden_by_an_unrelated_later_phone():
    a=analyze('Su tarjeta tiene terminación 9999. Este es el número personal de Luis.',
              numero_de_tarjeta='1234567890120014')
    assert a.metadata['card_validation']['result']=='TARJETA INCORRECTA'


def test_possible_suffix_correction_is_uncertain_not_completed_from_excel():
    a=analyze('Su tarjeta terminación 6503, 06 personas.',numero_de_tarjeta='1234567890126506')
    assert a.metadata['card_validation']['result']=='REVISAR - NUMERO NO CONFIABLE'
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('text',[
    'El pago lo estaría aplicando directamente en tienda o establecimientos autorizados que son del Sol, Kiosco.',
    'Adicional a tienda del Sol, pueden aplicar el pago en Kiosco.',
])
def test_payment_enumeration_remains_attached_to_instruction(text):
    a=analyze('Habla MRS. Soy yo. '+text,estatus_grabacion='CONVENIO')
    assert a.metadata['convenio_payment_validation']['authorized_places_count']==2


def test_su_recado_is_acceptance_but_never_invents_family_or_message():
    a=assess_recado('Yo le paso su recado.')
    assert a['acceptance'] and not a['family']
    assert not assess_recado('No le paso su recado.')['acceptance']
    assert not assess_recado('Gestor: Le paso su recado.')['acceptance']


def test_servidor_answers_a_named_identity_request_only():
    assert holder_confirmation('Me comunico con Juan Pérez. Servidor.')['confirmed']
    assert not holder_confirmation('¿Quién le llama? Servidor.')['confirmed']
    assert not holder_confirmation('Me comunico con Juan Pérez. Gestor: Servidor.')['confirmed']
    assert not holder_confirmation('Me comunico con Juan Pérez. Servidor. Soy su hermano.')['confirmed']


def test_callback_proposal_requires_review_instead_of_false_abandonment():
    a=analyze('Gestor: Si gusta le cuelgo la llamada y se la regreso. Titular: Ok.')
    assert 'PEN_CUELGA_GESTOR' not in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['call_end_validation']['callback_proposed']
    assert not a.metadata['shared_classification']['aprobado']


def test_callback_does_not_exempt_a_separate_unilateral_hangup():
    a=analyze('Gestor: Si gusta le cuelgo la llamada y se la regreso. '
              'Gestor: Ahora le voy a colgar.')
    assert 'PEN_CUELGA_GESTOR' in {p['id'] for p in a.metadata['penalties']}


def test_named_arco_right_does_not_waive_full_procedure():
    a=analyze('Habla MRS. No lo conozco. Es un derecho que se llama ARCO.')
    assert a.metadata['arco_validation']['rights_mentioned']
    assert not a.metadata['arco_validation']['valid']
    assert not a.metadata['shared_classification']['aprobado']


def test_distant_month_without_year_is_not_critical_by_automatic_rollover():
    a=analyze('Habla MRS. Soy yo. Me comprometo a pagar 500 pesos el 18 de junio.',
        estatus_grabacion='CONVENIO',asignacion='1PV',fecha='2026-10-31',vencimiento='2026-11-25',pago_minimo='500',saldo_total='2000')
    n=a.metadata['negotiation_validation']
    assert n['date_year_rollover_review']
    assert not n['promise_date_confirmed_from_call']
    assert 'PEN005' not in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'


def test_explicit_distant_year_does_not_waive_overdue_promise():
    a=analyze('Habla MRS. Soy yo. Me comprometo a pagar 500 pesos el 18 de junio de 2027.',
        estatus_grabacion='CONVENIO',asignacion='1PV',fecha='2026-10-31',vencimiento='2026-11-25',pago_minimo='500',saldo_total='2000')
    assert not a.metadata['negotiation_validation']['date_year_rollover_review']
    assert 'PEN005' in {p['id'] for p in a.metadata['penalties']}


def test_near_december_january_boundary_keeps_deadline_validation():
    a=analyze('Habla MRS. Soy yo. Me comprometo a pagar 500 pesos el 5 de enero.',
        estatus_grabacion='CONVENIO',asignacion='1PV',fecha='2026-12-30',vencimiento='2026-12-31',pago_minimo='500',saldo_total='2000')
    assert not a.metadata['negotiation_validation']['date_year_rollover_review']
    assert 'PEN005' in {p['id'] for p in a.metadata['penalties']}


def test_missing_convenio_label_does_not_approve_a_new_overdue_promise():
    a=analyze('Habla MRS. Soy yo. Me comprometo a pagar 500 pesos el 18 de junio de 2027.',
        asignacion='1PV',fecha='2026-10-31',vencimiento='2026-11-25',pago_minimo='500',saldo_total='2000')
    assert a.metadata['negotiation_validation']['review_required']
    assert not a.metadata['shared_classification']['aprobado']
