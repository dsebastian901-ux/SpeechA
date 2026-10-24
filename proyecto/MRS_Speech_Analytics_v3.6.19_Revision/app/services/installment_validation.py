"""Relaciona importes con parcialidades explícitas; conserva contradicciones."""
import re


def installment_plan(source, mentions):
    counts = []
    for match in re.finditer(r"\b(dos|tres|2|3) pagos (?:por|de)\s+", source):
        amount = next((m for m in mentions if match.end() <= m[0] <= match.end()+8), None)
        if amount:
            count = {"dos": 2, "tres": 3, "2": 2, "3": 3}[match[1]]
            counts.append((match.start(), [float(amount[2])]*count, source[match.start():amount[1]]))
    bindings = {}
    evidence = []
    pattern = r"\b(primer(?: pago)?|segundo(?: pago)?|tercer(?: pago)?|pago mas)\b"
    for match in re.finditer(pattern, source):
        ordinal = 1 if match[1].startswith("primer") else 3 if match[1].startswith("tercer") else 2
        amount = None
        for m in mentions:
            if not match.end() <= m[0] <= match.end()+100:
                continue
            bridge = source[match.end():m[0]]
            if re.search(pattern, bridge) or re.search(r"[.!?]", bridge):
                break
            if re.search(r"\b(?:por|cantidad de|de)\s*$", bridge):
                amount = m
            break
        if amount is None and re.search(r"\bcomo\s*$", source[max(0,match.start()-8):match.start()]):
            previous = [m for m in mentions if 0 <= match.start()-m[1] <= 85]
            if previous:
                amount = previous[-1]
        if amount:
            bindings.setdefault(ordinal, []).append(float(amount[2]))
            evidence.append({"installment": ordinal, "amount": float(amount[2]),
                             "text": source[min(match.start(),amount[0]):max(match.end(),amount[1])]})
    conflicts = [{"installment": ordinal, "amounts": sorted(set(values))}
                 for ordinal, values in bindings.items() if len(set(values)) > 1]
    if len(bindings) >= 2 and sorted(bindings) == list(range(1, max(bindings)+1)):
        amounts = [bindings[k][-1] for k in sorted(bindings)]
        method = "PARCIALIDADES_IDENTIFICADAS"
    elif counts:
        _, amounts, phrase = counts[-1]
        evidence.append({"text": phrase})
        method = "PAGOS_IGUALES_EXPLICITOS"
    else:
        amounts, method = [], "SIN_PLAN_EXPLICITO"
    return {"amounts": amounts, "total": sum(amounts) if amounts else None,
            "method": method, "evidence": evidence, "conflicts": conflicts,
            "review_required": bool(conflicts)}
