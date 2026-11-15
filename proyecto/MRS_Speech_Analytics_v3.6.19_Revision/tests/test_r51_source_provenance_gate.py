"""La procedencia del Excel es un requisito de confianza independiente del score."""
from copy import deepcopy
from app.services.relation_service import RelationRecord
from app.services.source_validation_gate import enforce_excel_source


def test_missing_excel_100_points_never_approved():
    initial = {"clasificacion": "APROBADO_SIN_ETIQUETAR", "aprobado": True,
               "calidad_aprobada": True, "score": 100, "motivo": "cumple"}
    before = deepcopy(initial)
    resolved = enforce_excel_source(initial, None, excel_required=True)
    assert initial == before
    assert resolved["clasificacion"] == "SIN_RELACION_EXCEL"
    assert not resolved["aprobado"]
    assert not resolved["calidad_aprobada"]
    assert resolved["preliminary_classification"] == "APROBADO_SIN_ETIQUETAR"


def test_normal_relation_record_keeps_approval():
    relation = RelationRecord(archivo_original="audio.ogg", gestor="gestor",
                             estatus_grabacion="CONVENIO")
    initial = {"clasificacion": "APROBADO", "aprobado": True}
    assert enforce_excel_source(initial, relation, excel_required=True) == initial


def test_checkpoint_relation_dict_keeps_approval():
    initial = {"clasificacion": "APROBADO", "aprobado": True}
    relation = {"archivo_original": "audio.ogg", "estatus_grabacion": "CONVENIO"}
    assert enforce_excel_source(initial, relation, excel_required=True) == initial


def test_audio_only_mode_does_not_require_excel():
    initial = {"clasificacion": "APROBADO", "aprobado": True}
    assert enforce_excel_source(initial, None, excel_required=False) == initial


def test_confirmed_critical_failure_visible_even_without_source():
    initial = {"clasificacion": "FALLA_GRAVE", "aprobado": False, "score": 0}
    resolved = enforce_excel_source(initial, {}, excel_required=True)
    assert resolved["clasificacion"] == "FALLA_GRAVE"
    assert resolved["source_data_blocked"]
    assert resolved["preliminary_classification"] == "FALLA_GRAVE"


def test_low_score_without_excel_is_not_final_quality_rejection():
    initial = {"clasificacion": "NO_APROBADO_MENOR_80", "aprobado": False, "score": 50}
    resolved = enforce_excel_source(initial, None, excel_required=True)
    assert resolved["clasificacion"] == "SIN_RELACION_EXCEL"
    assert resolved["score"] == 50
    assert resolved["preliminary_classification"] == "NO_APROBADO_MENOR_80"
