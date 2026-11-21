"""Regresión: la excepción validada no debe perder su categoría exclusiva.

Las confirmaciones son sintéticas; esta prueba no suplanta escucha humana.
"""
from app.services.analytics_service import AnalyticsService as A


FLAGS = {
    "audio_verified": True,
    "interlocutor_hostile_or_lascivious": True,
    "prevented_script": True,
    "agent_professional": True,
}


def _exception_metadata():
    return {
        "hostile_interlocutor_exception": dict(FLAGS),
        "quality_checks": {"groseria_bloquea_aprobacion": True},
        "status_validation": {
            "valid": True,
            "matches": True,
            "excel_status": "NO DEFINE FECHA DE PAGO",
            "detected_status": "NO DEFINE FECHA DE PAGO",
            "evidence": "Titular: Voy a revisar cuanto puedo juntar.",
        },
        "negotiation_validation": {"negotiation_attempt_detected": True},
    }


def test_validated_hostility_short_call_stays_in_exclusive_exception_category():
    """Antes se degradaba a APROBADO_DURACION_MENOR y perdía su carpeta."""
    decision = A.shared_quality_decision(_exception_metadata(), 100, duration_seconds=40)
    assert decision["management_completeness"]["complete"]
    assert decision["clasificacion"] == "APROBADO_CON_EXCEPCION"
    assert decision["calidad_aprobada"] is True
    assert decision["aprobado"] is False
    assert not decision["short_duration_approval"]


def test_validated_hostility_cannot_be_hidden_by_label_correction():
    """El reetiquetado simultáneo no tiene prioridad sobre una excepción."""
    metadata = _exception_metadata()
    metadata["status_validation"].update({
        "valid": False,
        "matches": False,
        "excel_status": "CONVENIO",
        "detected_status": "NO DEFINE FECHA DE PAGO",
        "detection_confidence": "ALTA",
        "evidence_method": "RESPUESTA_EXPLICITA_DE_PAGO",
        "review_required": False,
    })
    metadata["operational_context"] = {
        "numero_de_tarjeta": "1234567890123456",
        "nombre_final": "1234567890123456_1PV_352_PP_PERSONA_MRS_20261115",
    }
    decision = A.shared_quality_decision(metadata, 100, duration_seconds=90)
    assert decision["output_label_correction"]["valid"] is True
    assert decision["clasificacion"] == "APROBADO_CON_EXCEPCION"
    assert decision["aprobado"] is False


def test_unconfirmed_hostility_does_not_become_approved_short_call():
    metadata = _exception_metadata()
    metadata["hostile_interlocutor_exception"]["agent_professional"] = False
    decision = A.shared_quality_decision(metadata, 100, duration_seconds=40)
    assert decision["clasificacion"] == "REVISAR"
