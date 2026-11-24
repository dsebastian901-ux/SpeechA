"""Regresión: instrucciones de envío de comprobante en segunda persona (ASR MX)."""
import pytest

from app.services.operational_script_evidence import receipt_request_evidence


@pytest.mark.parametrize("message", [
    "Gestor: Una vez que realices tu pago, mandas tu comprobante por WhatsApp.",
    "Gestor: Cuando termines, envías tu comprobante al WhatsApp indicado.",
])
def test_second_person_receipt_instruction_is_confirmed(message):
    evidence = receipt_request_evidence(message)
    assert evidence["requested"] is True
    assert evidence["review_required"] is False
    assert evidence["request_evidence"]
    assert evidence["channel"] == "WHATSAPP"


@pytest.mark.parametrize("message", [
    "Gestor: No mandas tu comprobante por WhatsApp.",
    "Gestor: No envías tu comprobante por WhatsApp.",
    "Gestor: Dice que mandas tu comprobante por WhatsApp.",
])
def test_negated_or_reported_second_person_is_not_a_request(message):
    evidence = receipt_request_evidence(message)
    assert evidence["requested"] is False
