"""Dictaminar error confirmado sin ocultar dudas independientes."""
from copy import deepcopy

from app.services.quality_decision import evaluate_quality


def sample():
    return {
        'quality_contact_type': 'TERCERO / FAMILIAR',
        'privacy_validation': {'review_required': False},
        'negotiation_validation': {'valid': True, 'review_required': False},
        'status_validation': {
            'excel_status': 'MENSAJE CON TERCERO',
            'detected_status': 'MENSAJE CON FAMILIAR',
            'matches': False, 'valid': False, 'review_required': False,
            'detection_confidence': 'ALTA',
            'evidence': 'Sí, lo anoto, dígale que se comunique al 5551234567',
            'evidence_method': 'RECADO_ACEPTADO_CON_CONTACTO',
            'reasons': ['Parentesco familiar demostrado, pero Excel señala tercero'],
        },
    }


def test_confirmed_family_status_mismatch_is_mal_dictaminado():
    result = evaluate_quality(sample(), 100, minimum_score=80, duration_seconds=125)
    assert result['clasificacion'] == 'MAL_DICTAMINADO'
    assert not result['aprobado']


def test_missing_human_safe_evidence_remains_review():
    for changes in (
        {'detection_confidence': 'MEDIA'},
        {'evidence': ''},
        {'evidence_method': 'SIN_COMPROMISO_FIRME_RESPUESTA_EXPLICITA'},
        {'review_required': True},
    ):
        data = sample()
        data['status_validation'].update(changes)
        result = evaluate_quality(data, 100, minimum_score=80, duration_seconds=125)
        assert result['clasificacion'] == 'REVISAR'


def test_uncertain_privacy_takes_priority_over_status_mismatch():
    data = deepcopy(sample())
    data['privacy_validation'] = {
        'review_required': True, 'reason': 'Riesgo a tercero no atribuido'
    }
    result = evaluate_quality(data, 100, minimum_score=80, duration_seconds=125)
    assert result['clasificacion'] == 'REVISAR'
