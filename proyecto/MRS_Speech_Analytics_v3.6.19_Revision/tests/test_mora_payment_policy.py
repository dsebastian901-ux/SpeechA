"""Reglas contrastadas con manual 04/05/06/13/14 y excepción mensual del usuario."""
from datetime import date
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.mora_payment_policy import payment_policy, two_installment_window, LIQUIDATION_MORAS


def analyze(mora="C4", promise="31 de octubre", amount=2200, minimum="2000", total="50000", **context):
    text = (f"Habla MRS. Soy yo. Le ofrecemos una opción para liquidar su cuenta por {amount} pesos. "
            f"Me comprometo a pagar {amount} pesos el {promise}. "
            "Puede pagar en Chedraui y Farmacias del Ahorro. Envíe el comprobante por WhatsApp.")
    transcript = TranscriptionModel("synthetic.wav", "synthetic.wav", text, duration_seconds=90)
    return A.analyze_transcription(transcript, {"asignacion": mora, "fecha": "2026-10-10",
        "vencimiento": "2026-11-30", "corte": "8", "pago_minimo": minimum,
        "saldo_total": total, "estatus_grabacion": "CONVENIO", **context})


@pytest.mark.parametrize("mora", sorted(LIQUIDATION_MORAS))
def test_full_settlement_uses_minimum_and_month_end_in_all_liquidation_moras(mora):
    a = analyze(mora)
    n = a.metadata["negotiation_validation"]
    assert n["validacion_monto"] == "VALIDA - MINIMO DE LIQUIDACION SEGUN MORA"
    assert n["mora_payment_policy"]["window_end"] == "2026-10-31"
    assert n["mora_payment_policy"]["uses_cut"] is False
    assert n["calculated_payment_date"] is None
    assert n["date_effect"] == "LIQUIDACION DENTRO DEL MES"
    assert a.metadata["shared_classification"]["clasificacion"] == "APROBADO"


@pytest.mark.parametrize("mora", sorted(LIQUIDATION_MORAS))
def test_later_maturity_does_not_allow_settlement_in_next_month(mora):
    a = analyze(mora, promise="1 de noviembre")
    n = a.metadata["negotiation_validation"]
    assert not n["valid"]
    assert any("fuera del mes" in reason for reason in n["reasons"])
    assert a.metadata["shared_classification"]["clasificacion"] == "REVISAR"
    assert "PEN005" not in {p["id"] for p in a.metadata["penalties"]}


@pytest.mark.parametrize("call,expected", [("2026-02-02", "2026-02-28"), ("2028-02-02", "2028-02-29"),
                                            ("2026-12-10", "2026-12-31")])
def test_month_window_uses_historical_call_month_and_calendar_boundaries(call, expected):
    policy = payment_policy("C4", date.fromisoformat(call), date(2030, 1, 1))
    assert policy["window_end"] == expected


def test_earlier_maturity_remains_a_binding_limit():
    assert payment_policy("C4", date(2026,10,10),date(2026,10,20))["window_end"] == "2026-10-20"
    a = analyze(promise="21 de octubre", vencimiento="2026-10-20")
    assert "PEN005" in {p["id"] for p in a.metadata["penalties"]}
    assert a.metadata["shared_classification"]["clasificacion"] == "FALLA_GRAVE"


def test_month_of_next_year_is_not_the_same_month():
    a = analyze(promise="1 de enero de 2027", fecha="2026-12-20", vencimiento="2027-01-31")
    assert a.metadata["shared_classification"]["clasificacion"] == "REVISAR"


@pytest.mark.parametrize("minimum,total,amount", [("2000", "50000", 2000), ("2000", "50000", 50000)])
def test_amount_range_endpoints_are_valid_for_settlement(minimum,total,amount):
    assert analyze(amount=amount,minimum=minimum,total=total).metadata["negotiation_validation"]["amount_invalid"] is False


@pytest.mark.parametrize("minimum,total,amount", [("2000", "50000", 1999), ("2000", "50000", 50001)])
def test_confirmed_under_minimum_or_above_balance_is_not_approved(minimum,total,amount):
    a = analyze(amount=amount,minimum=minimum,total=total)
    assert a.metadata["negotiation_validation"]["amount_invalid"]
    assert a.metadata["shared_classification"]["clasificacion"] != "APROBADO"


@pytest.mark.parametrize("minimum,total", [("", "50000"), ("2000", "")])
def test_incomplete_financial_reference_is_reviewed(minimum,total):
    a = analyze(minimum=minimum,total=total)
    assert a.metadata["negotiation_validation"]["validacion_monto"] == "REVISAR - REFERENCIA FINANCIERA INCOMPLETA"


@pytest.mark.parametrize("mora", ["1PV", "1FLP", "2PV", "3PV"])
def test_total_settlement_stays_forbidden_for_regularization_moras(mora):
    a = analyze(mora, promise="12 de octubre")
    assert "PEN004" in {p["id"] for p in a.metadata["penalties"]}


@pytest.mark.parametrize("cut,day", [(3,26),(5,28),(8,1),(10,3),(11,4),(15,8),(19,12),(20,13),(23,16),(25,18),(28,21)])
def test_payment_day_stays_in_the_month_of_the_managed_call(cut,day):
    _, dt = A._calculate_payment_date_from_cut({"corte":cut,"fecha":"2026-10-14"})
    assert dt == date(2026,10,day)


@pytest.mark.parametrize("promise,regularizes", [("15 de octubre",True),("17 de octubre",False)])
def test_regularization_vs_overdue_monthly_payment_uses_cut_and_promise(promise,regularizes):
    text = f"Habla MRS. Soy yo. Me comprometo a pagar 2200 pesos el {promise}."
    r = A.calculate_basic_compliance(text,{"asignacion":"1PV","corte":"23","fecha":"2026-10-14",
        "vencimiento":"2026-11-23","pago_minimo":"2000","saldo_total":"50000","estatus_grabacion":"CONVENIO"})
    assert r["negotiation_validation"]["date_effect"] == ("SE PONE AL CORRIENTE" if regularizes else "CUBRE MENSUALIDAD VENCIDA")


def test_low_mora_promise_over_three_days_is_reviewed_without_inventing_maturity_penalty():
    text = "Habla MRS. Soy yo. Me comprometo a pagar 2200 pesos el 18 de octubre."
    r = A.calculate_basic_compliance(text,{"asignacion":"1PV","corte":"23","fecha":"2026-10-14",
        "vencimiento":"2026-11-23","pago_minimo":"2000","saldo_total":"50000","estatus_grabacion":"CONVENIO"})
    assert any("RN004" in reason for reason in r["negotiation_validation"]["reasons"])
    assert "PEN005" not in {p["id"] for p in r["penalties"]}


def test_final_installment_date_is_not_replaced_by_a_today_receipt_reminder():
    text = ("Habla MRS. Soy yo. Me comprometo a pagar. Activamos convenio por 1000 pesos hoy como primer pago "
            "y el segundo por 1200 pesos el 1 de noviembre. El comprobante del primer pago lo manda hoy.")
    r = A.calculate_basic_compliance(text,{"asignacion":"C4","fecha":"2026-10-14","vencimiento":"2026-11-30",
        "pago_minimo":"2000","saldo_total":"50000","estatus_grabacion":"CONVENIO"})
    n = r["negotiation_validation"]
    assert n["promise_date"] == "2026-11-01"
    assert n["monto_detectado"] == 2200
    assert any("fuera del mes" in reason for reason in n["reasons"])


def test_regularization_claim_in_a_liquidation_mora_requires_review():
    text = "Habla MRS. Soy yo. Gestor: Con ese pago de 2200 pesos queda al corriente."
    r = A.calculate_basic_compliance(text,{"asignacion":"C4","pago_minimo":"2000","saldo_total":"50000"})
    assert any("efecto de regularización" in reason for reason in r["negotiation_validation"]["reasons"])


def test_unknown_mora_does_not_invent_a_settlement_authorization():
    a = analyze("DESCONOCIDA")
    assert a.metadata["negotiation_validation"]["validacion_monto"] == "REVISAR - MORA SIN POLITICA DE LIQUIDACION"


@pytest.mark.parametrize("phone", ["25-06-77", "55-06-77", "25/06/77"])
def test_callback_phone_fragments_are_not_future_promises(phone):
    text = f"Le dicto WhatsApp para enviar su comprobante. Correcto. {phone}. Ahí envía su comprobante de pago."
    assert A._extract_payment_promise_date(text,"2026-10-01") is None


@pytest.mark.parametrize("day", ["23/10/2026", "23-10-2026"])
def test_explicit_numeric_date_after_payment_amount_is_still_detected(day):
    assert A._extract_payment_promise_date(f"Me comprometo a pagar 600 pesos el {day}.","2026-10-20") == date(2026,10,23)


def test_past_abono_report_has_no_future_promise_or_date_penalty():
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. Ya le di un abono el viernes y otro ayer. "
        "El viernes fueron 300 pesos y ayer 315 pesos. Ya mandé el ticket.",
        {"asignacion":"1FLP","fecha":"2026-10-14","vencimiento":"2026-10-10","estatus_grabacion":"CONVENIO"})
    assert r["negotiation_validation"]["payment_confirmation_case"]
    assert r["negotiation_validation"]["promise_date"] is None
    assert "PEN005" not in {p["id"] for p in r["penalties"]}


@pytest.mark.parametrize("raw", ["25-06-77", "manana"])
def test_contact_date_penalty_removal_does_not_allow_a_new_approval(raw):
    from tools.regression_checkpoints import verified_removal
    previous = {"negotiation_validation": {"promise_date_text":raw,
                                           "promise_date":"2077-06-25", "call_date":"2026-10-01",
                                           "promise_date_evidence":"25-06-77. Envíe su comprobante."}}
    current = {"negotiation_validation": {"promise_date_text":"mañana", "promise_date":"2026-10-02", "commitment_confirmed":False},
               "final_result":"REVISAR"}
    assert verified_removal("contact_number_not_payment_date", previous, current)
    current["final_result"] = "APROBADA"
    assert not verified_removal("contact_number_not_payment_date", previous, current)


def test_unaccepted_offer_beyond_maturity_is_review_not_confirmed_critical():
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. Le ofrecemos pagar 2200 pesos el 30 de octubre. "
        "No puedo confirmar esa fecha.", {"asignacion":"1PV","fecha":"2026-10-14","corte":"23",
        "vencimiento":"2026-10-23","estatus_grabacion":"CONVENIO","pago_minimo":"2000","saldo_total":"50000"})
    assert "PEN005" not in {p["id"] for p in r["penalties"]}
    assert r["final_result"] == "REVISAR"


@pytest.mark.parametrize("anchor,first,second,due,valid", [
    ("FIRST_PAYMENT","2026-10-13","2026-10-20","2026-10-25",True),
    ("CALL_DATE","2026-10-13","2026-10-20","2026-10-25",True),
    ("FIRST_PAYMENT","2026-10-16","2026-10-23","2026-10-25",True),
    ("CALL_DATE","2026-10-16","2026-10-23","2026-10-25",False),
    ("FIRST_PAYMENT","2026-10-17","2026-10-20","2026-10-25",False),
    ("FIRST_PAYMENT","2026-10-16","2026-10-24","2026-10-25",False),
    ("FIRST_PAYMENT","2026-10-16","2026-10-23","2026-10-22",False),
])
def test_two_installment_boundaries_are_explicit(anchor,first,second,due,valid):
    schedule=[{"installment":1,"date":first},{"installment":2,"date":second}]
    result=two_installment_window(schedule,date(2026,10,13),date.fromisoformat(due),second_anchor=anchor)
    assert result["valid"] is valid


@pytest.mark.parametrize("first,second,due,expected", [
    ("16 de octubre","23 de octubre","2026-10-30","APROBADO"),
    ("16 de octubre","24 de octubre","2026-10-30","REVISAR"),
    ("17 de octubre","23 de octubre","2026-10-30","REVISAR"),
    ("16 de octubre","23 de octubre","2026-10-22","FALLA_GRAVE"),
])
def test_two_installment_exception_is_applied_to_the_complete_decision(first,second,due,expected):
    text=(f"Habla MRS. Soy yo. Activamos convenio por 1000 pesos el {first} como primer pago "
          f"y el segundo por 1200 pesos el {second} para cubrir la mensualidad vencida. "
          "Me comprometo a pagar el convenio completo. Puede pagar en Chedraui y Farmacias del Ahorro. "
          "Envíe su comprobante por WhatsApp.")
    t=TranscriptionModel("synthetic.wav","synthetic.wav",text,duration_seconds=90)
    a=A.analyze_transcription(t,{"asignacion":"1PV","fecha":"2026-10-13","vencimiento":due,
        "corte":"23","pago_minimo":"2000","saldo_total":"50000","estatus_grabacion":"CONVENIO"})
    n=a.metadata["negotiation_validation"]
    assert n["installment_window"]["second_anchor"] == "FIRST_PAYMENT"
    assert n["installment_window"]["second_window_end"] <= due
    assert a.metadata["shared_classification"]["clasificacion"] == expected
