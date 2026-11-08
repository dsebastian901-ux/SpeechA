"""La aclaración del usuario permite saldo pendiente genérico, no sus importes."""
import pytest

from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import assess_privacy, sensitive_financial_matches


@pytest.mark.parametrize('text', [
    'Es referente al saldo pendiente.',
    'Tiene un saldo vencido.',
    'Tiene un saldo pendiente en su tarjeta departamental, terminación 6016.',
    'Le informo del saldo pendiente. Llame al 5551234567.',
    'Tiene un saldo pendiente; anote el teléfono 5551234567.',
    'Tiene un saldo pendiente. Puede llamar de 8 a 21 horas.',
    'Le llamo por el saldo pendiente de una tarjeta.',
    'Es sobre el saldo pendiente de un crédito.',
])
def test_generic_balance_is_allowed_even_for_confirmed_gestor_and_third_party(text):
    result = assess_privacy(text, [{'text': text, 'speaker_role': 'GESTOR'}], third_party_confirmed=True)
    assert not result['confirmed_disclosure'] and not result['review_required']
    assert result['allowed_generic_balance_mentions']


@pytest.mark.parametrize('text', [
    'Su saldo pendiente es de 1500 pesos.', 'Tiene un saldo pendiente de $1,500.',
    'Su saldo pendiente es de mil quinientos pesos.', 'Saldo pendiente: tres mil quinientos noventa pesos.',
    'Su saldo pendiente asciende a 3500.', 'Saldo pendiente de mil 500 pesos.',
    'Tiene una deuda de 500 pesos.', 'Tiene tres meses de atraso.',
    'Presenta dos mensualidades vencidas.',
    'Su tarjeta es 1234567890123456.',
    'Saldo pendiente de un peso.',
])
def test_amounts_arrears_debt_and_full_card_stay_protected(text):
    result = assess_privacy(text, [{'text': text, 'speaker_role': 'GESTOR'}], third_party_confirmed=True)
    assert sensitive_financial_matches(text)
    assert result['confirmed_disclosure']
    assert not result['review_required']


@pytest.mark.parametrize('role', ['TERCERO', 'TITULAR'])
def test_recipient_reporting_payment_does_not_become_gestor_disclosure(role):
    text = 'Tiene un saldo pendiente de 500 pesos.'
    result = assess_privacy(text, [{'text': text, 'speaker_role': role}], third_party_confirmed=True)
    assert not result['confirmed_disclosure'] and not result['review_required']


def test_generic_policy_does_not_approve_other_failures():
    result = A.calculate_basic_compliance(
        'Soy su madre. Tiene un saldo pendiente. No le voy a pasar el recado.',
        {'estatus_grabacion': 'MENSAJE CON FAMILIAR', 'asignacion': '1PV'})
    assert not result['privacy_validation']['review_required']
    assert not result['status_validation']['recado_evidence']['confirmed_recado']


@pytest.mark.parametrize('amount_role,critical,review', [
    ('GESTOR', True, False), ('NO DETERMINADO', False, True), ('TERCERO', False, False),
])
def test_amount_after_sentence_break_keeps_its_actual_speaker(amount_role, critical, review):
    text = 'Su saldo pendiente. Son 1500 pesos.'
    segments = [{'text': 'Su saldo pendiente.', 'speaker_role': 'GESTOR', 'start': 10, 'end': 12},
                {'text': 'Son 1500 pesos.', 'speaker_role': amount_role, 'start': 12, 'end': 15}]
    result = assess_privacy(text, segments, third_party_confirmed=True)
    assert result['confirmed_disclosure'] is critical
    assert result['review_required'] is review
