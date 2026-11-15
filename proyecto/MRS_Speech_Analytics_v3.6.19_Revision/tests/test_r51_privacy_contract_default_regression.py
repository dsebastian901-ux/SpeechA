"""Regresión de privacidad: «incumplimiento a contrato» ante terceros.

Una variación de la preposición producida por ASR no autoriza un APROBADO.
"""
from app.services.conversation_evidence import sensitive_financial_matches, assess_privacy
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService


def test_contract_default_prepositions_detected():
    for fragment in (
        "incumplimiento a contrato de la tarjeta",
        "incumplimiento al contrato de la tarjeta",
        "incumplimiento del contrato de la tarjeta",
        "incumplimiento de contrato de la tarjeta",
    ):
        assert any("incumplimiento" in match.group()
                   for match in sensitive_financial_matches(fragment)), fragment


def test_third_party_is_not_silently_approved_on_contract_default():
    text = (
        "Gestor: Buenas tardes, ¿me comunica con persona de ejemplo? "
        "Tercero: No se encuentra, soy amigo del trabajo. "
        "Gestor: ¿Le dejo un recado? Tercero: Sí, yo le digo. "
        "Gestor: Dígale que tiene una orden extrajudicial por incumplimiento "
        "a contrato de la tarjeta. Tercero: Yo le digo."
    )
    privacy = assess_privacy(text, third_party_confirmed=True,
                             expected_third_party=True)
    assert privacy["review_required"] or privacy["confirmed_disclosure"]
    t = TranscriptionModel("muestra.wav", "muestra.wav", text, duration_seconds=110)
    result = AnalyticsService.analyze_transcription(t, {
        "estatus_grabacion": "MENSAJE CON TERCERO",
        "asignacion": "1PV", "fecha": "2026-11-09",
        "numero_de_tarjeta": "1234567890123456",
    })
    assert result.metadata["final_result"] in {"REVISAR", "FALLA_GRAVE"}
