"""Efecto del mínimo y plazo: manual operativo y aclaración del usuario."""
from calendar import monthrange
from datetime import date, timedelta

REGULARIZATION_MORAS = frozenset({"1PV", "1FLP", "2PV", "3PV"})
LIQUIDATION_MORAS = frozenset({"3HN", "4PV", "5PV", "6PV", "C1", "C2", "C3", "C4", "B", "A"})


def payment_policy(mora, call_date, due_date=None):
    if mora in LIQUIDATION_MORAS:
        mode, effect, references = "MES_DE_LLAMADA", "LIQUIDACION", ["MOR045-MOR054", "ESTR004", "RM004", "RM011"]
        end = date(call_date.year, call_date.month, monthrange(call_date.year, call_date.month)[1]) if call_date else None
    elif mora in REGULARIZATION_MORAS:
        mode, effect, references = "CORTE_Y_VENCIMIENTO", "MENSUALIDAD_VENCIDA" if mora == "1FLP" else "REGULARIZACION_O_MENSUALIDAD", ["MOR001-MOR044", "RN004", "RM001", "RM002", "RM011"]
        end = call_date+timedelta(days=3) if call_date else None
    else:
        mode, effect, references, end = "MORA_NO_CONFIGURADA", "NO_DETERMINADO", [], None
    # El plazo mensual no prolonga un vencimiento anterior.
    if end and due_date:
        end = min(end, due_date)
    return {"mora": mora, "mode": mode, "minimum_effect": effect,
            "window_start": call_date.isoformat() if call_date else None,
            "window_end": end.isoformat() if end else None,
            "uses_cut": mora in REGULARIZATION_MORAS,
            "references": references,
            "monthly_exception_source": "Aclaración del usuario: liquidaciones dentro del mes de la llamada, incluso con vencimiento posterior" if mora in LIQUIDATION_MORAS else None}


def two_installment_window(schedule, call_date, due_date, *, second_anchor):
    """Excepción de dos exhibiciones; la base de los siete días es explícita."""
    if (len(schedule) != 2 or [entry.get("installment") for entry in schedule] != [1, 2]
            or not call_date or second_anchor not in {"FIRST_PAYMENT", "CALL_DATE"}):
        return {"applies": False, "valid": False, "reasons": []}
    try:
        first, second = [date.fromisoformat(entry["date"]) for entry in schedule]
    except (KeyError, TypeError, ValueError):
        return {"applies": False, "valid": False, "reasons": []}
    first_end = call_date+timedelta(days=3)
    second_end = (first if second_anchor == "FIRST_PAYMENT" else call_date)+timedelta(days=7)
    if due_date:
        first_end, second_end = min(first_end,due_date), min(second_end,due_date)
    reasons = []
    first_valid = call_date <= first <= first_end
    if not first_valid:
        reasons.append("La primera exhibición no queda dentro de los tres días de la llamada.")
    if not first <= second <= second_end:
        reasons.append("La segunda exhibición excede el plazo de siete días o el vencimiento, o es anterior a la primera.")
    return {"applies": True, "valid": not reasons, "first_payment": first.isoformat(),
            "first_payment_valid": first_valid,
            "second_payment": second.isoformat(), "first_window_end": first_end.isoformat(),
            "second_window_end": second_end.isoformat(), "second_anchor": second_anchor, "reasons": reasons}
