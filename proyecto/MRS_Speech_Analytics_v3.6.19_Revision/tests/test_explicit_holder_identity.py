"""Un titular que menciona familiares sigue siendo el interlocutor titular."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService
from app.services.conversation_evidence import assess_recado


@pytest.mark.parametrize("relative", ["es mi esposa", "es mi madre", "es mi hijo"])
def test_explicit_holder_mentioning_relative_does_not_become_third_party(relative):
    text = (f"Titular: Soy el titular. Ella {relative}, me ayuda con el pago.\n"
            "Gestor: Habla MRS. Confirmo su convenio. Puede pagar en Chedraui y Farmacias del Ahorro. "
            "Envíe su comprobante por WhatsApp.\n"
            "Titular: Me comprometo a pagar 600 pesos el 23 de octubre de 2026.")
    t = TranscriptionModel("synthetic.wav", "synthetic.wav", text, duration_seconds=90)
    a = AnalyticsService.analyze_transcription(t, {
        "estatus_grabacion": "CONVENIO", "fecha": "2026-10-20", "vencimiento": "2026-10-25",
        "asignacion": "1PV", "pago_minimo": "500", "saldo_total": "2000", "corte": "17"})
    assert a.metadata["quality_contact_type"] == "TITULAR"
    assert "PEN010" not in {p["id"] for p in a.metadata["penalties"]}
    assert a.metadata["status_validation"]["detected_status"] == "CONVENIO"


def test_explicit_holder_cannot_supply_family_recado_acceptance():
    r = assess_recado("Titular: Es mi esposa. Le paso el recado.")
    assert not r["family"]
    assert not r["acceptance"]


def test_real_family_recipient_is_retained():
    r = assess_recado("Familiar: Es mi esposa. Le paso el recado.")
    assert r["family"] and r["acceptance"]
