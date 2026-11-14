"""La falta de compromiso no convierte un 70% en REVISAR por defecto."""
from copy import deepcopy

from app.services.approval_resolution import ordinary_score_rejection
from app.services.quality_decision import evaluate_quality


def sample():
    return {
        'quality_contact_type': 'TITULAR',
        'penalties': [
            {'id': 'PEN_CONV_LUGARES', 'category': 'Negociación', 'points': 20,
             'reason': 'Omitió lugares de pago', 'invalidates': False},
            {'id': 'PEN009', 'category': 'Cierre', 'points': 10,
             'reason': 'Omitió cierre', 'invalidates': False},
        ],
        'critical_failures': [],
        'privacy_validation': {'review_required': False, 'confirmed_disclosure': False},
        'status_validation': {'excel_status': 'CONVENIO', 'detected_status': 'NO DEFINE FECHA DE PAGO',
                              'matches': False, 'valid': False,
                              'reasons': ['Estatus diferente al contenido']},
        'negotiation_validation': {
            'valid': False, 'review_required': True, 'hard_invalid': False,
            'validacion_monto': 'REVISAR - MONTO MENOR AL MINIMO SIN COMPROMISO CONFIRMADO',
            'commitment_evidence': {'accepted': False}, 'promise_date': None,
            'reasons': [
                'Se detectó 3000, menor al mínimo 3185, pero no hay fecha y compromiso suficientemente confirmados para declarar una negociación inválida.'
            ],
        },
    }


def test_below80_with_missing_commitment_uses_no_aprobado_menor_80():
    data = sample()
    assert ordinary_score_rejection(data, 70, 80, 120)
    decision = evaluate_quality(data, 70, 80, 120)
    assert decision['clasificacion'] == 'NO_APROBADO_MENOR_80'
    assert not decision['aprobado']
    assert 'NEGOTIATION_INVALID_OR_UNCERTAIN' in {
        finding['code'] for finding in decision['decision_findings']
    }


def test_privacy_uncertainty_still_requires_review():
    data = sample()
    data['privacy_validation']['review_required'] = True
    assert not ordinary_score_rejection(data, 70, 80, 120)
    assert evaluate_quality(data, 70, 80, 120)['clasificacion'] == 'REVISAR'


def test_hard_invalid_or_unsupported_amount_reason_not_excused():
    for change in ({'hard_invalid': True}, {'reasons': ['El importe negociado supera el saldo total']},
                   {'date_year_rollover_review': True}):
        data = deepcopy(sample())
        data['negotiation_validation'].update(change)
        assert not ordinary_score_rejection(data, 70, 80, 120)


def test_payment_destination_alert_remains_review():
    data = sample()
    data['penalties'].append({
        'id': 'PEN_CONV_TRANSFER_REV', 'category': 'Negociación',
        'points': 0, 'reason': 'Referencia bancaria inconsistente',
    })
    assert not ordinary_score_rejection(data, 70, 80, 120)
