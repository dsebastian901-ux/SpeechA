"""Montos y saldos: casos generales derivados del contraste de audio recibido."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.balance_context_evidence import balance_scope


def analyze(text):
    return A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo':'cuenta_ejemplo.ogg','texto':text,'duracion_segundos':150,'segmentos':[]}),
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO','numero_de_tarjeta':'1234567890123456',
         'asignacion':'C3','fecha':'2026-11-09','vencimiento':'2026-11-30',
         'pago_minimo':'1500','saldo_total':'6000'}).metadata


def test_a_generic_balance_notice_does_not_turn_callback_digits_into_money():
    text=('Habla MRS. Soy yo. Podemos conciliar el saldo. ¿Tiene dónde anotar? '
          'Permítame tantito. ¿Qué número es? Es 7.22. 9, 6, 2. 13, 0, 0. '
          'Nos quedamos en espera de su llamada.')
    result=analyze(text)['negotiation_validation']
    assert result['saldo_informado_detectado'] is None
    assert result['monto_detectado'] is None
    assert not result['monto_normalizado_asr']


@pytest.mark.parametrize('prefix',[
    'Ahorita me decían un saldo de ',
    'Me habían comentado un saldo total de ',
    'En la otra llamada me dijeron un saldo de ',
])
def test_reported_balance_is_not_attributed_to_the_current_collector(prefix):
    text=prefix+'cuatro mil pesos.'
    start=text.index('cuatro')
    assert balance_scope(text,[],start,start+len('cuatro mil pesos')) != 'SALDO_ACTUAL_DECLARADO'
    assert analyze('Habla MRS. Soy yo. '+text)['negotiation_validation']['saldo_informado_detectado'] is None


def test_a_current_balance_after_a_reported_one_is_still_checked():
    result=analyze('Habla MRS. Soy yo. Me decían un saldo de cuatro mil pesos. '
                   'Gestor: Su saldo total actual es de siete mil pesos.')['negotiation_validation']
    assert result['saldo_informado_detectado']==7000
    assert 'INCORRECTO' in result['validacion_saldo_informado']


def test_a_payment_after_callback_dictation_is_not_discarded():
    result=analyze('Habla MRS. Soy yo. El número de contacto es 55 12 34 56 78. '
                  'Su saldo total es de siete mil pesos. Puede pagar 2000 pesos mañana. '
                  'Sí, mañana pago esos 2000 pesos.')['negotiation_validation']
    assert result['saldo_informado_detectado']==7000
    assert result['monto_detectado']==2000
