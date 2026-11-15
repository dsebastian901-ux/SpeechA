"""Regresiones SISTEMICAS detectadas en el checkpoint de 207 llamadas.

No infiere que una falta es grave sin evidencia de quién pronunció la frase.
No permite que un tercero confirmado por su propio nombre se vuelva titular.
"""
import pytest

from app.services.conversation_evidence import (
    holder_confirmation, nominee_conflict_with_confirmed_name,
    sensitive_financial_matches, assess_privacy,
)
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService


def test_quantified_mora_mentioned_to_relative_is_never_silent():
    phrase = ("Le pido que se comunique para tratar el atraso de más "
              "de siete meses que presenta su tarjeta.")
    matches = [m.group() for m in sensitive_financial_matches(phrase)]
    assert matches, "Divulgación cuantitativa omitida"
    privacy = assess_privacy(phrase, third_party_confirmed=True,
                             expected_third_party=True)
    assert privacy["review_required"] or privacy["confirmed_disclosure"]


def test_different_named_receiver_is_not_titular():
    text = (
        "¿Me puede comunicar con Bautista Romero Jonathan? "
        "Eh, está equivocado. No lo he visto. Se lo dejo. "
        "Tengo el gusto con el caballero Jesús Omar López, ¿correcto? Sí. "
        "En caso de que lo vea le deja el recado."
    )
    initial = holder_confirmation(text)
    assert initial["confirmed"]
    assert nominee_conflict_with_confirmed_name(text, initial)["conflict"]
    a = AnalyticsService.analyze_transcription(
        TranscriptionModel.from_dict({"archivo": "dos_nombres.ogg",
                                      "texto": text, "duracion_segundos": 105}),
        {"estatus_grabacion": "RECADO REF1", "asignacion": "1PV"})
    assert a.metadata["quality_contact_type"] != "TITULAR"
    assert a.metadata["contact_conflict_validation"]["review_required"]


def test_same_named_person_is_not_a_nominal_conflict():
    text = (
        "¿Me puede comunicar con López García Ana? "
        "Tengo el gusto con la señora Ana López García, ¿correcto? Sí."
    )
    first = holder_confirmation(text)
    assert first["confirmed"]
    assert not nominee_conflict_with_confirmed_name(text, first)["conflict"]


def test_terminal_mexican_profanity_blocks_approval_without_voice_attribution():
    text = ("Bueno. Tengo el gusto con Flor Pérez. "
            "Sí, pero yo no soy Flor Pérez. "
            "No me hables así, hija culera, váyase a la verga.")
    result = AnalyticsService.analyze_transcription(
        TranscriptionModel.from_dict({"archivo": "groseria_final.ogg",
                                      "texto": text, "duracion_segundos": 70}),
        {"estatus_grabacion": "SE NIEGAN A TOMAR RECADO"})
    flags = result.metadata["quality_checks"]
    assert flags["groseria_bloquea_aprobacion"]
    assert flags["insultos_detectados"]
    assert not result.metadata["shared_classification"]["aprobado"]
    assert result.metadata["shared_classification"]["clasificacion"] != "APROBADO_CON_EXCEPCION"


def test_specific_future_payment_offer_is_an_attempt():
    text = (
        "Buen día, ¿hablo con Juan López? Sí, soy yo. "
        "Le hablo de MRS en representación de Bradescard. "
        "¿Ya tendrá su pago para hoy? ¿Podríamos contar con su pago? "
        "Se le está solicitando el pago para el día de hoy."
    )
    result = AnalyticsService.analyze_transcription(
        TranscriptionModel.from_dict({"archivo": "cobranza.ogg",
                                      "texto": text, "duracion_segundos": 100}),
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO", "asignacion": "1PV"})
    assert result.metadata["negotiation_validation"]["negotiation_attempt_detected"]
    assert not result.metadata["negotiation_validation"]["missing_collection_attempt_penalty"]


@pytest.mark.parametrize("phrase", [
    "Atraso de más de siete meses que presenta su tarjeta.",
    "Tiene un atraso de tres meses en la cuenta.",
    "El atraso de 6 meses que registra la tarjeta.",
])
def test_reverse_overdue_months_are_sensitive(phrase):
    assert sensitive_financial_matches(phrase)


def test_single_missing_status_is_one_blocker_not_two():
    from app.services.quality_decision import evaluate_quality
    m = {
        "quality_contact_type": "TITULAR",
        "negotiation_validation": {"valid": True},
        "status_validation": {
            "excel_status": "CONVENIO", "detected_status": "",
            "matches": None, "valid": False,
            "review_required": True,
            "reasons": ["No se determinó estatus a partir del diálogo"],
        },
    }
    d = evaluate_quality(m, 90, 80, duration_seconds=95)
    codes = [f["code"] for f in d["decision_findings"]]
    assert d["clasificacion"] == "REVISAR"
    assert codes.count("STATUS_INVALID") == 1
    assert "STATUS_NOT_CONFIRMED" not in codes
