"""Regresión r51: una oferta de pago expresa no es ausencia de negociación.

Cubre regresión detectada al reconocer titular durante reanálisis del mismo lote.
"""
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService


def test_holder_direct_offer_is_not_penalized_as_no_attempt():
    text = (
        "Buen día, de jurídico MRS en representación de Bradescard, "
        "mi nombre es Carla. Busco a Pedro González. "
        "¿Usted es Pedro? Sí. "
        "Por atraso en su tarjeta se le está requiriendo el pago. "
        "Puede cubrir 3154 pesos o un pago de 800 pesos. "
        "¿Usted podría realizar su pago de 800 pesos para el día de hoy? "
        "¿Podría confirmar su pago? "
        "No sé si hoy pueda. Entiendo, puede avisarnos después."
    )
    transcription = TranscriptionModel(
        'requerimiento.wav', 'requerimiento.wav', text, duration_seconds=130
    )
    analysis = AnalyticsService.analyze_transcription(transcription, {
        'estatus_grabacion': 'NO DEFINE',
        'fecha': '2026-11-09',
        'asignacion': '1PV',
        'pago_minimo': '800',
        'saldo_total': '3154',
    })
    m = analysis.metadata
    assert m['quality_contact_type'] == 'TITULAR'
    assert m['negotiation_validation']['negotiation_attempt_detected']
    assert not m['negotiation_validation']['missing_collection_attempt_penalty']
    assert 'PEN_SIN_INTENTO_NEGOCIACION' not in {p['id'] for p in m['penalties']}


def test_not_every_payment_mention_is_new_attempt():
    text = (
        "Buenos días, ¿hablo con Pedro González? Sí, soy yo. "
        "Solo llamo para saber si ya quedó registrado su pago."
    )
    t = TranscriptionModel('check.wav', 'check.wav', text, duration_seconds=100)
    analysis = AnalyticsService.analyze_transcription(t, {
        'estatus_grabacion': 'NO DEFINE',
        'fecha': '2026-11-09',
        'asignacion': '1PV',
    })
    m = analysis.metadata
    assert not m['negotiation_validation']['negotiation_attempt_detected']
