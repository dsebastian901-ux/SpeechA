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


def test_repeated_suffix_without_two_confirmations_remains_unverified():
    from app.services.analytics_service import AnalyticsService
    context = {"estatus_grabacion": "NO DEFINE FECHA DE PAGO",
               "numero_de_tarjeta": "0000000000005222",
               "asignacion": "1PV", "fecha": "2026-11-20",
               "pago_minimo": 200, "saldo_total": 1000}
    checked = AnalyticsService.calculate_basic_compliance(
        "Gestor: La tarjeta termina en 52 22 22.", context)
    assert checked["card_validation"]["result"] == "REVISAR - NUMERO NO CONFIABLE"


def test_nominal_request_without_me_with_personal_response():
    from app.services.contact_evidence_graph import nominal_requests, contextual_contact
    text = (
        "Gestor: ¿Podrá comunicar con Saúcedo Ramírez María Guadalupe? "
        "Interlocutor: Sí, soy yo. "
        "Gestor: ¿Ya pudo hacer el pago? "
        "Interlocutor: No he podido pagar, estoy sin trabajo."
    )
    assert list(nominal_requests(text))
    assert contextual_contact(text)["confirmed"] is True


def test_estoy_buscando_nominal_does_not_confirm_third_party():
    from app.services.contact_evidence_graph import nominal_requests, contextual_contact
    text = (
        "Gestor: Estoy buscando a Laura Ríos Sánchez. "
        "Tercero: Es mi hermana, no está en casa. "
        "Gestor: ¿Puede realizar el pago? "
        "Tercero: No, yo no puedo."
    )
    assert list(nominal_requests(text))
    assert contextual_contact(text)["confirmed"] is False


def test_word_recado_alone_is_not_evidence_of_third_party():
    from app.services.contact_evidence_graph import nonholder_context
    text = ("Gestor: ¿Me comunica con Aurora Méndez Lara? "
            "Titular: Sí, soy yo. "
            "Gestor: Le comento que ya le dejé un recado la semana pasada. "
            "Titular: Sí, lo recuerdo, mi tarjeta está al corriente.")
    assert nonholder_context(text) is False


def test_declared_relative_still_prevents_holder_inference():
    from app.services.contact_evidence_graph import nonholder_context, contextual_contact
    text = ("Gestor: ¿Me comunica con Aurora Méndez Lara? "
            "Tercero: No soy la persona, soy su hermana. No está. "
            "Gestor: Le dejo un recado para su hermana.")
    assert nonholder_context(text) is True
    assert contextual_contact(text)["confirmed"] is False
