"""Vincular datos bancarios a una instrucción local, no a números de toda la llamada."""
import re
from app.services.conversation_evidence import normalize, sentence_evidence


def wrong_bank_instructions(text, segments, bank_variants, authorized_codes, transfer_account):
    wrong = []
    instruction = re.compile(
        r"\b(?:deposite|deposita|depositar|transfiera|transferir|pague|pagar|abone|abonar)\b"
        r"[^.!?]{0,55}\b(?:cuenta|clabe)\b(?P<details>[^.!?]{0,110})")
    for unit in sentence_evidence(text, segments):
        if unit["speaker_role"] in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            continue
        s = normalize(unit["text"])
        if re.search(r"\b(?:me dijeron|me indicaron|ya deposite|ya pague|no deposite|no transfiera)\b", s):
            continue
        for offer in instruction.finditer(s):
            details = offer["details"]
            if re.search(r"\b(?:tarjeta|referencia|telefono|whatsapp)\b", details):
                continue
            numbers = [re.sub(r"\D", "", m.group()) for m in
                       re.finditer(r"(?<!\d)\d(?:[\d ,\-]{5,30})\d(?!\d)", details)]
            numbers = [n for n in numbers if 7 <= len(n) <= 18]
            if not numbers:
                continue
            local = s[max(0, offer.start()-40):offer.end()]
            for bank, variants in bank_variants.items():
                if not any(re.search(r"(?<!\w)"+re.escape(normalize(v))+r"(?!\w)", local) for v in variants):
                    continue
                allowed = {authorized_codes[bank]}
                if bank == "SANTANDER":
                    allowed.add(transfer_account)
                invalid = [n for n in numbers if n not in allowed]
                if invalid:
                    wrong.append({"bank": bank, "expected_convenio": authorized_codes[bank],
                                  "numbers_detected": invalid, "evidence": unit["text"],
                                  "speaker_role": unit["speaker_role"], "start": unit["start"], "end": unit["end"]})
    return wrong
