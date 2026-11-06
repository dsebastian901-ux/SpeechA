"""Hechos financieros confirmados por una persona, sin editar el texto de ASR."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from app.services.amount_review_service import evidence_digest


SCOPE = "BALANCE_AND_FINAL_INSTALLMENTS_ONLY"


def money(value):
    try:
        if isinstance(value, bool):
            raise ValueError
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0 or number != number.quantize(Decimal("0.01")):
            raise ValueError
        return float(number)
    except (ValueError, InvalidOperation, TypeError):
        raise ValueError("Indique un importe positivo con un máximo de dos decimales.") from None


def make_financial_review(data, negotiation, *, balance_amount=None, confirm_installments=False, audio_verified=False):
    if audio_verified is not True:
        raise ValueError("Se requiere confirmación explícita del usuario sobre el audio.")
    balance = installments = None
    if balance_amount is not None:
        original = negotiation.get("saldo_informado_detectado")
        evidence = negotiation.get("evidencia_saldo_informado")
        if original is None or not evidence:
            raise ValueError("La llamada no contiene evidencia de un saldo informado.")
        balance = {"original_amount": money(original), "confirmed_amount": money(balance_amount), "evidence": evidence}
    if confirm_installments:
        plan = negotiation.get("installment_validation") or {}
        amounts = plan.get("amounts") or []
        conflicts = plan.get("conflicts") or []
        if (plan.get("method") != "PARCIALIDADES_IDENTIFICADAS" or len(amounts) < 2 or not conflicts
                or not plan.get("evidence") or any(
                    not isinstance(c, dict) or c.get("installment") not in range(1, len(amounts)+1)
                    or not c.get("amounts") for c in conflicts)):
            raise ValueError("No hay un plan final explícito con discrepancias de parcialidades que confirmar.")
        installments = {key: deepcopy(plan.get(key)) for key in ("amounts", "total", "method", "evidence", "conflicts")}
        for amount in amounts:
            money(amount)
    if balance is None and installments is None:
        raise ValueError("Seleccione un saldo o un acuerdo final para confirmar.")
    return {"schema": 1, "scope": SCOPE, "source_sha256": evidence_digest(data),
            "reviewed_at": datetime.now(timezone.utc).isoformat(), "audio_verified": True,
            "balance": balance, "installments": installments}


def apply_financial_review(data, review, balance_amount, balance_evidence, plan):
    """Validar toda la revisión antes de usarla; el resto de las reglas se calcula después."""
    status = {"review_required": False, "human_verified": False, "balance_applied": False,
              "installments_applied": False, "human_review_record": None}
    if review is None:
        return balance_amount, balance_evidence, plan, status
    status["review_required"] = True
    status["reason"] = "La confirmación financiera no corresponde a la evidencia actual; revisar o revocar."
    try:
        if not isinstance(review, dict) or not isinstance(data, dict):
            raise ValueError
        negotiation = {"saldo_informado_detectado": balance_amount, "evidencia_saldo_informado": balance_evidence,
                       "installment_validation": plan}
        expected = make_financial_review(data, negotiation,
            balance_amount=(review.get("balance") or {}).get("confirmed_amount"),
            confirm_installments=review.get("installments") is not None, audio_verified=review.get("audio_verified"))
        if any(review.get(key) != expected[key] for key in ("schema", "scope", "source_sha256", "balance", "installments")):
            raise ValueError
    except (ValueError, TypeError, AttributeError, KeyError):
        return balance_amount, balance_evidence, plan, status
    if review["balance"] is not None:
        balance_amount = review["balance"]["confirmed_amount"]
        balance_evidence = f"Confirmado por usuario: {balance_amount:g}. ASR original: {balance_evidence}"
        status["balance_applied"] = True
    if review["installments"] is not None:
        plan = deepcopy(plan)
        plan["resolved_conflicts"] = plan["conflicts"]
        plan["conflicts"] = []
        plan["review_required"] = False
        plan["human_confirmed_final_plan"] = True
        status["installments_applied"] = True
    status.update(review_required=False, human_verified=True, human_review_record=deepcopy(review))
    status.pop("reason", None)
    return balance_amount, balance_evidence, plan, status
