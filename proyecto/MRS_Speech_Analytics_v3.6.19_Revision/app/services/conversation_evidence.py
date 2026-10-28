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


def sentence_evidence(text, segments=()):
    """Las ventanas de Whisper son acústicas; no delimitan frases ni turnos.

    Reunir oraciones del texto completo y conservar roles/timing solo cuando
    sus fragmentos los sustentan. Nunca se deduce una voz de SPEAKER_00/01.
    """
    source = normalize(text)
    spans, cursor = [], 0
    for unit in evidence_units(text, segments):
        folded = normalize(unit["text"])
        position = source.find(folded, cursor)
        if position >= 0:
            spans.append((position, position+len(folded), unit))
            cursor = position+len(folded)
    result, cursor = [], 0
    for unit in _text_units(text):
        folded = normalize(unit["text"])
        position = source.find(folded, cursor)
        if position < 0:
            result.append(unit)
            continue
        end = position+len(folded)
        overlaps = [u for a, b, u in spans if a < end and b > position]
        roles = {u["speaker_role"] for u in overlaps}
        if unit["speaker_role"] == "NO DETERMINADO" and len(roles) == 1:
            unit = dict(unit, speaker_role=next(iter(roles)))
        if overlaps and all(isinstance(u["start"], (int, float)) and isinstance(u["end"], (int, float)) for u in overlaps):
            unit = dict(unit, start=min(u["start"] for u in overlaps), end=max(u["end"] for u in overlaps))
        result.append(unit)
        cursor = end
    return result


def holder_confirmation(text, segments=()):
    """Confirmación conversacional del titular, independiente de la etiqueta Excel."""
    s = normalize(text)
    # Una confirmación aparente seguida de ausencia/tercero no acredita titular.
    counter = re.compile(r"\b(?:no (?:se encuentra|esta aqui|esta en casa)|no soy|soy su (?:espos[oa]|madre|padre|herman[oa])|es nuestro proveedor)\b")
    identification = (
        r"(?:me (?:puede|pueden|podria|podrian|podre|podeis) comunicar[, ]*(?:(?:por|de) favor[, ]*)?con|"
        r"me comunica[, ]*(?:(?:por|de) favor[, ]*)?con|estoy buscando a|hablo con|"
        r"tengo el gusto(?: de hablar)? con|me comunico con|(?<=¿)con)")
    prompt = re.compile(
        rf"\b{identification}\s+(?P<identity>[^.!?]{{2,100}})[.?]\s*"
        r"(?:ah[, ]+)?(?P<answer>(?:si[, ]+)?(?:digame|diganme|ella habla|el habla|con el habla|con ella habla|habla con el|habla con ella))\b")
    named_identity = re.compile(
        r"\b(?:tengo el gusto(?: de hablar)? con|me comunico con|hablo con|"
        r"buen(?:os dias| dia)[, ]+con|buenas tardes[, ]+con|(?<=¿)con)\s+"
        r"(?P<identity>[^.!?]{2,100})[.?]\s*(?:ah[, ]+)?"
        r"(?P<answer>si(?:[, ]+(?:digame|diganme))?|asi es|correcto|ella habla|el habla|digame|diganme)\b")
    # La presentación de la empresa puede separar la pregunta de «ella habla».
    # Solo una respuesta explícita de identidad permite saltar ese tramo.
    delayed_self_identity = re.compile(
        rf"\b{identification}\s+(?P<identity>[^.!?]{{2,100}})[.?].{{0,250}}?"
        r"(?P<answer>(?:si[, ]+)?(?:ella habla|el habla))(?=[.!?]|$)")
    direct = re.compile(
        r"\bes usted(?P<identity>[^.!?]{0,85})\?\s*"
        r"(?P<answer>si|asi es|correcto|aja)\b")
    contextual = re.compile(
        rf"\b{identification}\s+(?P<identity>[^.!?]{{2,100}})[.?]\s*"
        r"(?P<answer>si(?:[, ]+si)?[^.!?]{0,35})[.!?]\s*"
        r"(?:(?:buen(?:o|os)? dias?|buenas? tardes?|que tal|mucho gusto)[.!?]\s*){0,2}"
        r"(?:mucho gusto|me presento)\b")
    for pattern in (prompt, direct, contextual, named_identity, delayed_self_identity):
        for match in pattern.finditer(s):
            if pattern is not direct and re.search(
                    r"\b(?:familiar|espos[oa]|madre|padre|herman[oa]|referencia|quien|usted(?:es)?|"
                    r"banco|despacho|corporativo|cobranza|pago|deuda|cuenta|departamento|encargad[oa]|"
                    r"tarjeta|dinero|cantidad|telefono|linea|numero|servicio)\b", match["identity"]):
                continue
            if pattern is direct and match["identity"].strip() and not re.match(
                    r"(?:el caballero|la senora|la senorita|el senor|el titular|la titular|caballero|senora|senorita|senor)\b",
                    match["identity"].strip()):
                continue
            if pattern is direct and re.search(
                    r"\b(?:familiar|espos[oa]|madre|padre|herman[oa]|referencia|conocid[oa]|quien|pagar|pago)\b",
                    match["identity"]):
                continue
            if _role_at(text, segments, match.start("answer")) in {"GESTOR", "TERCERO"}:
                continue
            tail = s[match.end():match.end()+80]
            if (counter.search(match.group()+tail) or re.search(r"\b(?:obviamente )?no soy\b", s)
                    or re.search(r"\b(?:se lo comunico|le paso|permita|espere|no esta|lo busco|la busco)\b", match["answer"] + tail[:45])):
                continue
            return {"confirmed": True, "method": "RESPUESTA_A_IDENTIFICACION",
                    "evidence": match.group(), "speaker_role": "NO DETERMINADO"}
    return {"confirmed": False, "method": "SIN_CONFIRMACION", "evidence": ""}


def _role_at(text, segments, position):
    source, cursor = normalize(text), 0
    for unit in sentence_evidence(text, segments):
        folded = normalize(unit["text"])
        start = source.find(folded, cursor)
        if start >= 0:
            cursor = start+len(folded)
            if start <= position < cursor:
                return unit["speaker_role"]
    return "NO DETERMINADO"


def payment_commitment(text, segments=()):
    """Una propuesta, pregunta o mención de convenio no equivale a aceptación."""
    source = normalize(text)
    events, cursor = [], 0
    for unit in sentence_evidence(text, segments):
        s = normalize(unit["text"])
        position = source.find(s, cursor)
        if position >= 0:
            cursor = position + len(s)
        if unit["speaker_role"] == "GESTOR" or "?" in s or "¿" in s:
            continue
        positive = re.search(
            r"\b(?:me comprometo a (?:pagar|depositar|abonar|cubrir)|"
            r"(?:yo )?voy a (?:pagar|depositar|abonar|cubrir)|pagare|depositare|abonare|"
            r"(?:manana|el lunes|el martes|el miercoles|el jueves|el viernes|el sabado|el domingo) "
            r"(?:(?:le )?(?:pago|deposito)|mando a pagar(?:lo)?))\b", s)
        negative = re.search(
            r"\b(?:no (?:voy a|puedo|pienso|quiero) (?:pagar|depositar|abonar|cubrir)|"
            r"no puedo (?:comprometerme|confirmar|dar una fecha)|no me comprometo|"
            r"no tengo (?:esa|la) cantidad|no dispongo de (?:esa|la) cantidad|"
            r"no (?:tengo|cuento con) (?:dinero|la cantidad|esa cantidad)|"
            r"(?:manana|hoy) no (?:podria|puedo)|no (?:tendria|tendre)\s+(?:\d+|dos|mil))\b", s)
        conditional = re.search(
            r"\b(?:si me da tiempo|si consigo (?:el )?dinero|si tengo dinero|si puedo juntar|"
            r"lo podria(?: hacer)?|(?:yo )?pagaria|"
            r"hare lo posible|a lo mejor|yo creo|no se cuanto (?:voy a|vaya a|pueda) (?:pagar|depositar)|"
            r"no se cuando (?:pueda|voy a) pagar)\b", s)
        payment_context = re.search(r"\b(?:pago|pagar|depositar|dinero|cantidad|convenio|pesos|descuento)\b",
                                    source[max(0, position-220):cursor])
        if conditional and not payment_context:
            conditional = None
        if conditional:
            events.append((position, None, unit["text"]))
            continue
        if negative:
            events.append((position, False, unit["text"]))
        elif positive and not re.search(r"\b(?:no|si pudiera|si tuviera)\b.{0,18}"+re.escape(positive.group()), s):
            events.append((position, True, unit["text"]))
    question = re.compile(
        r"\b(?:podemos (?:contemplar|contar con|confirmar)|se compromete a|puedo confirmar|"
        r"confirmaria (?:su pago|el pago|la opcion))\b"
        r"[^?]{0,130}\b(?:pago|pagar|deposito|depositar)\b[^?]{0,90}\?\s*"
        r"(?P<answer>si|de acuerdo|esta bien|claro|correcto)\b")
    for match in question.finditer(source):
        if _role_at(text, segments, match.start("answer")) != "GESTOR":
            reply = source[match.start("answer"):match.end()+100].split(".")[0]
            if not re.search(r"\b(?:si me da tiempo|si consigo|si puedo juntar|yo creo|a lo mejor|no puedo|no tengo)\b", reply):
                events.append((match.start("answer"), True, match.group()))
    # La respuesta puede indicar el importe en lugar de repetir «sí». Se exige
    # una pregunta futura de pago, una cantidad explícita y una respuesta firme.
    amount_question = re.compile(
        r"\b(?:que cantidad|con que cantidad|por que cantidad)\b[^?!.]{0,100}"
        r"\b(?:confirmaria pagar|podemos contemplar|puede pagar|va a pagar)\b[^?!.]{0,60}\?\s*"
        r"(?P<answer>[^.!?]{1,110})")
    for match in amount_question.finditer(source):
        answer = match["answer"]
        if (_role_at(text, segments, match.start("answer")) in {"GESTOR", "TERCERO"}
                or not re.search(r"\b(?:\d{2,}|mil|cientos|quinientos)\b", answer)
                or re.search(r"\b(?:no|creo|a lo mejor|si consigo|si puedo|si me da)\b", answer)):
            continue
        events.append((match.start("answer"), True, match.group()))
    # Al corregir una propuesta, una aceptación nueva puede reemplazar una
    # condición anterior. Un «ok» aislado o responder sobre WhatsApp no basta.
    corrected_offer = re.compile(
        r"\b(?:cuanto me (?:dice|dices)|por que cantidad seria)\?\s*"
        r"[^.!?]{1,90}\bpesos\b[.!?]\s*(?P<answer>ok[, ]+esta bien|de acuerdo)\b")
    for match in corrected_offer.finditer(source):
        before = source[max(0, match.start()-220):match.start()]
        if (re.search(r"\b(?:pago|pagar|convenio|fecha)\b", before)
                and _role_at(text, segments, match.start("answer")) not in {"GESTOR", "TERCERO"}):
            events.append((match.start("answer"), True, match.group()))
    if not events:
        return {"accepted": False, "declined": False, "evidence": ""}
    _, accepted, evidence = max(events, key=lambda e: e[0])
    return {"accepted": accepted is True, "declined": accepted is False,
            "conditional": accepted is None, "evidence": evidence}


def completed_payment(text, segments=()):
    evidence = []
    source, cursor = normalize(text), 0
    for unit in sentence_evidence(text, segments):
        verbatim = unicodedata.normalize("NFC", re.sub(r"\s+", " ", unit["text"]).strip())
        s = normalize(verbatim)
        position = source.find(s, cursor)
        if position >= 0:
            cursor = position + len(s)
        if "?" in s or "¿" in s:
            continue
        candidates = list(re.finditer(
            r"\b(?:ya pague|yo pague|lo pague|pague (?:ayer|hoy)|ya (?:hice|realice) (?:mi |el |un )?pago|"
            r"(?:hice|realice) (?:mi|el|un) pago|lo realice|lo hice|depositamos|fui a realizar mi pago|"
            r"ya (?:mande|envie) (?:el |mi )?comprobante|ya (?:le )?di (?:un )?abono|"
            r"ya se pago|tengo registrado (?:un )?reporte de pago)\b", s))
        candidates.extend(re.finditer(r"\bpagué\b", verbatim, re.I))
        # Sin tilde, «realice» puede ser subjuntivo: una instrucción para un
        # pago futuro no acredita un depósito anterior, aunque mencione recibo.
        future_instructions = list(re.finditer(
            r"\b(?:una vez que|cuando|en cuanto|para que|despu[eé]s de que|si)\s+"
            r"(?:(?:usted|yo|ya|lo|me|le)\s+)*(?:realice|haga|pague|deposite|tenga)\b",
            verbatim, re.I))
        for candidate in candidates:
            if any(f.start() <= candidate.start() < f.end() for f in future_instructions):
                continue
            if re.search(r"\b(?:no|aun no|todavia no)\s+(?:he |lo )?$", s[:candidate.start()]):
                continue
            if unit["speaker_role"] == "GESTOR" and "tengo registrado" not in normalize(candidate.group()):
                continue
            start, end = position + candidate.start(), position + candidate.end()
            if position >= 0 and not any(u["text_start"] < end and u["text_end"] > start for u in evidence):
                evidence.append(dict(unit, text_start=start, text_end=end))
    # En una conversación natural, «sí» puede reportar el pago sin repetir
    # «ya pagué». «Puedo»/«pado» solo se toleran con una pregunta posterior
    # inequívoca de cuándo se hizo; nunca convierten una oferta futura en pago.
    question = re.compile(
        r"\bya (?P<verb>pudo|puedo|realizo|ha realizado|ha podido|hizo)\b[^?!]{0,95}"
        r"\b(?:pago|pado)\b[^?!]{0,25}\?\s*"
        r"(?:(?:titular|cliente|interlocutor)\s*:\s*)?(?P<answer>si|asi es)\b")
    for match in question.finditer(source):
        role = _role_at(text, segments, match.start("answer"))
        reply = source[match.start("answer"):match.end()+90].split(".")[0]
        if (role == "GESTOR" or re.search(r"\b(?:manana|proximo)\b", match.group())
                or re.search(r"\b(?:si puedo|si consigo|si me da|creo|no (?:pague|pude|lo hice|he pagado))\b", reply)
                or source[match.end():].lstrip().startswith("?")):
            continue
        followup = source[match.end():match.end()+180]
        past_question = re.search(
            r"\b(?:que dia lo (?:realice|realizo|hizo|pago)|cuando (?:lo )?(?:pago|realizo)|"
            r"que cantidad (?:pago|deposito))\b", followup)
        if match["verb"] == "puedo" and not past_question:
            continue
        if "pado" in match.group() and not past_question:
            continue
        evidence.append({"text": match.group(), "speaker_role": role, "start": None, "end": None,
                         "text_start": match.start(), "text_end": match.end(),
                         "method": "RESPUESTA_A_PAGO_REALIZADO"})
    return {"confirmed": bool(evidence), "evidence": evidence}


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
    for unit in sentence_evidence(text, segments):
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
    for unit in sentence_evidence(text, segments):
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
    for unit in sentence_evidence(text, segments):
        if unit["speaker_role"] in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            continue
        # Whisper puede unir «le ofrecemos un descuento, ¿lo acepta?» en una
        # oración. La pregunta posterior no elimina la oferta declarada.
        for clause in re.split(r"[;,]", unit["text"]):
            s = normalize(clause)
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
    for unit in sentence_evidence(text, segments):
        if unit["speaker_role"] in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            continue
        s = normalize(unit["text"])
        # La tienda de origen de la tarjeta no es una instrucción de pago.
        if not re.search(r"\b(?:puede pagar(?:lo|los)?|podra pagar(?:lo|los)?|puede realizar|realizar (?:su |el )?pago|"
                         r"pague|pagar(?:lo|los)? en|pago en|pago de servicio|deposite|depositar en|"
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
