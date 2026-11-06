"""Lectura adicional acotada de ofertas sin importe. No acredita autorización."""
import hashlib
import math
import re

from app.services.conversation_evidence import normalize, role_of


REQUEST = re.compile(r"\b(?:le (?:estan|estamos) pidiendo|le ofrecemos|le ofrezco)\b")
NUMBER_VALUES = dict(zip(
    "cero un uno una dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciseis diecisiete dieciocho diecinueve veinte veintiuno veintidos veintitres veinticuatro veinticinco veintiseis veintisiete veintiocho veintinueve".split(),
    [0, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]))
NUMBER_VALUES.update(dict(zip(
    "treinta cuarenta cincuenta sesenta setenta ochenta noventa cien ciento doscientos trescientos cuatrocientos quinientos seiscientos setecientos ochocientos novecientos".split(),
    [30, 40, 50, 60, 70, 80, 90, 100, 100, 200, 300, 400, 500, 600, 700, 800, 900])))
WORDS = "(?:" + "|".join(NUMBER_VALUES) + "|mil|y)"
MONEY = re.compile(rf"(?<!\w)(\d+(?:[.,]\d+)*|{WORDS}(?:\s+{WORDS}){{0,8}})\s+pesos?\b")


def source_text(text):
    # Equivalencia de formato monetario, sin cambiar cantidades.
    source = re.sub(r"\b(\d{1,3})\.(\d{3})0\b", r"\1,\2", normalize(text))
    return re.sub(r"\b(\d{1,3})\.(\d{3})(?=\s*pesos?\b)", r"\1,\2", source)


def fingerprint(text):
    return hashlib.sha256(source_text(text).encode("utf-8")).hexdigest()


def monetary_readings(text):
    source = source_text(text)
    result = set()
    for match in MONEY.finditer(source):
        token = match[1]
        if token[0].isdigit():
            if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", token):
                value = float(re.sub(r"[.,]", "", token))
            else:
                try:
                    value = float(token.replace(",", "."))
                except ValueError:
                    continue
        else:
            total = current = 0
            for word in token.split():
                if word == "mil":
                    total += (current or 1)*1000
                    current = 0
                elif word != "y":
                    current += NUMBER_VALUES[word]
            value = float(total+current)
        prefix = source[max(0, match.start()-70):match.start()]
        if re.search(r"\bno\b[^.!?;]{0,55}$", prefix):
            continue
        if re.search(r"\b(?:saldo|adeudo|tarjeta|telefono|clabe)\b[^.!?]*$", prefix) and not REQUEST.search(prefix):
            continue
        if 0 < value < 10_000_000:
            result.add(value)
    return result


def missing_proposals(text, segments):
    """Solo solicitudes sin importe y con tiempos existentes; máximo 3 ventanas."""
    source = source_text(text)
    spans, cursor = [], 0
    for segment in segments or []:
        if not isinstance(segment, dict):
            continue
        fragment = source_text(segment.get("texto", segment.get("text", "")))
        if not fragment:
            continue
        position = source.find(fragment, cursor)
        if position < 0:
            continue
        cursor = position+len(fragment)
        spans.append((position, cursor, segment))
    candidates = []
    for match in REQUEST.finditer(source):
        sentence_start = max(source.rfind(c, 0, match.start()) for c in ".!?")+1
        prefix = source[sentence_start:match.start()]
        if re.search(r"\b(?:no|me dijeron|me habian dicho|segun yo)\b", prefix):
            continue
        tail = re.split(r"[!?]|\.(?!\d)", source[match.end():match.end()+180])[0]
        local = source[match.start():match.end()] + tail
        financial_context = source[max(sentence_start, match.start()-120):match.end()] + tail
        if not re.search(r"\b(?:descuento|pago|pagar|abono|deuda|saldo|convenio|pesos|cantidad|finiquitar|liquidar)\b", financial_context):
            continue
        number_words = "|".join(set(NUMBER_VALUES)-{"un", "una", "uno", "cero"})
        if monetary_readings(local) or re.search(rf"\d|\b(?:mil|{number_words})\b", tail):
            continue  # Importe ambiguo ya presente: no reemplazarlo por otro.
        covered = [s for a, b, s in spans if a < match.end()+len(tail) and b > match.start()]
        if not covered or any(role_of(s.get("speaker_role") or s.get("role") or s.get("speaker")) in
                              {"TITULAR", "TERCERO", "INTERLOCUTOR"} for s in covered):
            continue
        try:
            start = float(covered[0].get("inicio", covered[0].get("start")))
            end = float(covered[-1].get("fin", covered[-1].get("end")))
        except (TypeError, ValueError):
            continue
        if not 0 <= start < end or end-start > 24:
            continue
        if candidates and start < candidates[-1]["fin"]:
            continue
        candidates.append({"anchor_start": match.start(), "anchor_end": match.end(),
                           "inicio": start, "fin": end, "texto_original": local})
        if len(candidates) == 3:
            break
    return candidates


def recover_amounts(text, segments, read_window):
    """read_window(start,end,beam) lee audio real con el mismo modelo, sin prompt."""
    entries = []
    for candidate in missing_proposals(text, segments):
        attempts = []
        # Dos encuadres y búsqueda distinta; la coincidencia no es escucha humana.
        for before, after, beam in [(5, 2, 5), (2, 4, 10)]:
            start, end = max(0, candidate["inicio"]-before), candidate["fin"]+after
            try:
                reading = read_window(start, end, beam)
                amounts = sorted(monetary_readings(reading))
                attempts.append({"inicio": start, "fin": end, "beam_size": beam,
                                 "texto": reading, "amounts": amounts})
            except Exception as error:
                attempts.append({"inicio": start, "fin": end, "beam_size": beam,
                                 "error": type(error).__name__, "amounts": []})
        amounts = [a["amounts"] for a in attempts]
        agreed = len(amounts) == 2 and len(amounts[0]) == 1 and amounts[0] == amounts[1]
        entries.append(dict(candidate, attempts=attempts,
                            amount=amounts[0][0] if agreed else None,
                            status="COINCIDENCIA_ASR" if agreed else "REQUIERE_REVISION"))
    return {"schema": 1, "source_text_sha256": fingerprint(text), "entries": entries,
            "human_verified": False}


def validated_entries(text, segments, audit):
    """Un número guardado solo no basta; comprobar fuente, ventana y dos lecturas."""
    if not isinstance(audit, dict) or audit.get("schema") != 1 or audit.get("source_text_sha256") != fingerprint(text):
        return []
    candidates = {c["anchor_start"]: c for c in missing_proposals(text, segments)}
    result = []
    entries = audit.get("entries") or []
    if not isinstance(entries, list):
        return []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if not isinstance(entry.get("anchor_start"), int):
            continue
        amount = entry.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or not 0 < amount < 10_000_000:
            continue
        candidate = candidates.get(entry.get("anchor_start"))
        attempts = entry.get("attempts") or []
        if not candidate or not isinstance(attempts, list) or len(attempts) != 2 or entry.get("status") != "COINCIDENCIA_ASR":
            continue
        if any(not isinstance(a, dict) for a in attempts):
            continue
        if any(entry.get(k) != candidate[k] for k in ("anchor_end", "inicio", "fin", "texto_original")):
            continue
        expected = [(max(0, candidate["inicio"]-5), candidate["fin"]+2, 5),
                    (max(0, candidate["inicio"]-2), candidate["fin"]+4, 10)]
        if any((a.get("inicio"), a.get("fin"), a.get("beam_size")) != window
               for a, window in zip(attempts, expected)):
            continue
        amounts = [monetary_readings(a.get("texto", "")) for a in attempts]
        if len(amounts[0]) == 1 and amounts[0] == amounts[1] == {entry.get("amount")}:
            result.append(entry)
    return result
