"""Un teléfono de retorno no es una referencia de tarjeta incompleta."""
import pytest
from app.services.payment_reference_validation import find_reference


@pytest.mark.parametrize('number',['55 51 23 45 67','cincuenta y cinco cincuenta y uno veintitres cuarenta y cinco sesenta y siete'])
def test_ten_digits_after_callback_purpose_are_not_a_partial_card(number):
    r=find_reference('Que nos pueda regalar una llamada para información de su tarjeta. '
                     'Le dejo el número para tomar nota: '+number+'.','1234567890123456')
    assert not r['requires_review'] and not r['ambiguous']
    assert r['excluded_callback_numbers'][0]['digits']=='5551234567'


@pytest.mark.parametrize('prefix',['Referencia de pago: ','Le indico los 16 dígitos de su tarjeta: '])
def test_incomplete_explicit_reference_is_not_excused_by_earlier_callback_purpose(prefix):
    r=find_reference('Que nos regrese una llamada. '+prefix+'55 51 23 45 67.','1234567890123456')
    assert r['requires_review'] and r['ambiguous']


def test_full_card_remains_a_card_after_a_callback_request():
    r=find_reference('Que nos regrese una llamada. Su tarjeta: 1234567890123456.','1234567890123456')
    assert r['detected'][0]['digits']=='1234567890123456'
    assert not r['excluded_callback_numbers']


def test_unknown_ten_digit_sequence_is_not_silently_declared_a_phone():
    r=find_reference('Tarjeta: 55 51 23 45 67.','1234567890123456')
    assert r['requires_review'] and not r['excluded_callback_numbers']
