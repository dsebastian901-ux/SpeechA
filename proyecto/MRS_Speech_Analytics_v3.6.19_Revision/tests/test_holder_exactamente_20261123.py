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


def test_si_soy_yo_after_full_name_confirms_holder():
    result = holder_confirmation(
        "Gestor: ¿Me puede comunicar con Persona Ejemplo? "
        "Titular: Sí, soy yo.")
    assert result["confirmed"] is True


def test_si_soy_yo_without_nominal_request_does_not_confirm_holder():
    result = holder_confirmation(
        "Gestor: ¿Puede realizar el pago? Titular: Sí, soy yo.")
    assert result["confirmed"] is False


def test_si_soy_yo_with_explicit_third_party_denial_stays_unconfirmed():
    result = holder_confirmation(
        "Gestor: ¿Me puede comunicar con Persona Ejemplo? "
        "Tercero: Sí, soy yo. Tercero: No soy el titular, soy su hermano.")
    assert result["confirmed"] is False


def test_repeated_suffix_requires_two_matching_card_mentions():
    from app.services.analytics_service import AnalyticsService
    context = {"estatus_grabacion": "NO DEFINE FECHA DE PAGO",
               "numero_de_tarjeta": "0000000000005222",
               "asignacion": "1PV", "fecha": "2026-11-20",
               "pago_minimo": 200, "saldo_total": 1000}
    text = ("Gestor: La tarjeta termina en 52-22. "
            "Gestor: Confirmo terminación, 52-22. "
            "Gestor: Repito terminación 52 22 22.")
    checked = AnalyticsService.calculate_basic_compliance(text, context)
    assert checked["card_validation"]["result"] == "TARJETA CORRECTA"
