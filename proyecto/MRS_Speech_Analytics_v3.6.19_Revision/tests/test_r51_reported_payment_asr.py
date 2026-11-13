"""Regresion: pago anterior reportado no es promesa/convenio nuevo."""
from app.services.conversation_evidence import completed_payment


def test_ayer_repositamos_is_reported_previous_deposit():
    text = ("Me dijeron que la cuenta tiene atraso. "
            "Sí, de hecho ayer repositamos, la aplicación decía 1200 y repositamos 1300. "
            "Voy a poner estos datos en el sistema.")
    evidence = completed_payment(text, ())
    assert evidence["confirmed"], "Un depósito reportado ayer debe reconocerse aun con error ASR"


def test_future_repositamos_not_a_confirmed_payment():
    text = "Si mañana repositamos el dinero, ¿podríamos actualizar la cuenta?"
    assert not completed_payment(text, ())["confirmed"]
