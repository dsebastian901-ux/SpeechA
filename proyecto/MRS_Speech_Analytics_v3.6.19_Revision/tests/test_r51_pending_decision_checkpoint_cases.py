"""Decisiones de pago pendientes detectadas en checkpoint de 207 audios.

Pruebas sin Whisper; las declaraciones no constituyen convenios aceptados.
La ausencia de fecha/compromiso no basta por sí sola para inventar NO DEFINE.
"""
import pytest

from app.services.dialogue_evaluation import scan_dialogue, pending_status


@pytest.mark.parametrize("answer", [
    "No, pues déjeme ver y me habla al rato.",
    "No, voy a ver cuánto puedo juntar.",
    "Ok, mire déjenme, casi le puedo regresar la llamada en unos 20 minutos.",
])
def test_clear_deferred_payment_reply_has_actual_evidence(answer):
    text = (
        "Me comunico de MRS en representación de Bradescard. "
        "El motivo es el pago pendiente de su cuenta. "
        "¿Podemos confirmar su pago para mañana? " + answer
    )
    dialogue = scan_dialogue(text)
    events = [e for e in dialogue["events"] if e["kind"] == "PENDING_DECISION"]
    assert events, (answer, dialogue)
    result = pending_status(dialogue, {"accepted": False, "declined": False})
    assert result["detected_status"] == "NO DEFINE FECHA DE PAGO"
    assert result["evidence"] and result["method"] == "PENDING_DECISION"


@pytest.mark.parametrize("unrelated", [
    "¿Puede revisar el estado de mi cuenta? Sí.",
    "Gestor: Déjeme ver y le llamo después.",
    "¿Me puede pasar el número de WhatsApp? Sí, déjeme ver.",
    "Mi madre me llamó al rato.",
])
def test_no_generic_deferral_without_payment_reply(unrelated):
    dialogue = scan_dialogue("Buenas tardes, llamo del corporativo. " + unrelated)
    assert pending_status(dialogue, {"accepted": False, "declined": False}) is None


def test_confirmed_commitment_precedes_older_indecision():
    dialogue = scan_dialogue(
        "La cuenta tiene un pago pendiente. No, voy a ver cuánto puedo juntar. "
        "Al final, me comprometo a pagar el viernes."
    )
    assert pending_status(dialogue, {"accepted": True, "declined": False}) is None


def test_existing_payment_followup_not_reinterpreted_by_a_weak_deferral():
    dialogue = scan_dialogue(
        "Ya hice el pago ayer. Solo quería confirmar que quedó registrado. "
        "Voy a ver cuánto puedo juntar."
    )
    assert pending_status(dialogue, {"accepted": False, "declined": False},
                          payment_followup=True) is None
