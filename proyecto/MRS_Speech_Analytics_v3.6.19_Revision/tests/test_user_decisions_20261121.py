"""Decisiones expresas del área de monitoreo, 21/nov/2026.

Ninguna prueba confunde estatus operativo con la calidad o sustituye audio
humano. Se emplean nombres, tarjetas y conversaciones sintéticas.
"""
from copy import deepcopy

from openpyxl import Workbook
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.batch_service import BatchService
from app.services.batch_report_service import BatchReportService
from app.services.classification_policy import corrected_label_exportable
from app.services.context_audio_recovery import needs_recovery
from app.services.conversation_evidence import payment_commitment
from app.services.quality_decision import evaluate_quality
from app.services.retagging_report import add_retagging_sheets

CARD = "1234567890123456"
NAME = CARD + "_1PV_352_PP_PERSONA_MRS_20261121"


def corrected_metadata():
    return {
        "quality_contact_type": "TITULAR",
        "quality_checks": {},
        "critical_failures": [],
        "penalties": [{"id": "PEN001", "points": 30,
                       "reason": "Incumplimiento ordinario confirmado"}],
        "status_validation": {
            "excel_status": "CONVENIO",
            "detected_status": "NO DEFINE FECHA DE PAGO",
            "valid": False, "matches": False, "review_required": False,
            "detection_confidence": "ALTA",
            "evidence_method": "SIN_COMPROMISO_FIRME_RESPUESTA_EXPLICITA",
            "evidence": "Titular: No se cuándo podría pagar.",
            "reasons": ["Estatus distinto con evidencia alta."],
        },
        "operational_context": {"nombre_final": NAME, "numero_de_tarjeta": CARD},
        "negotiation_validation": {"valid": True},
    }


def _relation(status="NO DEFINE FECHA DE PAGO"):
    return {
        "numero_de_tarjeta": CARD, "nombre_final": NAME.replace("_PP_", "_TH_")
        if status == "NO DEFINE FECHA DE PAGO" else NAME,
        "estatus_grabacion": status, "asignacion": "1PV", "corte": "23",
        "fecha": "2026-11-21", "vencimiento": "2026-11-30",
        "pago_minimo": "1000", "saldo_total": "3000",
    }


def _analyze(text, status="NO DEFINE FECHA DE PAGO"):
    return A.analyze_transcription(TranscriptionModel.from_dict({
        "archivo": "sintetico.wav", "texto": text, "duracion_segundos": 90,
    }), _relation(status))


def test_correction_under_80_changes_status_not_quality_or_folder(tmp_path):
    m = corrected_metadata()
    original = deepcopy(m)
    d = evaluate_quality(m, 70, minimum_score=80)
    assert d["clasificacion"] == "NO_APROBADO_MENOR_80"
    assert not d["aprobado"] and not d["calidad_aprobada"]
    assert d["score"] == 70 and d["puntaje_minimo"] == 80
    assert corrected_label_exportable(d)
    assert d["output_label_correction"]["corrected_status"] == "NO DEFINE FECHA DE PAGO"
    assert d["output_label_correction"]["corrected_name"] == NAME.replace("_PP_", "_TH_")
    assert m == original

    source = tmp_path / "sintetico.ogg"
    source.write_bytes(b"OggS audio sintetico inmutable")
    item = {"file_name": source.name, "path": str(source),
            "relation": {"numero_de_tarjeta": CARD, "nombre_final": NAME,
                         "estatus_grabacion": "CONVENIO"},
            "analytics_metadata": m, "classification": d, "status": "completado"}
    batch = BatchService.__new__(BatchService)
    copied = batch._copy_classified_audio(item, None, d, tmp_path / "proyecto" / "Transcripciones")
    from pathlib import Path
    copy = Path(copied)
    assert copy.parent.name == "NO_APROBADOS_MENOR_80"
    assert copy.name == NAME.replace("_PP_", "_TH_") + ".ogg"
    assert copy.read_bytes() == source.read_bytes()

    row = BatchReportService._row_from_item(item)
    assert row["Estatus de salida"] == "NO DEFINE FECHA DE PAGO"
    assert row["Estatus Excel"] == "CONVENIO"
    assert row["Carpeta de etiqueta corregida"] == "NO_APROBADOS_MENOR_80"
    assert row["Clasificación física"] == "NO_APROBADO_MENOR_80"

    book = Workbook()
    detail, _ = add_retagging_sheets(book, [item])
    row2 = dict(zip([c.value for c in detail[1]], [c.value for c in detail[2]]))
    assert row2["Estatus correcto"] == "NO DEFINE FECHA DE PAGO"
    assert row2["Resultado de calidad"] == "NO_APROBADO_MENOR_80"
    book.close()


def test_safety_failure_cannot_be_hidden_by_low_score_relabel():
    m = corrected_metadata()
    m["privacy_validation"] = {"confirmed_disclosure": True}
    d = evaluate_quality(m, 70)
    assert d["clasificacion"] == "FALLA_GRAVE"
    assert not corrected_label_exportable(d)


def test_amount_accepted_without_date_is_no_define_not_convenio():
    text = ("Gestor: Habla MRS. ¿Me puede comunicar con Persona Ejemplo? "
            "Titular: Soy yo. Gestor: ¿Puede confirmar su pago de 1000 pesos? "
            "Titular: Sí voy a pagar 1000 pesos, pero todavía no sé cuándo.")
    commitment = payment_commitment(text)
    assert not commitment["accepted"] and commitment.get("conditional")
    status = _analyze(text).metadata["status_validation"]
    assert status["detected_status"] == "NO DEFINE FECHA DE PAGO"


def test_last_confirmed_payment_agreement_overrides_prior_refusal():
    text = ("Gestor: Habla MRS. ¿Me puede comunicar con Persona Ejemplo? "
            "Titular: Soy yo. Titular: No voy a pagar. "
            "Gestor: ¿Acepta pagar 1000 pesos el 25 de noviembre? "
            "Titular: Me comprometo a pagar 1000 pesos el 25 de noviembre.")
    commitment = payment_commitment(text)
    assert commitment["accepted"] and not commitment["declined"]
    status = _analyze(text, "CONVENIO").metadata["status_validation"]
    assert status["detected_status"] == "CONVENIO"


def test_paid_followup_is_not_an_aclaracion():
    text = ("Gestor: Habla MRS. Titular: Soy yo. Ya pagué 1000 pesos ayer. "
            "Gestor: Envíe su comprobante de pago por WhatsApp.")
    status = _analyze(text).metadata["status_validation"]
    assert status["detected_status"] == "CONVENIO"
    assert status["detected_status"] != "ACLARACION"
    assert status["detected_status"] != "PAGO REPORTADO / ACLARACION"


def test_followup_relabels_no_define_to_convenio_without_changing_quality():
    text = ("Gestor: Habla MRS. Titular: Soy yo. Ya pagué 1000 pesos ayer. "
            "Gestor: Envíe su comprobante de pago por WhatsApp.")
    analysis = _analyze(text, "NO DEFINE FECHA DE PAGO")
    status = analysis.metadata["status_validation"]
    assert status["detected_status"] == "CONVENIO"
    assert status["excel_status"] == "NO DEFINE FECHA DE PAGO"
    assert status["matches"] is False
    assert status["detection_confidence"] == "ALTA"
    assert not status.get("review_required", False)
    assert status["evidence_method"] == "SEGUIMIENTO_PAGO_REPORTADO_CON_COMPROBANTE_SIN_ACREDITACION"


def test_paid_followup_with_prior_convenio_remains_convenio():
    text = ("Gestor: Habla MRS. Titular: Soy yo. Ya pagué 1000 pesos ayer. "
            "Gestor: Envíe su comprobante de pago por WhatsApp.")
    status = _analyze(text, "CONVENIO").metadata["status_validation"]
    assert status["detected_status"] == "CONVENIO"
    assert status["matches"] is True


def test_reported_payment_does_not_relabel_itself_as_an_aclaracion():
    text = ("Gestor: Habla MRS. Titular: Soy yo. Ya pagué 1000 pesos ayer. "
            "Gestor: Envíe su comprobante de pago por WhatsApp.")
    status = _analyze(text, "ACLARACION").metadata["status_validation"]
    assert status["detected_status"] == "CONVENIO"
    assert status["matches"] is False
    assert status["detection_confidence"] == "ALTA"
    assert status.get("review_required") is False


def test_second_listening_of_recado_callback_even_if_score_below_80():
    metadata = {
        "shared_classification": {"clasificacion": "NO_APROBADO_MENOR_80",
                                  "score": 70, "aprobado": False},
        "quality_contact_type": "TERCERO / FAMILIAR",
        "message_workflow_validation": {
            "directed_body": True, "recipient_accepted": True,
            "callback_available": False, "final_refusal": False,
        },
    }
    assert needs_recovery(metadata) == {"callback"}
    metadata["message_workflow_validation"]["callback_available"] = True
    assert needs_recovery(metadata) == set()
    metadata["shared_classification"]["clasificacion"] = "FALLA_GRAVE"
    metadata["message_workflow_validation"]["callback_available"] = False
    assert needs_recovery(metadata) == set()
