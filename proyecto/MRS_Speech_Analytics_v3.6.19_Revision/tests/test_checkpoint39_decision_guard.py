"""Regresiones de seguridad extraídas de problemas reales del lote r65 de 39.

No contienen datos de titulares ni permiten aprobar por una etiqueta Excel.
"""
from app.services.quality_decision import evaluate_quality


def _status_case(*, excel="CONVENIO", detected="NO DEFINE FECHA DE PAGO",
                 amount=True, date=True, attempt=True):
    return {
        "quality_contact_type": "TITULAR",
        "status_validation": {
            "excel_status": excel, "detected_status": detected,
            "valid": False, "matches": False,
            "detection_confidence": "ALTA",
        },
        "negotiation_validation": {
            "amount_confirmed": amount,
            "payment_date_confirmed": date,
            "promise_date": "2026-11-20" if date else None,
            "negotiation_attempt_detected": attempt,
            "commitment_evidence": {"accepted": True},
        },
    }


def test_convenio_with_confirmed_amount_date_cannot_be_approved_as_no_define():
    metadata = _status_case()
    outcome = evaluate_quality(metadata, score=100, minimum_score=80)
    assert outcome["clasificacion"] == "REVISAR"
    assert "CONVENIO_OUTCOME_CONFLICT" in {
        f["code"] for f in outcome["decision_findings"]
    }


def test_convenio_status_contradiction_blocks_even_at_exactly_80():
    outcome = evaluate_quality(_status_case(), score=80, minimum_score=80)
    assert outcome["clasificacion"] == "REVISAR"


def test_asset_coercion_review_has_priority_over_minor_failure(monkeypatch):
    # La falta mínima de calendario es independiente de la presión para
    # vender bienes o de una penalización adicional no corroborada.
    from app.services import minor_failure_policy
    monkeypatch.setattr(
        minor_failure_policy, "confirmed_minor_failure",
        lambda metadata: {
            "rule_group": 12,
            "code": "CONFIRMED_MINOR_FAILURE",
            "severity": "CONFIRMED_NONCRITICAL",
            "source_field": "negotiation_validation",
            "reasons": ["Fecha fuera de plazo"],
        },
    )
    metadata = {
        "treatment_validation": {
            "asset_pressure_review": True,
            "asset_pressure_evidence": [
                "tiene muebles tiene bienes ... venderlas empenarlas",
            ],
        },
    }
    result = evaluate_quality(metadata, score=100, minimum_score=80)
    assert result["clasificacion"] == "REVISAR"
    assert "ASSET_COERCION_REVIEW" in {
        f["code"] for f in result["decision_findings"]
    }


def test_no_asset_pressure_does_not_create_false_review():
    metadata = {"treatment_validation": {"asset_pressure_review": False}}
    result = evaluate_quality(metadata, score=100, minimum_score=80)
    assert "ASSET_COERCION_REVIEW" not in {
        f["code"] for f in result["decision_findings"]
    }
