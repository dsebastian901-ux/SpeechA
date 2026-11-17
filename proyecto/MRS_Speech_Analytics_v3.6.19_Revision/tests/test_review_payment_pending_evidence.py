"""Casos de r51 sin estatus: evidencia real y no frases aisladas.

Los ejemplos son sintéticos, sin nombres ni datos de cuenta de usuarios.
No son convenios ni prueba de voz acústica; solo acreditan decisión pendiente.
"""
import pytest
from app.services.dialogue_evaluation import scan_dialogue, pending_status


def _pending(text):
    dialogue = scan_dialogue(text)
    return pending_status(dialogue, {"accepted": False, "declined": False})


@pytest.mark.parametrize("text", [
    "Gestor: ¿Podemos contar con su pago hoy? Titular: Lo intentaré.",
    "Gestor: ¿Puede cubrir su pago mínimo mañana? Titular: Voy a intentar.",
    "Titular: Estoy tratando de juntar el dinero para liquidar la deuda, pero no tengo fechas.",
])
def test_real_uncertain_payment_answer_provides_pending_evidence(text):
    result = _pending(text)
    assert result is not None
    assert result["detected_status"] == "NO DEFINE FECHA DE PAGO"
    assert result["evidence"]


@pytest.mark.parametrize("text", [
    "Gestor: ¿Puede anotar nuestro teléfono? Titular: Lo intentaré.",
    "Gestor: Su tarjeta tiene atraso. ¿Puede localizar una pluma? Titular: Lo intentaré.",
    "Titular: No tengo fechas para mis vacaciones.",
    "Gestor: ¿Cuándo puede enviarme el comprobante? Titular: No tengo fechas.",
    "Titular: Voy a intentar encontrar el número de teléfono.",
])
def test_unrelated_logistics_and_dates_must_not_be_called_payment_status(text):
    assert _pending(text) is None


def test_uncertain_phrase_never_overrides_confirmed_agreement():
    dialogue = scan_dialogue(
        "Gestor: ¿Podemos contar con su pago? Titular: Lo intentaré. "
        "Titular: Confirmo que pagaré el próximo viernes."
    )
    assert pending_status(dialogue, {"accepted": True, "declined": False}) is None


# Errores P2 confirmados por Codex; el texto financiero incidental
# nunca transforma vacaciones ni conseguir una pluma en decisión de pago.
@pytest.mark.parametrize("text", [
    "Gestor: ¿Podemos contar con su pago hoy? "
    "Titular: Antes necesito anotar el teléfono para aclarar mi pago, "
    "voy a intentar encontrar una pluma.",
    "Titular: No tengo fechas para mis vacaciones, el pago de mi tarjeta "
    "está al corriente.",
    "Gestor: ¿Podemos contar con su pago hoy? "
    "Titular: Voy a intentar encontrar mi comprobante por WhatsApp.",
    "Gestor: ¿Podemos contar con su pago hoy? "
    "Titular: Lo intentaré, necesito anotar el número de teléfono.",
])
def test_codex_p2_no_false_payment_status_from_logistics(text):
    assert _pending(text) is None
