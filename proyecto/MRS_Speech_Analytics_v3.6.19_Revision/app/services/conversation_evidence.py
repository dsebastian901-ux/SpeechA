"""Evidencia textual conservadora; no sustituye diarización ni escucha del audio."""

import re
import unicodedata


def normalize(text):
    return re.sub(r"\s+", " ", "".join(
        c for c in unicodedata.normalize("NFD", str(text or "").lower())
        if unicodedata.category(c) != "Mn"
    )).strip()


def role_of(value):
    value = normalize(value)
    if value in {"gestor", "agente", "asesor", "agent", "collector"}:
        return "GESTOR"
    if value in {"titular", "cardholder"}:
        return "TITULAR"
    if value in {"familiar", "tercero", "third_party"}:
        return "TERCERO"
    if value in {"interlocutor", "cliente", "customer"}:
        return "INTERLOCUTOR"
    # SPEAKER_00/01 son identidades, no roles operativos.
    return "NO DETERMINADO"


def _text_units(text, role="NO DETERMINADO", start=None, end=None):
    for line in str(text or "").splitlines():
        line_role = role
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            label = re.match(r"^\s*(gestor|agente|asesor|titular|familiar|tercero|interlocutor|cliente)\s*:\s*", sentence, re.I)
            if label:
                line_role = role_of(label[1])
                sentence = sentence[label.end():]
            if sentence.strip():
                yield {"text": sentence.strip(), "speaker_role": line_role,
                       "start": start, "end": end}


def evidence_units(text, segments=()):
    """Alinear segmentos con el texto; cubrir también texto final sin segmentos.

    Solo roles semánticos explícitos atribuyen voz. Un ID de Whisper o una
    etiqueta inferida de Excel no identifica al gestor. Los tiempos conservados
    corresponden al segmento completo, nunca a palabras inventadas.
    """
    source = normalize(text)
    cursor = 0
    units = []
    for segment in segments or ():
        if not isinstance(segment, dict):
            continue
        fragment = segment.get("text", segment.get("texto", ""))
        folded = normalize(fragment)
        if not folded:
            continue
        position = source.find(folded, cursor)
        if position < 0:
            continue  # Un segmento ajeno al texto no demuestra una infracción.
        units.extend(_text_units(source[cursor:position]))
        role = role_of(segment.get("speaker_role") or segment.get("role") or segment.get("speaker"))
        units.extend(_text_units(fragment, role,
                                 segment.get("start", segment.get("inicio")),
                                 segment.get("end", segment.get("fin"))))
        cursor = position + len(folded)
    units.extend(_text_units(source[cursor:] if cursor else text))
    return units


KIN = r"(?:espos[oa]|marido|mujer|pareja|herman[oa]|hij[oa]|mama|madre|papa|padre|sobrin[oa]|prim[oa]|ti[oa]|abuel[oa]|cunad[oa])"
FAMILY = re.compile(rf"\b(?:(?:soy|era) (?:su |un |una )?familiar|soy su {KIN}|(?:es|era) mi {KIN}|(?:es|era) (?:espos[oa]|pareja) de mi {KIN})\b")
ACCEPTANCE = re.compile(
    r"\b(?:lo anoto|lo puedo anotar|puedo anotarlo|yo se lo (?:envio|mando)|"
    r"yo le aviso|le (?:paso|doy|transmito) el recado|se lo comunico|"
    r"se lo hago saber|le hago llegar el mensaje|le voy a (?:pasar|dar) el (?:recado|mensaje))\b")
DECLINES = re.compile(
    r"\b(?:no (?:quiero|puedo|voy a) (?:recibir|tomar|anotar|pasar|dar|transmitir)|"
    r"no (?:le|se lo) (?:voy a |puedo |quiero )?(?:pasar|dar|mandar|avisar)|"
    r"no tengo (?:con que|donde|como|forma de) (?:anotar|apuntar|contactar|avisar)|"
    r"no soy (?:su )?mensajer[oa]|no me interesa recibir el recado)\b")


def assess_recado(text, segments=()):
    families, acceptances, refusals, unknown = [], [], [], []
    for unit in evidence_units(text, segments):
        s = normalize(unit["text"])
        if unit["speaker_role"] in {"GESTOR", "TITULAR"}:
            continue
        if re.search(r"\b(?:no (?:lo|la) conozco|no se quien es|numero equivocado)\b", s):
            unknown.append(unit)
        if DECLINES.search(s):
            refusals.append(unit)
        for match in FAMILY.finditer(s):
            prefix = s[max(0, match.start()-55):match.start()]
            suffix = s[match.end():match.end()+25]
            if ("?" in s or "¿" in s
                    or re.search(r"\b(?:no|no es|no era|no soy|(?:no se si|creo que|tal vez|quizas)(?: es| sea)?|usted es|usted seria)\s*$", prefix)
                    or re.match(r"\s*[,;]?\s*(?:verdad|correcto|cierto)\b", suffix)):
                continue
            families.append(dict(unit, phrase=match.group()))
        if ACCEPTANCE.search(s) and not DECLINES.search(s) and "?" not in s and "¿" not in s:
            # Una cita o una instrucción del gestor no confirma recepción.
            if not re.search(r"\b(?:diga|digale|dijera|dijera que|diga que|gracias por|no)\b.{0,25}" + ACCEPTANCE.pattern, s):
                acceptances.append(unit)
    return {"family": families, "acceptance": acceptances,
            "refusal": refusals, "unknown_recipient": unknown}


def recipient_statement(text, segments, pattern):
    """No usar preguntas, negaciones ni palabras del gestor como identidad."""
    for unit in evidence_units(text, segments):
        if unit["speaker_role"] == "GESTOR":
            continue
        s = normalize(unit["text"])
        if "?" in s or "¿" in s:
            continue
        for match in re.finditer(pattern, s):
            prefix = s[max(0, match.start()-25):match.start()]
            if not re.search(r"\b(?:no|si fuera|creo que)\s*$", prefix):
                return True
    return False


def agent_statement(text, segments, pattern):
    for unit in evidence_units(text, segments):
        if unit["speaker_role"] in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            continue
        s = normalize(unit["text"])
        if "?" in s or "¿" in s:
            continue
        for match in re.finditer(pattern, s):
            prefix = s[max(0, match.start()-70):match.start()]
            if not re.search(r"\bno\b[^.!?;]{0,65}$", prefix):
                return True
    return False


def payment_places(text, segments, catalog):
    """Lugares ofrecidos para pagar, sin duplicar marcas anidadas ni negadas."""
    found = {}
    for unit in evidence_units(text, segments):
        if unit["speaker_role"] in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            continue
        s = normalize(unit["text"])
        # La tienda de origen de la tarjeta no es una instrucción de pago.
        if not re.search(r"\b(?:puede pagar|podra pagar|puede realizar|realizar (?:su |el )?pago|"
                         r"pague|pagar en|pago en|pago de servicio|deposite|depositar en|"
                         r"lugares de pago|opciones de pago|convenio (?:numero )?\d)\b", s):
            continue
        matches = []
        for place, variants in catalog.items():
            for variant in variants:
                for match in re.finditer(r"(?<!\w)" + re.escape(normalize(variant)) + r"(?!\w)", s):
                    matches.append((match.start(), match.end(), place, match.group()))
        selected = []
        for start, end, place, phrase in sorted(matches, key=lambda x: -(x[1]-x[0])):
            if any(start < b and end > a for a, b in selected):
                continue
            selected.append((start, end))
            before = s[max(0, start-100):start]
            if re.search(r"\bno\b.{0,80}\b(?:pagar|pague|en)\b", before):
                continue
            found[place] = dict(unit, phrase=phrase, place=place)
    return list(found.values())


SENSITIVE = re.compile(
    r"\b(?:saldo (?:pendiente|vencido|total|de\s+\d[\d.,]*|es\s+\d[\d.,]*)|"
    r"(?:tiene|presenta|cuenta con) (?:un |una |dos |tres |cuatro |\d+ )?(?:deuda|adeudo|atraso|mensualidades)|"
    r"(?:\d+|un|una|dos|tres|cuatro|cinco|seis) (?:mes(?:es)?|mensualidades)(?: de)? (?:atraso|vencid[ao]s?)|"
    r"(?:deuda|adeudo|pago minimo|monto) (?:de |es |por )?\d[\d.,]*|"
    r"(?:adeuda|debe)\s+(?:\d[\d.,]*|mil|cien|doscientos|trescientos|quinientos)|"
    r"(?:su|una|la) deuda|cubrir (?:el |su )?atraso|respecto a su atraso|"
    r"negativa de pago|recuperacion (?:del|de su|en el) saldo|"
    r"pagos? vencidos?|incumplimiento (?:al|del|de) contrato|"
    r"(?:tiene|maneja|cuenta con) (?:una |la |su )?tarjeta)\b")
CARD = re.compile(r"\b(?:tarjeta|referencia|plastico|numero de cuenta)\s*(?:(?:numero|de pago|es|de)\s*)?(?:\d[ -]?){15}\d\b")


def assess_privacy(text, segments=(), *, third_party_confirmed=False,
                   expected_third_party=False, titular=False, legacy_financial=False):
    evidence = []
    last_recipient = None
    for unit in evidence_units(text, segments):
        role = unit["speaker_role"]
        if role in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            last_recipient = role
        s = normalize(unit["text"])
        matches = list(SENSITIVE.finditer(s)) + list(CARD.finditer(s))
        for match in matches:
            prefix = s[max(0, match.start()-30):match.start()]
            hypothetical = bool("?" in s or "¿" in s or re.search(r"\b(?:si|no|nunca)\s*$", prefix)
                                or re.search(r"\b(?:no tiene|sin|si tuviera|en caso de)\b", s))
            protected = third_party_confirmed and last_recipient != "TITULAR"
            confirmed = role == "GESTOR" and protected and not hypothetical
            uncertain = (role == "NO DETERMINADO" or hypothetical
                         or (role == "GESTOR" and not titular and last_recipient != "TITULAR" and not protected))
            relevant = third_party_confirmed or expected_third_party or not titular
            evidence.append(dict(unit, phrase=match.group(), confirmed=confirmed,
                                 review_required=bool(relevant and uncertain)))
    # Conserva los bloqueos previos que aún no tienen un extractor específico.
    if legacy_financial and not evidence and (third_party_confirmed or expected_third_party or not titular):
        evidence.append({"text": "Señal financiera contextual sin atribución de voz confirmada.",
                         "speaker_role": "NO DETERMINADO", "start": None, "end": None,
                         "phrase": "", "confirmed": False, "review_required": True})
    confirmed = any(e["confirmed"] for e in evidence)
    review = any(e["review_required"] for e in evidence) and not confirmed
    return {"confirmed_disclosure": confirmed, "review_required": review,
            "third_party_confirmed": bool(third_party_confirmed), "evidence": evidence,
            "reason": ("Divulgación atribuida al gestor ante un tercero confirmado." if confirmed else
                       "Posible divulgación financiera; confirmar hablante y destinatario en audio." if review else
                       "Sin divulgación a terceros confirmada.")}
