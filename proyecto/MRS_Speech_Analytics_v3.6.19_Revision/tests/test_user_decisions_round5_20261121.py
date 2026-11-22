"""Comprobaciones sintéticas para puntos 139, 146, 147 y 145.

La prueba es código añadido, todavía no ejecutado en Windows/pytest.
"""
from app.services.analytics_service import AnalyticsService
from app.models.transcriptions import TranscriptionModel


def analyze(text, status):
    return AnalyticsService.analyze_transcription(
        TranscriptionModel.from_dict({
            "archivo": "regresion.ogg", "texto": text,
            "duracion_segundos": 67,
        }),
        {
            "numero_de_tarjeta": "1234567890123456",
            "nombre_final": "1234567890123456_1PV_352_TH_PERSONA_MRS_20261121",
            "estatus_grabacion": status, "asignacion": "1PV",
            "fecha": "2026-11-21", "vencimiento": "2026-11-30",
            "pago_minimo": "1000", "saldo_total": "3000",
            "corte": "23",
        },
    )


def penalty(analysis, code):
    return [p for p in analysis.metadata["penalties"] if p["id"] == code]


def test_titular_hangup_without_mrs_identification_costs_25_points():
    a = analyze("Gestor: Buenas tardes. Titular: Soy yo. Voy a colgar.",
                "TITULAR CUELGA")
    found = penalty(a, "PEN001")
    assert len(found) == 1
    assert found[0]["points"] == 25
    assert "CUELGUE147" in found[0]["rule_ids"]


def test_accepting_recado_without_any_callback_costs_15_points():
    a = analyze(
        "Gestor: Habla MRS. ¿Le puedo dejar un recado para su hermano? "
        "Tercero: Soy su hermana. Sí, dígame. "
        "Gestor: Dígale que se comunique con nosotros. "
        "Tercero: Entendido, le aviso.",
        "MENSAJE CON FAMILIAR",
    )
    found = penalty(a, "PEN_RECADO_SIN_CONTACTO_RETORNO")
    assert len(found) == 1
    assert found[0]["points"] == 15
    assert not a.metadata["message_workflow_validation"]["callback_available"]


def test_confirmed_repeated_interruption_is_not_old_25_point_penalty():
    a = analyze(
        "Gestor: Habla MRS. Titular: Soy yo. "
        "Titular: Usted no me deja hablar, no me interrumpa. "
        "Titular: Usted me interrumpe y no me permite terminar. "
        "Gestor: Entiendo.",
        "NO DEFINE FECHA DE PAGO",
    )
    found = penalty(a, "PEN_TRATO_INTERRUPCION")
    assert len(found) == 1
    assert found[0]["points"] == 5
