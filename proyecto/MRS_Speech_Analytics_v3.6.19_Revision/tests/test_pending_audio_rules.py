"""Ejemplos sintéticos de ofertas de finiquito y respuestas condicionales."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import payment_commitment


def analyze_offer(offer, **context):
    text = ("Habla MRS. Soy yo. " + offer +
            " Me interesa, pero lo podría hacer a principios de noviembre.")
    transcript = TranscriptionModel("synthetic.wav", "synthetic.wav", text, duration_seconds=90)
    return A.analyze_transcription(transcript, {
        "estatus_grabacion": "NO DEFINE FECHA DE PAGO", "asignacion": "C4",
        "saldo_total": "60000", "pago_minimo": "3000", "fecha": "2026-10-14", **context})


@pytest.mark.parametrize("offer", [
    "Se le está ofreciendo un descuento para finiquitar la deuda, le están pidiendo 3100 pesos.",
    "Le ofrecemos una opción para liquidar lo que ya es la cuenta por 3100 pesos con descuento.",
    "Le ofrezco un descuento para liquidar su cuenta por 3100 pesos, ¿lo acepta?",
])
def test_settlement_offer_uses_the_mora_minimum_reference(offer):
    a = analyze_offer(offer)
    n = a.metadata["negotiation_validation"]
    assert n["total_liquidation_wording"]
    assert n["monto_detectado"] == 3100
    assert n["validacion_monto"] == "VALIDA - MINIMO DE LIQUIDACION SEGUN MORA"
    assert not n["commitment_confirmed"]
    assert a.metadata["status_validation"]["detected_status"] == "NO DEFINE FECHA DE PAGO"
    assert a.metadata["shared_classification"]["clasificacion"] == "APROBADO"


def test_split_whisper_windows_do_not_hide_the_settlement_offer():
    offer = "Se le está ofreciendo un descuento para finiquitar la deuda, le están pidiendo 3100 pesos."
    a = analyze_offer(offer, _segments=[
        {"text": "Se le está ofreciendo un descuento para", "start": 2, "end": 4},
        {"text": "finiquitar la deuda, le están pidiendo 3100 pesos.", "start": 4, "end": 8}])
    n = a.metadata["negotiation_validation"]
    assert n["total_liquidation_wording"] and n["monto_detectado"] == 3100
    assert n["validacion_monto"] == "VALIDA - MINIMO DE LIQUIDACION SEGUN MORA"


@pytest.mark.parametrize("offer", [
    "Titular: Me dijeron que se le está ofreciendo un descuento para finiquitar la deuda por 3100 pesos.",
    "Me dijeron que se le está ofreciendo un descuento para finiquitar la deuda por 3100 pesos.",
    "Gestor: No se le está ofreciendo un descuento para finiquitar la deuda por 3100 pesos.",
    "Titular: Le ofrecemos un descuento para finiquitar la deuda por 3100 pesos.",
    "Gestor: Le ofrecemos una opción para cubrir la mensualidad vencida por 3100 pesos.",
])
def test_customer_history_negative_offer_and_monthly_due_are_not_new_total_settlements(offer):
    assert not analyze_offer(offer).metadata["negotiation_validation"]["total_liquidation_wording"]


def test_settlement_offer_stays_forbidden_in_restricted_assignment():
    a = analyze_offer("Le ofrecemos un descuento para finiquitar la deuda por 3100 pesos.", asignacion="1PV")
    assert "PEN004" in {p["id"] for p in a.metadata["penalties"]}
    assert a.metadata["shared_classification"]["clasificacion"] == "FALLA_GRAVE"


@pytest.mark.parametrize("answer", [
    "Pues mañana no, sería, lo podría hasta el sábado.",
    "Lo podría hacer el sábado.",
    "Si yo pagaría el sábado, yo pago completo.",
])
def test_conditional_payment_date_does_not_confirm_an_agreement(answer):
    a = A.analyze_transcription(TranscriptionModel("synthetic.wav", "synthetic.wav",
        "Habla MRS. Soy yo. Le ofrecemos una opción de pago de 900 pesos. " + answer,
        duration_seconds=90), {"estatus_grabacion": "NO DEFINE FECHA DE PAGO", "fecha": "2026-10-13"})
    n = a.metadata["negotiation_validation"]
    assert not n["commitment_confirmed"]
    assert a.metadata["status_validation"]["detected_status"] == "NO DEFINE FECHA DE PAGO"


def test_later_firm_acceptance_can_supersede_conditional_payment():
    c = payment_commitment("Le ofrecemos una opción de pago. Lo podría hacer el sábado. "
                           "Me comprometo a pagar 1000 pesos mañana.")
    assert c["accepted"]


def test_unrelated_podria_without_payment_context_is_not_a_payment_event():
    assert not payment_commitment("Lo podría revisar el sábado.").get("conditional")


def test_known_agent_conditional_is_not_a_customer_response():
    assert not payment_commitment("Gestor: Le ofrecemos una opción de pago. Lo podría hacer el sábado.").get("conditional")
