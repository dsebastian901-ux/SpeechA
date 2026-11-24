"""Regresión de respuesta afirmativa explícita a solicitud nominal de identidad."""
from app.services.conversation_evidence import holder_confirmation


def test_exatamente_after_name_confirms_holder():
    text = ("Gestor: Tengo el gusto con Vargas Mosqueda Luis Angel Antonio. "
            "Titular: Exactamente. Gestor: Mucho gusto, me presento.")
    result = holder_confirmation(text)
    assert result["confirmed"] is True
    assert result["method"] == "RESPUESTA_A_IDENTIFICACION"


def test_exactamente_without_nominal_request_does_not_confirm_holder():
    result = holder_confirmation(
        "Gestor: ¿Está de acuerdo con el pago? Titular: Exactamente.")
    assert result["confirmed"] is False


def test_exactamente_with_third_party_denial_does_not_confirm_holder():
    result = holder_confirmation(
        "Gestor: Tengo el gusto con Luis Angel Antonio. Tercero: Exactamente. "
        "Tercero: Pero no soy el titular, soy su hermano.")
    assert result["confirmed"] is False
