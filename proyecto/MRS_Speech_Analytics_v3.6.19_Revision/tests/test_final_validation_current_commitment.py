"""Regresiones: convenio actual no se pierde por la mención de pago anterior."""
from app.services.final_validation_confirmation import confirmed_validation_plan


def test_final_validator_confirms_new_amount_and_date_after_old_payment():
    text = ("Titular: Ya había pagado antes. Gestor: Lo pasaré al área de validación. "
            "Validador: Queda confirmado su pago por la cantidad de mil pesos "
            "al día de mañana 21 del mes. Titular: Sí, correcto.")
    found = confirmed_validation_plan(text)
    assert found['confirmed'] is True
    assert found['amount'] == 1000.0


def test_validator_asks_and_holder_answers_amount_and_date():
    text = ("Gestor: Lo paso al área de validación. "
            "Validador: ¿Me indica el monto y la fecha de su pago? "
            "Titular: Sería el monto es 526, el día 20 de noviembre. "
            "Validador: Perfecto, envíe comprobante.")
    found = confirmed_validation_plan(text)
    assert found['confirmed'] is True
    assert found['amount'] == 526.0


def test_historical_payment_alone_does_not_create_new_commitment():
    text = ("Titular: Ya pagué mil pesos el día 15. "
            "Gestor: Lo paso al área de validación para consultar el comprobante.")
    assert confirmed_validation_plan(text)['confirmed'] is False


def test_amount_without_date_is_not_confirmed():
    text = ("Gestor: Lo paso al área de validación. "
            "Validador: Queda confirmado su pago por la cantidad de mil pesos.")
    assert confirmed_validation_plan(text)['confirmed'] is False


def test_no_validation_phase_no_automatic_agreement():
    text = ("Gestor: El monto es 526, el día 20 de noviembre. "
            "Titular: Tal vez lo revise.")
    assert confirmed_validation_plan(text)['confirmed'] is False


def test_cancelled_commitment_is_not_confirmed():
    text = ("Gestor: Lo paso al área de validación. "
            "Validador: Queda confirmado su pago por 526 pesos el día 20. "
            "Titular: Se cancela el compromiso, no voy a pagar.")
    assert confirmed_validation_plan(text)['confirmed'] is False
