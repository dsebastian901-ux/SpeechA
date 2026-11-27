"""Incumplimiento grave al pactar un convenio fuera del plazo autorizado.

La etiqueta operativa CONVENIO no cambia. La falta grave es del gestor.
Decisión explícita de supervisión: 2026-11-26.
"""
from datetime import date


def _parse(value):
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except (TypeError, ValueError):
        return None


def confirmed_grave_payment_date(negotiation):
    """Devuelve evidencia grave solo para acuerdos con monto y fecha firmes.

    No supone compromiso por una mera oferta, una fecha recordada, un pago
    anterior, un año ambiguo ni una segunda escucha no resuelta.
    """
    n = negotiation or {}
    if not (
        n.get("financial_validation_applicable")
        and n.get("commitment_confirmed")
        and n.get("amount_confirmed")
        and n.get("payment_date_confirmed")
        and (n.get("commitment_evidence") or {}).get("accepted")
        and not n.get("payment_confirmation_case")
        and not n.get("date_year_rollover_review")
        and not n.get("review_required")
        and not n.get("monto_normalizado_asr")
        and not n.get("datos_saldo_inconsistentes")
    ):
        return None
    promise = _parse(n.get("promise_date"))
    policy = n.get("mora_payment_policy") or {}
    limit = _parse(policy.get("window_end"))
    due = _parse(n.get("due_date"))
    if not promise:
        return None

    # Nunca se permite superar el vencimiento, incluso si existiera
    # una excepción válida para un calendario de parcialidades.
    if due and promise > due:
        return {
            "code": "AGREEMENT_AFTER_DUE_DATE",
            "reason": (
                f"FALTA GRAVE DEL GESTOR: aceptó un CONVENIO con fecha "
                f"{promise.isoformat()} posterior al vencimiento "
                f"{due.isoformat()}."
            ),
        }
    installment = n.get("installment_window") or {}
    # Conservar una excepción explícitamente autorizada y validada.
    if installment.get("applies") and installment.get("valid"):
        return None
    if limit and promise > limit:
        return {
            "code": "AGREEMENT_AFTER_AUTHORIZED_WINDOW",
            "reason": (
                f"FALTA GRAVE DEL GESTOR: aceptó un CONVENIO con fecha "
                f"{promise.isoformat()} posterior al límite operativo "
                f"{limit.isoformat()}."
            ),
        }
    return None
