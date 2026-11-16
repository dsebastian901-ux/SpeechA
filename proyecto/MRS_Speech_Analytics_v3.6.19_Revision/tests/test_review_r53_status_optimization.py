"""Regresiones de causas comunes, sin utilizar audios privados del lote.

Mantener aprobación/bloqueo de seguridad independiente de inferencias textuales:
preguntar por pago futuro es un INTENTO, no una promesa del titular.
"""
import pytest

from app.services.collection_attempt_evidence import collection_request_question
from app.services.conversation_evidence import payment_commitment
from app.services.dialogue_evaluation import scan_dialogue, pending_status
from app.services.quality_decision import evaluate_quality
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService


@pytest.mark.parametrize("phrase", [
    "¿Usted podría realizar su pago de 800 pesos para el día de hoy?",
    "¿Ya tendrá su pago para mañana?",
    "¿Podríamos contar con el pago?",
    "¿Se confirma su pago para hoy?",
])
def test_future_payment_question_is_attempt_not_agreement(phrase):
    text = "Gestor: Se requiere cubrir el mínimo de la cuenta. " + phrase
    evidence = collection_request_question(text)
    assert evidence["detected"]
    assert evidence["method"] == "SOLICITUD_DE_PAGO_FUTURO"
    assert not evidence["human_verified"]
    assert not payment_commitment(text)["accepted"]


@pytest.mark.parametrize("phrase", [
    "¿Ya pagó ayer?",
    "¿Me puede enviar su comprobante de pago?",
    "¿Ya quedó reflejado el pago?",
    "¿Tiene la referencia o número de WhatsApp?",
    "El titular dijo que ¿podríamos contar con el pago?",
])
def test_prior_payment_and_quotes_do_not_count_as_new_attempt(phrase):
    assert not collection_request_question("Gestor: " + phrase)["detected"]


def test_future_request_after_previous_receipt_is_still_collection():
    text = (
        "Gestor: Recibimos su comprobante de pago anterior. "
        "¿Usted podría realizar su pago de 800 pesos para el día de hoy?"
    )
    assert collection_request_question(text)["detected"]


def test_role_explicitly_not_agent_does_not_count():
    assert not collection_request_question(
        "Titular: ¿Usted podría realizar su pago de 800 pesos para el día de hoy?"
    )["detected"]


def test_deferred_decision_supported_by_actual_payment_context():
    text = ("¿Podemos confirmar su pago de 800 pesos para mañana? "
            "No, déjeme ver y me habla al rato.")
    events = scan_dialogue(text)["events"]
    assert any(e["kind"] == "PENDING_DECISION" for e in events)
    pending = pending_status({"events": events},
                             {"accepted": False, "declined": False})
    assert pending["detected_status"] == "NO DEFINE FECHA DE PAGO"
    assert pending["evidence"]
    assert not payment_commitment(text)["accepted"]


def test_agent_or_out_of_context_deferral_does_not_set_payment_status():
    for text in (
        "Gestor: Déjeme ver y me habla al rato.",
        "Estamos revisando el número de teléfono. Déjeme ver y me habla al rato.",
    ):
        events = scan_dialogue(text)["events"]
        assert pending_status({"events": events},
                              {"accepted": False, "declined": False}) is None


def test_previously_accepted_agreement_precedes_pending_event():
    text = ("La cuenta tiene un pago pendiente. "
            "Déjeme ver y me habla al rato. Luego confirmo pagar mañana.")
    events = scan_dialogue(text)["events"]
    assert pending_status({"events": events},
                          {"accepted": True, "declined": False}) is None


def test_repeated_missing_status_generates_only_one_blocker():
    metadata = {
        "quality_contact_type": "TITULAR",
        "status_validation": {
            "excel_status": "NO DEFINE FECHA DE PAGO",
            "detected_status": "",
            "matches": None,
            "valid": False,
            "review_required": True,
            "reasons": ["Sin respuesta concluyente del interlocutor"],
        },
    }
    decision = evaluate_quality(metadata, 100, duration_seconds=110)
    codes = [f["code"] for f in decision["decision_findings"]
             if f["severity"] == "REVIEW"]
    assert decision["clasificacion"] == "REVISAR"
    assert codes.count("STATUS_INVALID") == 1
    assert "STATUS_NOT_CONFIRMED" not in codes


def test_full_analysis_recognizes_payment_question_without_15_point_penalty():
    transcript = (
        "Gestor: Buenos días, me comunico de MRS Consultores en "
        "representación de Bradescard. ¿Hablo con Luis Ejemplo? "
        "Titular: Sí, soy yo. Gestor: ¿Usted podría realizar su pago "
        "de 800 pesos para el día de hoy? Titular: Hoy no puedo pagar."
    )
    model = TranscriptionModel.from_dict({
        "archivo": "prueba_ficticia.ogg", "texto": transcript,
        "duracion_segundos": 120,
    })
    analysis = AnalyticsService.analyze_transcription(model, {
        "estatus_grabacion": "NO DEFINE FECHA DE PAGO",
        "asignacion": "1PV",
        "fecha": "2026-11-15",
        "numero_de_tarjeta": "1234567890123456",
        "pago_minimo": "800",
    })
    meta = analysis.metadata
    assert meta["negotiation_validation"]["negotiation_attempt_detected"]
    assert not meta["negotiation_validation"]["missing_collection_attempt_penalty"]
    assert "PEN_SIN_INTENTO_NEGOCIACION" not in {
        p["id"] for p in meta["penalties"]
    }
    assert not meta["negotiation_validation"]["commitment_evidence"]["accepted"]


def test_codex_review_historical_payment_question_is_not_new_collection():
    # Cobro ya efectuado; pedir confirmación de ese mismo depósito no basta.
    text = (
        "Titular: Ayer pagué 100 pesos. "
        "Gestor: ¿Podríamos contar con el pago que realizó ayer?"
    )
    assert not collection_request_question(text)["detected"]


def test_codex_review_historical_plus_real_future_question_detects_future():
    text = (
        "Gestor: ¿Podríamos contar con el pago que realizó ayer? "
        "Gestor: ¿Ya tendrá su pago para mañana?"
    )
    e = collection_request_question(text)
    assert e["detected"] and e["method"] == "SOLICITUD_DE_PAGO_FUTURO"


def test_codex_review_note_taking_not_a_payment_decision():
    text = (
        "Gestor: Le llamo sobre su tarjeta. "
        "Gestor: ¿Puede anotar el teléfono? "
        "Titular: Déjeme revisar dónde tengo una pluma y me habla al rato."
    )
    events = scan_dialogue(text)["events"]
    assert not any(e["kind"] == "PENDING_DECISION" for e in events)
    assert pending_status(
        {"events": events}, {"accepted": False, "declined": False}
    ) is None


def test_short_deferred_response_needs_actual_payment_question():
    text = (
        "Gestor: ¿Podría pagar 800 pesos mañana? "
        "Titular: No, déjeme ver y me habla al rato."
    )
    events = scan_dialogue(text)["events"]
    assert any(e["kind"] == "PENDING_DECISION" for e in events)
