"""Regresiones de integridad sin alterar las reglas de calidad r51."""
from app.services.status_output_label import corrected_status_label
from app.services.account_source_validation import validate_account_source


def _metadata(old_status, detected_status, code, card="4812820090495012"):
    name = f"{card}_CANAL_GESTOR_{code}_FECHA_SUPERVISOR_OTRO"
    return {
        "operational_context": {"numero_de_tarjeta": card, "nombre_final": name},
        "status_validation": {
            "excel_status": old_status,
            "detected_status": detected_status,
            "matches": False,
            "detection_confidence": "ALTA",
            "review_required": False,
            "evidence_method": "CONTEXTO_DIALOGO",
            "evidence": "Confirmo el recado",
        },
    }


def test_ref1_to_family_is_equivalent_not_relabel():
    result = corrected_status_label(_metadata("RECADO REF1", "MENSAJE CON FAMILIAR", "3EROS"))
    assert not result["valid"]
    assert not result["eligible"]


def test_ref2_to_family_is_equivalent_not_relabel():
    result = corrected_status_label(_metadata("RECADO REF2", "MENSAJE CON FAMILIAR", "3EROS"))
    assert not result["valid"]


def test_true_status_change_still_allowed():
    result = corrected_status_label(_metadata("NEGATIVA DE PAGO", "NO DEFINE FECHA DE PAGO", "NP"))
    assert result["valid"] and result["changed"]
    assert result["original_code"] == "NP"
    assert result["corrected_code"] == "TH"
    assert result["corrected_name"].startswith("4812820090495012_")
    assert "_TH_" in result["corrected_name"]


def test_conflicting_account_requires_review():
    relation = {
        "nombre_final": "4812820090495012_CANAL_GESTOR_NP_FECHA_SUPERVISOR_OTRO",
        "numero_de_tarjeta": "4812820090495013",
    }
    result = validate_account_source(relation)
    assert result["review_required"]
    assert relation["nombre_final"].startswith("4812820090495012_")
