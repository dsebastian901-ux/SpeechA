"""Reglas confirmadas de fechas de CONVENIO: 26 noviembre 2026."""
from app.services.grave_date_policy import confirmed_grave_payment_date
from app.services.quality_decision import evaluate_quality


def agreed(*, promise="2026-12-07", window="2026-11-23",
           due="2026-12-10", accepted=True):
    return {
        "quality_contact_type": "TITULAR",
        "status_validation": {
            "excel_status": "CONVENIO", "detected_status": "CONVENIO",
            "matches": True, "valid": True,
        },
        "negotiation_validation": {
            "financial_validation_applicable": True,
            "commitment_confirmed": bool(accepted),
            "amount_confirmed": True,
            "payment_date_confirmed": True,
            "commitment_evidence": {"accepted": bool(accepted)},
            "payment_confirmation_case": False,
            "date_year_rollover_review": False,
            "review_required": False,
            "promise_date": promise,
            "mora_payment_policy": {"window_end": window},
            "due_date": due,
        },
    }


def test_outside_operational_window_is_grave_even_before_due():
    m=agreed()
    result=evaluate_quality(m,100)
    assert result["clasificacion"]=="FALLA_GRAVE"
    assert any(f["code"]=="CRITICAL_AGREED_DATE_OUTSIDE_POLICY"
               for f in result["decision_findings"])
    assert m["status_validation"]["detected_status"]=="CONVENIO"


def test_after_due_is_grave_even_if_inside_operational_window():
    result=evaluate_quality(agreed(promise="2026-12-11",window="2026-12-20"),100)
    assert result["clasificacion"]=="FALLA_GRAVE"


def test_accepted_within_both_limits_does_not_trigger_grave_date():
    result=confirmed_grave_payment_date(
        agreed(promise="2026-11-22")["negotiation_validation"])
    assert result is None


def test_without_accepted_commitment_no_grave_date():
    result=confirmed_grave_payment_date(
        agreed(accepted=False)["negotiation_validation"])
    assert result is None


def test_ambiguous_date_never_becomes_confirmed_grave():
    m=agreed()["negotiation_validation"]
    m["date_year_rollover_review"]=True
    assert confirmed_grave_payment_date(m) is None


def test_valid_installment_exception_cannot_override_due_date():
    m=agreed(promise="2026-12-11")["negotiation_validation"]
    m["installment_window"]={"applies":True,"valid":True}
    assert confirmed_grave_payment_date(m)["code"]=="AGREEMENT_AFTER_DUE_DATE"


def test_valid_installment_exception_can_override_only_operational_window():
    m=agreed()["negotiation_validation"]
    m["installment_window"]={"applies":True,"valid":True}
    assert confirmed_grave_payment_date(m) is None
