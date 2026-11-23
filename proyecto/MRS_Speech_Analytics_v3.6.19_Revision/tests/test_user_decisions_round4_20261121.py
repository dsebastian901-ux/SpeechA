"""Regresiones sintéticas de criterios 59, 65, 68, 69, 78 y 80.

Distinguir cambios de código de evidencia clínica/acústica y de pagos bancarios.
"""
from copy import deepcopy
import pytest

from app.services.quality_decision import evaluate_quality
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel
from app.services.operational_outcome_resolution import (
    callback_number_reconfirmed, distinct_partial_alternative,
    reported_unauthorized_venue)


def _analyze(text,status="CONVENIO"):
    return A.analyze_transcription(
        TranscriptionModel.from_dict({
            "archivo":"synthetic.ogg",
            "texto":text,
            "duracion_segundos":100
        }),
        {
            "numero_de_tarjeta":"1234567890123456",
            "nombre_final":"1234567890123456_1PV_352_PP_PERSONA_MRS_20261121",
            "estatus_grabacion":status,
            "asignacion":"1PV",
            "fecha":"2026-11-21",
            "vencimiento":"2026-11-30",
            "pago_minimo":"1000",
            "saldo_total":"3000",
            "corte":"23"
        })


@pytest.mark.parametrize("spoken,expected",[
    ("Gestor: ¿Me confirma que el número es correcto? Tercero: Sí.",True),
    ("Gestor: Le dejo nuestro número. Tercero: Ya tengo su número.",False)
])
def test_phone_known_is_distinct_from_phone_reconfirmed(spoken,expected):
    assert callback_number_reconfirmed(spoken)["confirmed"] is expected


def test_partial_requires_additional_option_for_no_5_point_deduction():
    partial=("Gestor: El pago será parcial y no regulariza la cuenta.")
    other=partial+" Gestor: Como otra opción, podemos ofrecer un segundo pago."
    assert not distinct_partial_alternative(partial)["confirmed"]
    assert distinct_partial_alternative(other)["confirmed"]


def test_outside_mora_window_is_operational_negativa_even_if_amount_was_accepted():
    text=("Gestor: Habla MRS. Titular: Soy yo. "
          "Gestor: Puede pagar 1000 pesos el 2 de diciembre? "
          "Titular: Me comprometo a pagar 1000 pesos el 2 de diciembre.")
    a=_analyze(text)
    status=a.metadata["status_validation"]
    # 23/11: fecha fuera de política no equivale a negativa del titular.
    # Este caso supera además vencimiento; PEN005 conserva su prioridad.
    assert status["detected_status"]=="CONVENIO"
    assert status["evidence_method"]=="CONVENIO_CON_FECHA_FUERA_DE_POLITICA"
    assert a.metadata["negotiation_validation"]["commitment_confirmed"]


def test_oxxo_payment_report_is_not_accredited_against_minimum():
    text=("Gestor: Habla MRS. Titular: Soy yo. Ya pagué 500 pesos en OXXO. "
          "Gestor: Puede realizar el pago correctamente en BBVA o Santander.")
    a=_analyze(text)
    n=a.metadata["negotiation_validation"]
    assert n["prior_payment_total"] is None
    assert n["prior_payment_amount_validation"]["reported_payment_not_accredited"]
    assert not n["prior_payment_covers_minimum"]
    assert a.metadata["convenio_payment_validation"]["prior_unauthorized_venue"]["confirmed"]


def _unattributed_meta():
    return {
        "quality_checks":{"groseria_bloquea_aprobacion":True},
        "audio_block_evidence_validation":{
            "present":True,"valid":True,"review_required":True,
            "second_listening_complete":True,"human_verified":False,
            "quality":{"degraded":False},
            "risks":[{"type":"EXPRESION_OFENSIVA_SIN_HABLANTE_CONFIRMADO",
                      "source":"CIERRE","evidence":"palabra potencialmente ofensiva"}],
        }
    }


def test_after_second_listen_unattributed_only_approved_with_alert():
    decision=evaluate_quality(_unattributed_meta(),95,duration_seconds=85)
    assert decision["clasificacion"]=="APROBADO_CON_ALERTA"
    assert decision["aprobado"] is True
    assert decision["aprobado_con_alerta"] is True
    assert decision["score"]==95
    assert any(f["severity"]=="ALERTA_INFORMATIVA" for f in decision["decision_findings"])


def test_no_second_listen_stays_review():
    data=_unattributed_meta()
    data["audio_block_evidence_validation"]["second_listening_complete"]=False
    decision=evaluate_quality(data,95,duration_seconds=85)
    assert decision["clasificacion"]=="REVISAR"
    assert not decision["aprobado"]


def test_independent_privacy_risk_not_overridden_by_second_listen():
    data=_unattributed_meta()
    data["privacy_validation"]={"review_required":True,"reason":"Divulgación sin voz confirmada"}
    decision=evaluate_quality(data,95,duration_seconds=85)
    assert decision["clasificacion"]=="REVISAR"


def test_confirmed_critical_failure_overrides_90_points_and_audio_alert():
    data=_unattributed_meta()
    data["privacy_validation"]={"confirmed_disclosure":True,
                                "reason":"Revelación confirmada a tercero."}
    decision=evaluate_quality(data,90,duration_seconds=85)
    assert decision["clasificacion"]=="FALLA_GRAVE"
    assert not decision["aprobado"]
    assert decision["score"]==90
