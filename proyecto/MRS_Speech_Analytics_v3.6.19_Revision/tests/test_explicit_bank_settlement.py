import pytest
from app.services.analytics_service import AnalyticsService as A

OFFER='El banco le está proporcionando un descuento para realizar una liquidación con un pago único por la cantidad de 3000 pesos.'


def analyze(text,mora='C4'):
    return A.calculate_basic_compliance(text,{'asignacion':mora,'pago_minimo':2000,'saldo_total':5000,
        'fecha':'2026-11-09','vencimiento':'2026-11-30','estatus_grabacion':'NO DEFINE FECHA DE PAGO'})


def test_present_bank_offer_is_collection_attempt_without_demanding_acceptance():
    m=analyze('Habla MRS. Soy yo. '+OFFER+' No puedo pagar hoy.')
    assert m['negotiation_validation']['negotiation_attempt_detected']
    assert not m['negotiation_validation']['missing_collection_attempt_penalty']


def test_confirmed_bank_settlement_does_not_waive_first_arrears_prohibition():
    m=analyze('Habla MRS. Soy yo. '+OFFER,'1PV')
    assert any(p['id']=='PEN004'for p in m['penalties'])


@pytest.mark.parametrize('text',[
    'Me dijeron que '+OFFER,
    'Titular: '+OFFER,
    'Diga que '+OFFER,
    OFFER.replace('le está proporcionando','no le está proporcionando'),
])
def test_historical_other_speaker_hypothetical_and_negative_offers_are_not_confirmed(text):
    m=analyze(text,'1PV')
    assert not any(p['id']=='PEN004'for p in m['penalties'])
