"""Vincular datos bancarios a una instrucción local, no a números de toda la llamada."""
import re
from app.services.conversation_evidence import normalize, sentence_evidence


def only_negated_transfers(text):
    source = normalize(text)
    mentions = list(re.finditer(r"\b(?:transferencia|transferir|transfiera)\b", source))
    return bool(mentions) and all(re.search(
        r"\bno (?:puede|pueda|debe|se puede|se pueda|se permite)\b[^.!?;,]{0,60}$",
        source[max(0, m.start()-85):m.start()]) for m in mentions)


def future_transfer_discussion(text, segments=()):
    """Explorar una transferencia nueva impide tratar todo como pago histórico."""
    pattern = re.compile(
        r"\b(?:puedo|puede|pueden|podria|podra|pudiera|podemos)\s+"
        r"(?:(?:hacer|realizar|pagar)\b[^.!?]{0,65}\b(?:transferencia|clabe)|transferir\b)")
    for unit in sentence_evidence(text, segments):
        clauses=[unit['text']] if '?' in unit['text'] or '¿' in unit['text'] else re.split(r"[;,]",unit['text'])
        for clause in clauses:
            s = normalize(clause)
            for match in pattern.finditer(s):
                if not re.search(r"\bno\s*$", s[max(0,match.start()-8):match.start()]):
                    return True
    return False


def transfer_instructions(text, segments=()):
    """Instrucciones futuras del gestor; un comprobante de pago no es una CLABE."""
    evidence = []
    pattern = re.compile(
        r"\b(?:puede (?:pagar|realizar|hacer|transferir)|podra (?:pagar|realizar|hacer|transferir)|"
        r"debe (?:pagar|realizar|hacer|transferir)|realice|haga|transfiera|transferir a|"
        r"pague|deposite)\b[^.!?]{0,70}\b(?:transferencia|clabe|cuenta interbancaria)\b|"
        r"\b(?:puede|podra|debe) transferir\b|\btransfiera\b")
    for unit in sentence_evidence(text, segments):
        if unit["speaker_role"] in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            continue
        for clause in re.split(r"[;,]", unit["text"]):
            s = normalize(clause)
            raw = re.sub(r"\s+", " ", clause).strip()
            # Revisar cada verbo permite ver la instrucción nueva incluso si
            # una frase histórica anterior llega hasta la misma «transferencia».
            for anchor in re.finditer(r"\b(?:puede|podra|debe|realice|haga|transfiera|transferir|pague|deposite)\b", s):
                match = pattern.match(s, anchor.start())
                if match is None:
                    continue
                before = s[max(0, match.start()-45):match.start()]
                if (re.search(r"\b(?:no|nunca|ya|yo|lo|ayer|hoy)\s*$", before)
                        or re.match(r"(?:pagué|deposité|realicé)\b", raw[match.start():], re.I)
                        or re.search(r"\bno (?:le recomiendo|es necesario)\b[^.!?]{0,30}$", before)
                        or re.search(r"\b(?:me dijeron|me indicaron)\b", s)):
                    continue
                evidence.append(dict(unit, phrase=match.group()))
    return evidence


def transfer_is_option_listing(text, segments, authorized_places):
    """Enumerar bancos no es dictar una CLABE ni una transferencia elegida.

    Solo exime el aviso genérico si hay dos alternativas autorizadas en la
    conversación y no se desarrolla una transferencia concreta. No valida
    datos bancarios ni agrega bancos al número de lugares autorizados.
    """
    source=normalize(text)
    if len(set(authorized_places))<2 or future_transfer_discussion(text,segments) or transfer_instructions(text,segments):
        return False
    if re.search(r"\b(?:clabe|cuenta bancaria|numero de cuenta|cuenta de destino|"
                 r"cuenta personal|banca movil|pago de tarjetas|practicaja|convenio (?:es|numero|\d))\b",source):
        return False
    mentions=list(re.finditer(r"\btransferencia\b",source))
    return bool(mentions) and all(re.match(
        r"\s+(?:de |desde |con |en )?(?:bbva|bancomer|van commer|citibanamex|santander)\b",
        source[m.end():]) for m in mentions)


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
