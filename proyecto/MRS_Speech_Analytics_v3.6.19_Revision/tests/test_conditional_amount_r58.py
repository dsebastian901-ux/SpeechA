"""Regresión del diálogo de pago con fecha sin confirmar.

Caso inspirado en una frase transcrita, sin datos ni audios de clientes.
"""
import pytest

from app.services.payment_lifecycle import payment_decision_events


@pytest.mark.parametrize("reply", [
    "Voy a ver cuánto puedo juntar.",
    "Voy a revisar cuánto podría pagar.",
])
def test_pending_amount_search_is_not_an_accepted_payment(reply):
    text = "Gestor: ¿Cuánto podría pagar hoy?\nTitular: " + reply
    events = payment_decision_events(text)
    assert any(e["conditional"] and not e["accepted"] and not e["declined"]
               and "voy a" in e["decision_phrase"] for e in events)


@pytest.mark.parametrize("text", [
    "Gestor: Voy a ver cuánto puedo juntar.\nTitular: Gracias.",
    "Titular: Me dijeron que voy a ver cuánto puedo juntar.",
    "Titular: Si fuera yo, voy a ver cuánto puedo juntar.",
])
def test_reported_or_non_holder_pending_amount_is_not_a_new_commitment(text):
    events = payment_decision_events(text)
    assert not any("voy a" in e["decision_phrase"] and e["conditional"] for e in events)
