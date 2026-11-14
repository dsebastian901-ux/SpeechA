"""Regresiones: eliminar revisiones falsas sin aprobar divulgaciones a terceros."""
import pytest

from app.services.conversation_evidence import holder_confirmation, assess_privacy
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService


@pytest.mark.parametrize("answer", ["Sí, digamos.", "Sí, diga.", "Sí, ya habló.", "Ya habla."])
def test_nombre_confirmado_con_variantes_asr(answer):
    r = holder_confirmation("¿Me puede comunicar con Persona de Ejemplo? " + answer)
    assert r["confirmed"], answer


def test_respuesta_nominal_seguida_de_tercero_no_confirma_titular():
    r = holder_confirmation(
        "¿Me puede comunicar con Persona de Ejemplo? Sí, digamos. "
        "No está aquí, le paso el recado."
    )
    assert not r["confirmed"]


def test_tres_nacionalidades_vencidas_es_revision_no_aprobacion_automatica():
    text = (
        "Gestor: El señor Gabriel dejó su número como referencia. "
        "Él presenta tres nacionalidades vencidas de la tarjeta C y A Visa."
    )
    r = assess_privacy(text, third_party_confirmed=True, expected_third_party=True)
    assert r["review_required"]
    assert not r["confirmed_disclosure"]


def test_pago_previo_no_es_nuevo_convenio_por_ser_menor_al_minimo():
    text = (
        "Gestor: Buenos días, ¿hablo con Persona de Ejemplo? "
        "Titular: Sí, soy yo. Gestor: ¿Ya realizó su pago? "
        "Titular: Ya pagué mil pesos ayer. Gestor: "
        "Registraré el reporte del pago para evitar más llamadas."
    )
    transcription = TranscriptionModel("previo.wav", "previo.wav", text, duration_seconds=90)
    analysis = AnalyticsService.analyze_transcription(transcription, {
        "estatus_grabacion": "NO DEFINE FECHA DE PAGO",
        "fecha": "2026-11-09", "vencimiento": "2026-11-15",
        "asignacion": "1PV", "pago_minimo": "2941", "saldo_total": "8529", "corte": "12"
    })
    n = analysis.metadata["negotiation_validation"]
    assert n["payment_confirmation_case"]
    assert not n["validacion_monto"].startswith("REVISAR - MONTO MENOR AL MINIMO")
