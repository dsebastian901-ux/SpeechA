"""Las excepciones hostiles/lascivas confirmadas nunca entran a otras aprobaciones."""
from app.services.quality_decision import evaluate_quality
import app.services.status_output_label as labels


def test_verified_hostility_stays_in_exception_folder_even_with_corrected_label(monkeypatch):
    monkeypatch.setattr(labels, "corrected_status_label", lambda _: {
        "valid": True, "eligible": True, "reason": "estatus corregido"
    })
    metadata = {
        "hostile_interlocutor_exception": {
            "audio_verified": True, "interlocutor_hostile_or_lascivious": True,
            "prevented_script": True, "agent_professional": True
        }
    }
    decision = evaluate_quality(metadata, 90, minimum_score=80, duration_seconds=120)
    assert decision["clasificacion"] == "APROBADO_CON_EXCEPCION"
    assert decision["output_label_correction"]["valid"]


def test_privacy_uncertainty_still_prevents_exception_approval():
    metadata = {
        "hostile_interlocutor_exception": {
            "audio_verified": True, "interlocutor_hostile_or_lascivious": True,
            "prevented_script": True, "agent_professional": True
        },
        "privacy_validation": {
            "confirmed_disclosure": False,
            "review_required": True,
            "reason": "Hablante sin atribuir durante información financiera"
        },
    }
    assert evaluate_quality(metadata, 90, duration_seconds=120)["clasificacion"] == "REVISAR"
