"""Puerta única para no confundir falta de Excel con problemas del audio.

En modo AUDIOS + EXCEL un registro ausente invalida aprobar/reetiquetar:
no se conocen datos de cuenta, gestor, supervisor, estatus ni referencias.
La clasificación de calidad anterior queda registrada como PROVISIONAL.
Fallas graves confirmadas por el contenido se conservan como FALLA_GRAVE.
En modo SOLO AUDIOS NO aplica esta puerta.
"""
from __future__ import annotations

from copy import deepcopy


SOURCE_MISSING_CATEGORY = "SIN_RELACION_EXCEL"
SOURCE_MISSING_REASON = (
    "El audio no tiene registro correspondiente en el Excel de relación. "
    "No es posible aprobar, reetiquetar o dar por validada la cuenta; "
    "se requiere corregir la fuente de datos, no retranscribir el audio."
)


def enforce_excel_source(classification, relation, *, excel_required):
    """Devolver nueva decisión sin alterar el dictamen de calidad original."""
    decision = deepcopy(classification if isinstance(classification, dict) else {})
    # El lote nuevo usa RelationRecord (dataclass); el reanálisis usa dict.
    # No confundir un registro válido con una relación ausente.
    if isinstance(relation, dict):
        has_relation = bool(relation.get("archivo_original"))
    else:
        has_relation = bool(getattr(relation, "archivo_original", None))
    if not excel_required or has_relation:
        return decision
    preliminary = str(decision.get("clasificacion") or "REVISAR").upper()
    decision["preliminary_classification"] = preliminary
    decision["source_data_status"] = "SIN_RELACION_EXCEL"
    decision["source_data_blocked"] = True
    decision["source_data_reason"] = SOURCE_MISSING_REASON
    decision["aprobado"] = False
    decision["calidad_aprobada"] = False
    # No ocultar una falta grave efectivamente confirmada en el audio.
    # Las faltas no críticas y puntajes sin Excel continúan preliminares.
    if preliminary != "FALLA_GRAVE":
        decision["clasificacion"] = SOURCE_MISSING_CATEGORY
    decision["motivo"] = SOURCE_MISSING_REASON + (
        " | Hallazgo crítico preservado." if preliminary == "FALLA_GRAVE" else ""
    )
    decision["rechazo_automatico_por_puntaje"] = False
    decision["rechazo_automatico_por_reglas"] = False
    return decision
