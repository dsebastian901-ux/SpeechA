"""Auditoría de cambios r53 propuestos para revisión de Codex.

Reglas críticas: las excepciones hostiles/lascivas verificadas mantienen
siempre su categoría exclusiva; el reporte no valida una llamada sin Excel.
No se aplican parches sobre codex/entrega-r53 ni sobre la versión en pruebas.
"""
import pytest

from app.services.quality_decision import evaluate_quality
from app.services.classification_policy import APPROVED_RESULTS, corrected_approval
from app.services.batch_report_service import BatchReportService
import app.services.status_output_label as status_output_label


@pytest.mark.parametrize("seconds,correctable", [
    (120, False),
    (120, True),
    (35, False),
    (35, True),
])
def test_verified_exception_is_approved_and_kept_in_exclusive_category(
    monkeypatch, seconds, correctable
):
    monkeypatch.setattr(
        status_output_label,
        "corrected_status_label",
        lambda _: {
            "eligible": correctable,
            "valid": correctable,
            "reason": "estatus ajustable" if correctable else "",
            "corrected_name": "1234567890123456_1PV_352_TH_PERSONA_MRS_20261115"
            if correctable else "",
        },
    )
    metadata = {
        "hostile_interlocutor_exception": {
            "audio_verified": True,
            "interlocutor_hostile_or_lascivious": True,
            "prevented_script": True,
            "agent_professional": True,
        },
        "status_validation": {
            "valid": True,
            "detected_status": "NO DEFINE FECHA DE PAGO",
            "evidence": "Interlocutor: todavía no confirmo una fecha.",
        },
        "negotiation_validation": {"negotiation_attempt_detected": True},
    }
    decision = evaluate_quality(metadata, 90, 80, duration_seconds=seconds)
    assert decision["clasificacion"] == "APROBADO_CON_EXCEPCION"
    assert decision["aprobado"] is False  # Excepción validada, sin copia automática como APROBADO
    assert decision["calidad_aprobada"] is True
    assert decision["clasificacion"] in APPROVED_RESULTS
    assert decision["output_label_correction"]["valid"] is correctable
    assert not corrected_approval(decision)
    # Ni las etiquetas ni la duración anulan la separación de excepciones.
    assert not decision["short_duration_approval"]


def test_uncertain_privacy_blocks_exception_approval():
    metadata = {
        "hostile_interlocutor_exception": {
            "audio_verified": True,
            "interlocutor_hostile_or_lascivious": True,
            "prevented_script": True,
            "agent_professional": True,
        },
        "privacy_validation": {
            "confirmed_disclosure": False,
            "review_required": True,
            "reason": "No se pudo determinar a quién se le dio el dato financiero",
        },
    }
    decision = evaluate_quality(metadata, 95, 80, duration_seconds=120)
    assert decision["clasificacion"] == "REVISAR"
    assert not decision["aprobado"]


def test_excel_missing_is_not_reported_as_compliant_or_validated():
    item = {
        "file_name": "falta_relacion.ogg",
        "status": "completado",
        "relation": None,
        "analytics_metadata": {"final_result": "SIN_RELACION_EXCEL"},
        "analytics": {"compliance_status": "cumple"},
        "compliance_score": 100,
        "classification": {
            "clasificacion": "SIN_RELACION_EXCEL",
            "aprobado": False,
            "calidad_aprobada": False,
            "cumple_puntaje": True,
            "motivo": "Audio no relacionado con el Excel de origen",
        },
    }
    row = BatchReportService._row_from_item(item)
    assert row["Clasificación física"] == "SIN_RELACION_EXCEL"
    assert row["Resultado Calidad"] == "NO VALIDABLE - FALTA RELACION EXCEL"
    assert row["Validación Dictamen"] == "SIN RELACION EXCEL"
