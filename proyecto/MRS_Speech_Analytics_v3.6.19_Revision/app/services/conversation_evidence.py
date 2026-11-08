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
    from app.services.contextual_identity_evidence import valid_nominal_request, proxy_account_evidence
    if proxy_account_evidence(text,segments):
        return {"confirmed":False,"method":"CUENTA_DE_OTRA_PERSONA","evidence":""}
    # Una confirmación aparente seguida de ausencia/tercero no acredita titular.
    counter = re.compile(r"\b(?:no (?:se encuentra|esta aqui|esta en casa)|no soy|soy su (?:espos[oa]|madre|padre|herman[oa])|es nuestro proveedor)\b")
    identification = (
        r"(?:me (?:puede|puedes|pueden|puedo|pude|podria|podrias|podrian|podre|podeis) comunicar[, ]*(?:(?:por|de) favor[, ]*)?(?:con|a)|"
        r"me comunican?[, ]*(?:(?:por|de) favor[, ]*)?con|me comunique con|me puede conectar con|"
        r"(?:me )?voy a comunicar con|puede comunicar con|"
        r"buen(?:os dias| dia)[, ]+con|buenas tardes[, ]+con|se encuentra|estoy buscando a|hablo con|"
        r"me estoy comunicando al numero telefonico de|seria tan amable de comunicarme con|"
        r"tengo(?: el)? (?:gusto|uso)(?: de hablar)? (?:con|a)|me comunico con|(?<=¿)con)")
    explicit_answer = r"(?:ah[, ]+)?(?P<answer>(?:si[, ]+)?(?:digame|diganme|dime|servidor|servidora|al habla|ella habla|el habla|con el habla|con ella habla|habla con el|habla con ella))\b"
    prompt = re.compile(
        rf"\b{identification}\s+(?P<identity>[^.!?]{{2,100}}?)(?:[.?]|,)\s*" + explicit_answer)
    salutation_prompt = re.compile(
        r"\b(?:buen dia|buenos dias|buenas tardes)[,. ]+"
        r"(?:juridico[, ]+m[. ]*r[. ]*s[. ]*)?con\s+"
        r"(?P<identity>[^.!?]{2,100}?)(?:[.?]|,)\s*" + explicit_answer)
    named_identity = re.compile(
        r"\b(?:tengo(?: el)? (?:gusto|uso)(?: de hablar)? (?:con|a)|me comunico con|hablo con|"
        r"buen(?:os dias| dia)[, ]+con|buenas tardes[, ]+con|(?<=¿)con)\s+"
        r"(?P<identity>[^.!?]{2,100})[.?]\s*(?:ah[, ]+)?"
        r"(?P<answer>si(?:[, ]+(?:digame|diganme|servidor|servidora))?|asi es|correcto|ella habla|el habla|digame|diganme|servidor|servidora)\b")
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
    split_honorific = re.compile(
        r"\btengo el gusto con (?:el senor|la senora|la senorita)[.]\s*"
        r"(?P<identity>[^.!?]{2,85})[.?]\s*(?P<answer>si|asi es|ella habla|el habla)\b")
    greeted_identity = re.compile(
        rf"\b{identification}\s+(?P<identity>[^.!?]{{2,100}})[.?]\s*"
        r"(?P<answer>si)[.!]\s*(?:muy )?(?:buenos dias|buen dia|buenas tardes)"
        r"(?:[, ]+(?:senor|senora|senorita|caballero)[^.!?]{0,65})?[.!]\s*"
        r"(?:mi nombre es|me presento|le marcamos)\b")
    company_reply = re.compile(
        rf"\b{identification}\s+(?P<identity>[^.!?]{{2,100}})[.?]\s*"
        r"¿?(?:de (?:donde habla|parte de quien)|quien habla)(?:[, ]+perdon)?\?\s*"
        r"(?P<bridge>[^.!?]{1,130}\b(?:mrs|corporativo|juridico)\b[^.!?]{0,60})[.!]\s*"
        r"(?P<answer>(?:ah[, ]+)?(?:si[, ]+)?(?:digame|diganme|dime))\b")
    for pattern in (prompt, salutation_prompt, direct, contextual, named_identity, delayed_self_identity, split_honorific, greeted_identity, company_reply):
        for match in pattern.finditer(s):
            if not valid_nominal_request(s,match.start(),match["identity"]):continue
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
            if pattern is company_reply and re.search(r"\b(?:se lo comunico|te hablan|le paso|no esta|no se encuentra)\b",match['bridge']):
                continue
            tail = s[match.end():match.end()+80]
            if (counter.search(match.group()+tail) or re.search(r"\bno soy (?:esa persona|ese senor|el titular|la titular)\b", s)
                    or re.search(r"\b(?:se lo comunico|le paso|permita|espere|no esta|lo busco|la busco)\b", match["answer"] + tail[:45])):
                continue
            return {"confirmed": True, "method": "RESPUESTA_A_IDENTIFICACION",
                    "evidence": match.group(), "speaker_role": "NO DETERMINADO"}
    # Autorreferencia independiente del Excel: pregunta nominal + respuesta
    # sobre la PROPIA cuenta/tarjeta. «No tengo dinero»/«sí» solos no bastan.
    # No transforma en titular a un familiar que paga por otra persona.
    request = re.search(rf"\b{identification}\s+(?P<identity>[^.!?]{{2,100}}?)(?:[.?]|,\s*gracias\b)", s)
    third_person = re.search(
        r"\b(?:soy su |es mi (?:espos[oa]|herman[oa]|sobrin[oa]|hij[oa]|madre|padre)|"
        r"no soy (?:esa persona|ese senor|el titular|la titular)|no esta (?:aqui|en casa)|"
        r"no se encuentra(?: aqui)?|se lo comunico|le paso (?:al titular|con el|con ella)|lo busco|la busco|"
        r"no es mi (?:tarjeta|cuenta)|pago por (?:el|ella)|cuenta de mi|es nuestro proveedor|"
        r"soy (?:su )?(?:companero|companera|amigo|amiga|vecino|vecina|familiar)|"
        r"(?:solicite|saque|contrate|tramite|adquiri) (?:la |una )?tarjeta (?:para|a nombre de) (?:ella|mi (?:espos[oa]|madre|padre|hij[oa]|herman[oa])))\b", s)
    ownership = re.compile(
        r"\b(?:mi (?:tarjeta|cuenta|saldo|estado de cuenta|aplicacion|pago)|"
        r"yo (?:tengo|tenia) una (?:cuenta|tarjeta)|"
        r"yo (?:solicite|saque|contrate|tramite|adquiri) (?:mi |la |una |esa |esta )?(?:cuenta|tarjeta)|"
        r"(?:yo )?(?:cancele|bloquee|rompi) (?:mi |la )?tarjeta)\b")
    requested_person=(re.sub(r'^(?:(?:el|la) )?(?:senorita|senora|senor|caballero)\s*','',request['identity']).strip(', ')
                      if request else '')
    if request and valid_nominal_request(s,request.start(),request["identity"]) and re.search(r'[a-z]{2,}',requested_person) and not third_person and not re.search(
            r"\b(?:familiar|espos[oa]|madre|padre|herman[oa]|banco|despacho|corporativo|tarjeta|pago|deuda|cuenta|servicio)\b", request['identity']):
        for unit in sentence_evidence(text, segments):
            if unit["speaker_role"] in {"GESTOR", "TERCERO"}:
                continue
            value = normalize(unit["text"])
            if ownership.search(value) and not re.search(
                    r"\b(?:si tuviera|si tuviese|si yo tuviera|diga|digale|repita|usted dice|usted dijo|el cliente dice)\b", value):
                return {"confirmed": True, "method": "AUTORREFERENCIA_CUENTA_TRAS_IDENTIFICACION",
                        "evidence": request.group()+" / "+unit["text"],
                        "speaker_role": unit["speaker_role"]}
    from app.services.contextual_identity_evidence import contextual_holder_confirmation
    contextual_identity=contextual_holder_confirmation(text,segments,identification)
    if contextual_identity['confirmed']:
        return contextual_identity
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


def unknown_recipient_response(text, segments=()):
    """Una respuesta explícita a la pregunta de conocimiento del titular.

    «No» aislado tras una pregunta negativa es ambiguo. «No, para nada» sí
    expresa desconocimiento; nunca se toma una respuesta conocida del gestor.
    """
    source=normalize(text)
    if recipient_statement(text,segments,
            r"\b(?:si (?:lo |la )?(?:conozco|conocemos)|soy yo|soy (?:el |la )?titular|"
            r"soy su (?:herman[oa]|madre|padre|hij[oa]|sobrin[oa])|es mi (?:herman[oa]|madre|padre|hij[oa]|sobrin[oa]))\b"):
        return {'confirmed':False,'method':'RESPUESTAS_CONTRADICTORIAS','evidence':''}
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role']=='GESTOR':continue
        if re.fullmatch(r'no (?:lo|la) conocemos(?: aqui| en (?:esta|la|nuestra) casa)?[.!]?|'
                        r'no conocemos a (?:esa|esta) persona[.!]?',normalize(unit['text'])):
            return {'confirmed':True,'method':'DECLARACION_PLURAL_DESCONOCIMIENTO',
                    'evidence':unit['text'],'speaker_role':unit['speaker_role'],
                    'start':unit['start'],'end':unit['end']}
    question=re.compile(r"\bno (?:lo |la )?conoce(?:s)?(?: (?:a |para )?[^?!.]{0,65})?\?\s*"
                        r"(?P<answer>no[, ]+(?:para nada|jamas|nunca))\b")
    for match in question.finditer(source):
        role=_role_at(text,segments,match.start('answer'))
        after=source[match.end():match.end()+60]
        if role=='GESTOR' or re.search(r"\b(?:si (?:lo |la )?conozco|es mi familiar|es mi hermana)\b",after):
            continue
        return {'confirmed':True,'method':'RESPUESTA_EXPLICITA_DE_DESCONOCIMIENTO',
                'evidence':match.group(),'speaker_role':role}
    return {'confirmed':False,'method':'SIN_RESPUESTA_EXPLICITA','evidence':''}


def associate_relationship(text, segments=()):
    """Una relación plural explícita acredita tercero, no parentesco ni recado."""
    for unit in sentence_evidence(text, segments):
        if unit['speaker_role'] in {'GESTOR', 'TITULAR'}:
            continue
        if re.fullmatch(
                r'(?:(?:pues|bueno)[, ]+)?(?:solo )?somos (?:solo )?'
                r'(?:conocid[oa]s|amig[oa]s)[.!]?', normalize(unit['text'])):
            return {'confirmed': True, 'method': 'RELACION_PLURAL_EXPLICITA',
                    'evidence': unit['text'], 'speaker_role': unit['speaker_role'],
                    'start': unit['start'], 'end': unit['end']}
    source=normalize(text)
    question=re.compile(
        r'\b(?:es usted[^?!.]{0,70}\b(?:conocid[oa]|amig[oa]|familiar)\b[^?!.]{0,45}|'
        r'(?:me puede indicar )?que es usted[^?!.]{0,90}|solo conocid[oa])\?\s*'
        r'(?P<answer>(?:si[, ]+)?(?:(?:soy |solo )?(?:una? |su )?)?(?:conocid[oa]|amig[oa]))\b')
    for match in question.finditer(source):
        role=_role_at(text,segments,match.start('answer'))
        tail=source[match.end():match.end()+45]
        if (role not in {'GESTOR','TITULAR'} and not re.match(r'\s*\?',tail)
                and not re.search(r'\b(?:no|no se si|creo que|tal vez)\s*$',source[max(0,match.start()-25):match.start()])):
            return {'confirmed':True,'method':'RESPUESTA_RELACION_CONOCIDO',
                    'evidence':match.group(),'speaker_role':role,'start':None,'end':None}
    return {'confirmed': False, 'method': 'SIN_RELACION_PLURAL_EXPLICITA', 'evidence': ''}


def _payment_review_condition(value):
    explicit = re.search(r'\b(?:voy a hacer ?lo posible|voy a hacerlo posible|'
                         r'(?:esto|eso) es lo que no tengo|'
                         r'para ver si me puedo comprometer|'
                         r'(?:checar|revisar) mis cuentas[^.!?]{0,65}para ver si|'
                         r'aun no lo tengo (?:asi )?confirmado|'
                         r'no quisiera que me (?:hiciera|hicieran) (?:hasta )?(?:el |un )?convenio|'
                         r'ya les digo si puedo o no|'
                         r'(?:yo )?(?:requeriria|necesito|quiero) que me (?:entreguen|den|envien) primero|'
                         r'estoy esperando (?:un |el )?dinero|ya que me caiga (?:ese |el )?dinero)\b', value)
    if explicit:
        return explicit
    return re.search(
        r'\bsi (?:es necesari[oa]|corresponde|procede|'
        r'me (?:aclaran|explican) (?:los cargos|el adeudo|la deuda)|'
        r'se aclara (?:el saldo|la deuda|el adeudo))'
        r'(?=\s*(?:[,;.!]|$|(?:yo )?(?:pago|pagare|voy a pagar|depositare|abonare)\b))', value)


def _payment_review_deferral(value):
    match = re.search(
        r'\b(?:primero|antes(?: de pagar)?) (?:yo )?'
        r'(?:voy a|tengo que|necesito|quiero) (?:analizar|revisar|consultar|verificar|aclarar|preguntar)'
        r'\b[^.!?]{0,110}\b(?:pagos?|cargos|deuda|adeudo|cobros?|estado de cuenta|aclaracion)\b', value)
    if match and re.search(r'\b(?:comprobante|ticket|recibo|whatsapp)\b', value):
        if not re.search(r'\b(?:cargos|deuda|adeudo|cobros|aclaracion)\b', value):
            return None  # Preparar un comprobante no revoca un pago futuro firme.
    return match


def payment_commitment(text, segments=()):
    """Una propuesta, pregunta o mención de convenio no equivale a aceptación."""
    source = normalize(text)
    events, cursor = [], 0
    for unit in sentence_evidence(text, segments):
        s = normalize(unit["text"])
        position = source.find(s, cursor)
        if position >= 0:
            cursor = position + len(s)
        if unit["speaker_role"] == "GESTOR":
            continue
        if '?' in s or '¿' in s:
            s = s.split('¿', 1)[0].strip() if '¿' in s else ''
            if not s or '?' in s:
                continue
        positive = re.search(
            r"\b(?:me comprometo a (?:pagar|depositar|abonar|cubrir)|"
            r"(?:yo )?voy a (?:ir a )?(?:pagar|depositar|abonar|cubrir)|lo voy a realizar|pagare|depositare|abonare|"
            r"(?:hoy|manana) (?:mismo )?(?:deposito|abono|lo hago|lo realizo|hago el deposito|hago el pago)|"
            r"(?:manana|(?:el )?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)) "
            r"(?:(?:le )?(?:pago|deposito)|mando a pagar(?:lo)?))\b", s)
        if positive and positive.group() == 'pagare' and re.search(
                r'\b(?:el|un|su|del|al|ese|este)(?: (?:supuesto|mencionado))?\s*$', s[:positive.start()]):
            positive = None  # El documento «pagaré» no es «yo pagaré».
        if positive and positive.group() == 'lo voy a realizar' and not re.search(
                r'\b(?:pagos?|pagar|deposito|depositar|abono)\b', source[max(0,position-220):cursor]):
            positive = None  # «Lo» necesita un antecedente de pago, no otro trámite.
        negative = re.search(
            r"\b(?:no (?:(?:le|les|lo) )?(?:voy a|puedo|pienso|quiero) (?:pagar|depositar|abonar|cubrir)|"
            r"no he podido realizarlo|no he podido ir (?:porque|hasta)|no les voy a completar|no voy a poder[.!]?$|"
            r"no puedo (?:comprometerme|confirmar|dar una fecha)|no me comprometo|"
            r"no tengo (?:esa|la) cantidad|no dispongo de (?:esa|la) cantidad|"
            r"no (?:tengo|cuento con) (?:(?:todo |una? |la |esa )?(?:cierta )?cantidad de )?dinero|"
            r"no tengo todo el dinero|no (?:tengo|cuento con) (?:la cantidad|esa cantidad)|"
            r"no tengo (?:ni )?(?:para |pal )?(?:abonar|pagar)|"
            r"no (?:lo )?(?:puedo|voy a poder) (?:pagar|hacer)|no lo confirmo|"
            r"(?:manana|hoy) no (?:podria|puedo)|no (?:tendria|tendre)\s+(?:\d+|dos|mil))\b", s)
        conditional = re.search(
            r"\b(?:si me da tiempo|si consigo (?:el )?dinero|si tengo dinero|si puedo juntar|"
            r"lo podria(?: hacer)?|(?:yo )?pagaria|"
            r"hare lo posible|a lo mejor|yo creo|no sabria decir(?:le|te)? (?:si|cuanto|cuando)|no se cuanto (?:voy a|vaya a|pueda) (?:pagar|depositar)|"
            r"no se cuando (?:pueda|voy a) pagar)\b", s)
        conditional = conditional or _payment_review_condition(s) or (not positive and _payment_review_deferral(s))
        payment_context = re.search(r"\b(?:pagos?|paguito|pagar|pagare|deposito|depositar|dinero|cantidad|convenio|pesos|descuento)\b",
                                    source[max(0, position-220):cursor])
        if conditional and not payment_context:
            conditional = None
        if conditional and not (positive or negative) and re.search(
                r"\b(?:no se (?:ha )?reflejado|no (?:habia|tenia|tienen) sistema|"
                r"ustedes son|empresa.*seria)\b", s):
            conditional = None
        if conditional and re.search(r"\b(?:lo podria repetir|podria repetirlo)\b",s):
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
        r"(?:se )?confirmaria|confirma(?:mos|s)?|puede confirmar|seria posible|estarias? confirmando)\b"
        r"[^?¿]{0,130}\b(?:pago|pagar|deposito|depositar)\b[^?¿]{0,90}\?\s*"
        r"(?:(?:titular|cliente|interlocutor|gestor|tercero)\s*:\s*)?"
        r"(?P<answer>si|de acuerdo|esta bien|claro|correcto)\b")
    for match in question.finditer(source):
        if (_role_at(text, segments, match.start("answer")) not in {"GESTOR","TERCERO"}
                and not re.search(r'\b(?:realizado|efectuado|ayer|pasado|recibido|reportado|whatsapp|comprobante|telefono|recibo)\b',source[match.start():match.start('answer')])):
            reply = source[match.start("answer"):match.end()+100].split(".")[0]
            if not (re.search(r"\b(?:si me da tiempo|si consigo|si puedo juntar|yo creo|a lo mejor|no puedo|no tengo)\b", reply)
                    or _payment_review_condition(reply) or _payment_review_deferral(reply)):
                events.append((match.start("answer"), True, match.group()))
    agreement_question=re.compile(
        r'\bpodemos (?:poner|generar|formalizar) (?:su |el |un )?convenio\b'
        r'[^.!?]{0,80}\b(?:hoy|manana|el dia \d{1,2}|el (?:lunes|martes|miercoles|jueves|viernes|sabado|domingo))\b'
        r'[^.!?]{0,40}[.?]\s*(?:(?:titular|cliente|interlocutor|gestor|tercero)\s*:\s*)?'
        r'(?P<answer>(?:aja[, ]+)?(?:si|de acuerdo|esta bien|correcto))\b')
    for match in agreement_question.finditer(source):
        reply=source[match.start('answer'):match.end()+100].split('.')[0]
        if (_role_at(text,segments,match.start('answer')) not in {'GESTOR','TERCERO'}
                and not _payment_review_condition(reply) and not _payment_review_deferral(reply)
                and not re.search(r'\b(?:si puedo|si consigo|no puedo|yo creo|a lo mejor)\b',reply)):
            events.append((match.start('answer'),True,match.group()))
    # La respuesta puede indicar el importe en lugar de repetir «sí». Se exige
    # una pregunta futura de pago, una cantidad explícita y una respuesta firme.
    amount_question = re.compile(
        r"\b(?:que cantidad|con que cantidad|por que cantidad)\b[^?!.]{0,100}"
        r"\b(?:confirmaria pagar|podemos contemplar|puede pagar|va a pagar|va a realizar (?:su |el )?pago)\b[^?!.]{0,60}\?\s*"
        r"(?P<answer>[^.!?]{1,110})")
    for match in amount_question.finditer(source):
        answer = match["answer"]
        if (_role_at(text, segments, match.start("answer")) in {"GESTOR", "TERCERO"}
                or not re.search(r"\b(?:\d{2,}|mil|cientos|quinientos)\b", answer)
                or re.search(r"\b(?:no|creo|a lo mejor|si consigo|si puedo|si me da)\b", answer)
                or _payment_review_condition(answer) or _payment_review_deferral(answer)):
            continue
        events.append((match.start("answer"), True, match.group()))
    future_question = re.compile(
        r"\b(?:ya tendra(?:n)? (?:usted )?(?:el |su )?pago para (?:hoy|manana)|"
        r"podemos contar con (?:su |el )?pago (?:para )?(?:hoy|manana))[^?!.]{0,45}\?\s*"
        r"(?P<answer>si(?:[, ]+[^.!?]{0,65})?)")
    for match in future_question.finditer(source):
        if (_role_at(text, segments, match.start('answer')) not in {'GESTOR', 'TERCERO'}
                and not re.search(r"\b(?:creo|si puedo|si consigo|si me da|no puedo|a lo mejor)\b", match['answer'])
                and not _payment_review_condition(match['answer']) and not _payment_review_deferral(match['answer'])):
            events.append((match.start('answer'), True, match.group()))
    # Al corregir una propuesta, una aceptación nueva puede reemplazar una
    # condición anterior. Un «ok» aislado o responder sobre WhatsApp no basta.
    corrected_offer = re.compile(
        r"\b(?:cuanto me (?:dice|dices)|por que cantidad seria)\?\s*"
        r"[^.!?]{1,90}\bpesos\b[.!?]\s*(?P<answer>ok[, ]+esta bien|de acuerdo)\b")
    for match in corrected_offer.finditer(source):
        before = source[max(0, match.start()-220):match.start()]
        if (re.search(r"\b(?:pago|pagar|convenio|fecha)\b", before)
                and _role_at(text, segments, match.start("answer")) not in {"GESTOR", "TERCERO"}
                and not _payment_review_condition(source[match.start('answer'):match.end()+100].split('.')[0])
                and not _payment_review_deferral(source[match.start('answer'):match.end()+100].split('.')[0])):
            events.append((match.start("answer"), True, match.group()))
    # Aceptación del importe que se acaba de confirmar, sin confundir la
    # recepción de un número de WhatsApp ni la confirmación de un pago pasado.
    confirmation = re.compile(
        r"\bconfirm(?:a|aria|o) (?:usted )?(?:su |el |un )?pago\b"
        r"(?P<offer>[^.!?]{0,100}(?:\d[\d.,]*|pesos)[^.!?]{0,65})[.?]\s*"
        r"(?P<answer>si(?:[, ]+esta bien)?|de acuerdo|correcto|esta bien)\b")
    for match in confirmation.finditer(source):
        after=source[match.end():match.end()+60].split('.')[0]
        before=source[max(0,match.start()-70):match.start()]
        if (not re.search(r"\b(?:no|diga|diga que|usted dice|por ejemplo)\s*$",before)
                and not re.search(r"\b(?:realizado|pago|hizo|ayer|pasado|recibido|reportado)\b",match['offer'])
                and not re.search(r"\b(?:pero|no puedo|si consigo|a lo mejor|creo)\b",after)
                and not _payment_review_condition(source[match.start('answer'):match.end()+100].split('.')[0])
                and not _payment_review_deferral(source[match.start('answer'):match.end()+100].split('.')[0])
                and _role_at(text,segments,match.start('answer')) not in {'GESTOR','TERCERO'}):
            events.append((match.start('answer'),True,match.group()))
    from app.services.dialogue_confirmation_evidence import future_confirmation_events
    extra_events = future_confirmation_events(text,segments)
    events.extend((event['position'],True,event['evidence']) for event in extra_events)
    if not events:
        return {"accepted": False, "declined": False, "evidence": ""}
    _, accepted, evidence = max(events, key=lambda e: e[0])
    return {"accepted": accepted is True, "declined": accepted is False,
            "conditional": accepted is None, "evidence": evidence,
            "contextual_confirmation_events":extra_events}


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
            r"(?:hice|realice) (?:mi|el|un|ese|este) pago|lo realice|lo hice|depositamos|fui a realizar mi pago|"
            r"(?:(?:el|mi|ese|este) )?pago ya se (?:realizo|hizo|aplico)|"
            r"ya (?:hice|realice) (?:mi |el |un )?deposito|"
            r"(?:yo )?hice (?:mi |el |una? )?transferencia|"
            r"ya (?:mande|envie) (?:el |mi )?comprobante|ya (?:le )?di (?:un )?abono|"
            r"ya esta saldada|ya (?:la )?liquide|ya se pago|ya se (?:hizo|realizo) (?:el |un )?pago|(?:ayer |hoy |ya )pagamos|(?:el |mi )?pago ya esta (?:hecho|realizado)|"
            r"fui a abonar|ya abone|tengo registrado (?:un )?reporte de pago)\b", s))
        candidates.extend(re.finditer(r"\bpagué\b", verbatim, re.I))
        candidates.extend(re.finditer(r"\bdeposité\b", verbatim, re.I))
        candidates.extend(re.finditer(r"\brealicé (?:mi|el|un) pago\b", verbatim, re.I))
        # Sin tilde, «realice» puede ser subjuntivo: una instrucción para un
        # pago futuro no acredita un depósito anterior, aunque mencione recibo.
        future_instructions = list(re.finditer(
            r"\b(?:una vez que|cuando|en cuanto|para que|despu[eé]s de que|si)\s+"
            r"(?:(?:usted|yo|ya|lo|me|le)\s+)*(?:realice|haga|pague|deposite|tenga)\b",
            verbatim, re.I))
        for candidate in candidates:
            if re.search(r'\b(?:vamos a|le enviaremos|le estaremos|le mandaremos|cuando recibamos|en caso de que)\b[^.!?]{0,100}$',s[:candidate.start()]):
                continue
            if any(f.start() <= candidate.start() < f.end() for f in future_instructions):
                continue
            if (normalize(candidate.group()) == 'lo pague'
                    and not re.search(r'\bpagué\b', verbatim[candidate.start():candidate.end()], re.I)
                    and re.search(r'\bque\s+(?:usted\s+)?$', s[:candidate.start()])):
                continue  # «Recomiendo que lo pague» no acredita «lo pagué».
            if 'realice' in candidate.group() and not re.search(r"\brealicé\b", verbatim, re.I):
                prefix=s[max(0,candidate.start()-65):candidate.start()]
                if (re.search(r"\b(?:que|para que)\b[^.!?]{0,80}$",prefix)
                        or not re.search(r"\b(?:ya|hoy|ayer|pasado|pasada)\b",prefix+' '+candidate.group())):
                    continue
            if re.search(r"\b(?:no|aun no|todavia no)\s+(?:he |lo )?$", s[:candidate.start()]):
                continue
            if (re.match(r'ya se (?:hizo|realizo) ',candidate.group())
                    and re.search(r'\b(?:si|cuando|una vez que|en caso de que|dijo que|dice que|creo que|'
                                  r'no es (?:cierto|verdad) que|supongamos que|no se si)\s*$',s[:candidate.start()])):
                continue
            if candidate.group() in {'lo realice', 'lo hice'} and re.search(
                    r"\b(?:que|para que|cuando|si)\s*$", s[:candidate.start()]):
                continue
            if unit["speaker_role"] == "GESTOR" and "tengo registrado" not in normalize(candidate.group()):
                continue
            if re.search(r"\b(?:cuando|una vez que|si|para que)\b[^.!?]{0,35}$", s[:candidate.start()]):
                if 'esta hecho' in candidate.group() or 'esta realizado' in candidate.group():
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
    for state in re.finditer(r'\b(?:mi cuenta (?:ya )?esta (?:liquidada|en ceros?)|'
                             r'ya (?:esta en|esten) ceros? mi cuenta)\b',source):
        prefix=source[max(0,state.start()-65):state.start()]
        if (_role_at(text,segments,state.start())=='GESTOR' or re.search(
                r'\b(?:si|cuando|en caso de que|no se si|creo que|no es cierto que|diga que|dice que|dijo que)\s*$',prefix)):
            continue
        if source.rfind('¿',0,state.start())>source.rfind('?',0,state.start()):continue
        evidence.append({'text':state.group(),'speaker_role':_role_at(text,segments,state.start()),
                         'start':None,'end':None,'text_start':state.start(),'text_end':state.end(),
                         'method':'CUENTA_EN_CERO_REPORTADA_NO_VERIFICACION_BANCARIA'})
    return {"confirmed": bool(evidence), "evidence": evidence}


KIN = r"(?:espos[oa]|marido|mujer|pareja|herman[oa]|hij[oa]|mama|madre|papa|padre|sobrin[oa]|prim[oa]|ti[oa]|abuel[oa]|cunad[oa]|suegr[oa]|yerno|nuera|niet[oa]|padrastro|madrastra|hijastr[oa])"
FAMILY = re.compile(rf"\b(?:(?:soy|era) (?:su |un |una )?familiar|soy su {KIN}|(?:es|era) mi {KIN}|(?:es|era) (?:espos[oa]|pareja) de mi {KIN})\b")
ACCEPTANCE = re.compile(
    r"\b(?:lo anoto|dejelo anoto|dejeme anotarlo|lo puedo anotar|puedo anotarlo|puedo (?:hasta )?tomar nota|ya estoy anotando|yo se lo (?:envio|mando)|"
    r"yo le aviso|le (?:tomamos|tomo|recibimos|recibo) (?:el|su) recado|le (?:paso|doy|transmito) (?:el|su) recado|se lo comunico|"
    r"se lo hago saber|le hago llegar el mensaje|le paso el dato|"
    r"yo (?:le )?aviso(?: igual)?|le voy a (?:pasar|dar) el (?:recado|mensaje))\b")
DECLINES = re.compile(
    r"\b(?:no (?:quiero|puedo|voy a) (?:recibir|tomar|anotar)(?=\s*(?:[,.!?]|$)|\s+(?:el |un )?(?:recado|mensaje|numero))|"
    r"no (?:quiero|puedo|voy a) (?:pasar|dar|transmitir) (?:el |un |su )?(?:recado|mensaje)|"
    r"no le (?:voy a |puedo |quiero )?(?:pasar|dar|mandar) (?:el |un |su )?(?:recado|mensaje)|"
    r"no le (?:voy a |puedo |quiero )?avisar|"
    r"no se lo (?:voy a |puedo |quiero )?(?:pasar|dar|mandar)(?=\s*(?:[,.!?]|$))|"
    r"no tengo (?:con que|donde|como|forma de) (?:anotar|apuntar|contactar|avisar)|"
    r"no soy (?:su )?mensajer[oa]|no me interesa recibir el recado)\b")


def assess_recado(text, segments=()):
    from app.services.context_rules import unknown_debtor_statement
    families, acceptances, refusals, unknown = [], [], [], []
    for unit in sentence_evidence(text, segments):
        s = normalize(unit["text"])
        if unit["speaker_role"] in {"GESTOR", "TITULAR"}:
            continue
        if unknown_debtor_statement(unit["text"]):
            unknown.append(unit)
        if DECLINES.search(s):
            refusals.append(unit)
        for match in FAMILY.finditer(s):
            prefix = s[max(0, match.start()-55):match.start()]
            suffix = s[match.end():match.end()+25]
            # Una pregunta posterior («es mi marido, ¿por qué?») no borra
            # la afirmación. La afirmación dentro de una pregunta sí se excluye.
            left = max(s.rfind(c,0,match.start()) for c in '.!?¿')
            right = min((p for c in '.!?¿' if (p:=s.find(c,match.end()))>=0), default=len(s))
            if ((left>=0 and s[left]=='¿') or (right<len(s) and s[right]=='?')
                    or re.search(r"\b(?:no|no es|no era|no soy|(?:no se si|creo que|tal vez|quizas)(?: es| sea)?|usted es|usted seria|(?:diga|dice|dijo|dijera) que)\s*$", prefix)
                    or re.match(r"\s*[,;]?\s*¿?\s*(?:verdad|correcto|cierto)\b", suffix)):
                continue
            families.append(dict(unit, phrase=match.group()))
        if ACCEPTANCE.search(s) and not DECLINES.search(s):
            from app.services.message_contact_evidence import _outside_question
            # Una cita o una instrucción del gestor no confirma recepción.
            for accepted in ACCEPTANCE.finditer(s):
                if not _outside_question(s,accepted.start(),accepted.end()):continue
                prefix=s[max(0,accepted.start()-60):accepted.start()]
                if (not re.search(r"\b(?:diga|digale|dijera|dijera que|diga que|gracias por)\b.{0,25}$",prefix)
                        and not re.search(r"\bno\s*$",prefix)):
                    acceptances.append(unit)
                    break
    source = normalize(text)
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role'] in {'GESTOR','TITULAR'}:continue
        if re.fullmatch(r'(?:(?:ok|bien|si|claro)[, ]+)?yo le digo[.!]?',normalize(unit['text'])):
            # Una respuesta concreta al mensaje de retorno, no «yo le digo»
            # dentro de una cita, una discusión o una instrucción del gestor.
            at=source.find(normalize(unit['text']))
            nearby=source[max(0,at-350):at]
            if re.search(r'\b(?:que se comunique|se comunique (?:ese|al|a ese) numero|se pueda poner en contacto)\b',nearby):
                acceptances.append(dict(unit,method='CONFIRMA_AVISO_TRAS_RECONTACTO'))
    # «Hermana» es respuesta a una pregunta de parentesco, nunca una identidad
    # inferida del estatus o de una mención suelta del gestor.
    kin_reply = re.compile(
        r"\bque (?:parentesco|parentezco) (?:tiene|tienes) (?:usted )?(?:con (?:el|ella))?\?\s*"
        r"(?:no (?:la|lo) escuche[.!]\s*)?(?P<answer>"+KIN+r")[.! ,]")
    for match in kin_reply.finditer(source):
        if _role_at(text, segments, match.start('answer')) not in {'GESTOR', 'TITULAR'}:
            families.append({'text':match.group(), 'phrase':match['answer'],
                             'speaker_role':_role_at(text,segments,match.start('answer')),
                             'start':None,'end':None})
    contextual_kin = re.compile(
        r'\b(?:que (?:parentesco|parentezco)\b[^?!.]{0,100}|'
        r'que es (?:usted\b[^?!.]{0,80}|(?:de |del |de la )?(?:senor|senora|senorita|titular)\b[^?!.]{0,70})|'
        r'con quien (?:tengo|tuve) el gusto[^?!.]{0,50}|'
        r'usted(?: es)?[^?!.]{0,20}(?:familiar|conocid[oa]|amig[oa])[^?!.]{0,50})\?\s*'
        r'(?:si[, ]+)?(?P<answer>(?:(?:con |soy )?su |mi )?'+KIN+r')(?=[.!?, ]|$)')
    for match in contextual_kin.finditer(source):
        role=_role_at(text,segments,match.start('answer'))
        tail=source[match.end():match.end()+40]
        if role not in {'GESTOR','TITULAR'} and not re.match(r'\s*\?',tail):
            families.append({'text':match.group(),'phrase':match['answer'],
                             'speaker_role':role,'start':None,'end':None})
    confirm_kin=re.compile(r'\b(?:me comenta que |usted )?es su (?P<kin>'+KIN+r')\?\s*'
                           r'(?P<answer>si|asi es|correcto)\b')
    for match in confirm_kin.finditer(source):
        prefix=source[max(0,match.start()-45):match.start()]
        if (_role_at(text,segments,match.start('answer')) not in {'GESTOR','TITULAR'}
                and not re.search(r'\b(?:no|dice que|dijo que)\s*$',prefix)
                and not re.match(r'\s*\?',source[match.end():])
                and not re.search(r'\b(?:creo|tal vez|pero no)\b',source[match.end():match.end()+35])):
            families.append({'text':match.group(),'phrase':match['kin'],
                             'speaker_role':_role_at(text,segments,match.start('answer')),'start':None,'end':None})
    request = re.compile(
        r"\b(?:puedo|puede|puedes|podre|podra|podria|pudiera|podemos|podriamos) (?:dejar(?:le)?|dar(?:le)?) "
        r"(?:un |el |algun |algun tipo de )?(?:recado|mensaje|mensajito)[^?!.]{0,120}[?.]\s*"
        r"(?P<answer>si(?:[, ]+claro)?|(?:bien[, ]+)?claro|de acuerdo|ok(?:[, ]+si)?|esta bien|con gusto|a ver[, ]+digame)\b")
    for match in request.finditer(source):
        if (_role_at(text,segments,match.start('answer')) not in {'GESTOR','TITULAR'}
                and not re.search(r'\b(?:no|diga que|dice que|dijo que)(?: usted)?(?: le)?\s*$',source[max(0,match.start()-45):match.start()])
                and not re.match(r'\s*\?',source[match.end():])
                and not re.search(r"\b(?:pero no|no quiero|no puedo|no le voy)\b", source[match.end():match.end()+70])):
            acceptances.append({'text':match.group(), 'speaker_role':_role_at(text,segments,match.start('answer')),
                                'start':None,'end':None})
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role'] in {'GESTOR','TITULAR'}:continue
        s=normalize(unit['text'])
        offer=re.search(r'\b(?:(?:si |se )?gusta|quiere|desea) dejar(?:le)? (?:un |algun |el )?(?:recado|mensaje|mensajito)\b',s)
        if offer and not re.search(r'\b(?:no(?: me| le)?|dice que|dijo que|diga que)\s*$',s[:offer.start()]):
            acceptances.append(dict(unit,method='OFRECE_RECIBIR_MENSAJE'))
    note_request=re.compile(
        r'\b(?:tiene|tienes|tendra|tendria) (?:usted )?(?:(?:con que|donde) (?:anotar|apuntar)|donde tomar nota)'
        r'[^?!.]{0,65}\?\s*(?P<answer>si(?:[, ]+(?:a ver|claro))?|a ver[, ]+diga(?:me|nme))\b')
    for match in note_request.finditer(source):
        nearby=source[max(0,match.start()-300):match.end()+300]
        if (re.search(r'\b(?:recado|mensaje|se comunique|comunicarse)\b',nearby)
                and _role_at(text,segments,match.start('answer')) not in {'GESTOR','TITULAR'}
                and not re.match(r'\s*\?',source[match.end():])
                and not re.search(r'\b(?:pero no|no quiero|no puedo|no le voy)\b',source[match.end():match.end()+70])):
            acceptances.append({'text':match.group(),'speaker_role':_role_at(text,segments,match.start('answer')),
                                'start':None,'end':None})
    contact_offer=re.compile(
        r'\ble (?:voy a dejar|dejare|dejo|podria dejar) (?:un |el )?(?:numero|telefono)\b'
        r'(?P<purpose>[^.!?]{0,230})[.?]\s*'
        r'(?P<answer>a ver(?:[, ]+diga(?:me|nme))?|diga(?:me|nme)|si[, ]+digame)[.!]\s*'
        r'(?:(?:mire|bien|muy bien|ok)[, ]+)?'
        r'(?:el (?:numero|telefono) (?:es|seria) (?:el )?|es (?:el )?)'
        r'(?P<number>\d[\d\s,.-]{7,30}\d)')
    for match in contact_offer.finditer(source):
        prefix=source[max(0,match.start()-60):match.start()]
        if (len(re.sub(r'\D','',match['number']))==10
                and re.search(r'\b(?:se comunique|pueda comunicarse|se pueda comunicar|(?:nos|me) llame|llame al)\b',match['purpose'])
                and _role_at(text,segments,match.start('answer')) not in {'GESTOR','TITULAR'}
                and not re.search(r'\b(?:no|dice que|dijo que|diga que|repita que)\s*$',prefix)):
            acceptances.append({'text':match.group(),'method':'SOLICITA_DICTADO_TRAS_OFERTA_DE_CONTACTO',
                                'speaker_role':_role_at(text,segments,match.start('answer')),'start':None,'end':None})
    readback=re.compile(r'\bme (?:lo |puede )?rectifi(?:ca|car)\b[^?!.]{0,80}\?\s*'
                        r'(?P<number>\d+(?:[\s,.-]+\d+){2,8})')
    for match in readback.finditer(source):
        digits=re.sub(r'\D','',match['number'])
        nearby=source[max(0,match.start()-400):match.end()+150]
        if (len(digits)==10 and re.search(r'\b(?:recado|mensaje|se comunique|comunicarse|numero telefonico)\b',nearby)
                and _role_at(text,segments,match.start('number')) not in {'GESTOR','TITULAR'}):
            acceptances.append({'text':match.group(),'method':'REPETICION_NUMERO_CONTACTO_SOLICITADA',
                                'speaker_role':_role_at(text,segments,match.start('number')),'start':None,'end':None})
    information_offer=re.compile(
        r'\b(?:puedo|podre|podria|podemos) dejar(?:le)? (?:una |la |esta )informacion con usted'
        r'[^.!?]{0,30}[.!?]\s*(?P<answer>si(?:[, ]+claro)?|claro|de acuerdo)\b')
    from app.services.payment_reference_validation import callback_numbers
    for match in information_offer.finditer(source):
        role=_role_at(text,segments,match.start('answer'))
        prefix=source[max(0,match.start()-50):match.start()]
        tail=source[match.end():match.end()+900]
        if (role in {'GESTOR','TITULAR'}
                or re.search(r'\b(?:no|dice que|dijo que|diga que)(?: le)?\s*$',prefix)
                or not re.match(r'\s*[.!]',tail)
                or re.search(r'\b(?:pero no|no quiero|no puedo|no le voy)\b',tail[:70])):
            continue
        phones=callback_numbers(tail)
        phones=[p for p in phones if _role_at(text,segments,match.end()+p['text_start'])
                not in {'TITULAR','TERCERO','INTERLOCUTOR'}]
        if phones:
            acceptances.append({'text':match.group(),'method':'ACEPTA_INFORMACION_Y_RECIBE_CONTACTO',
                'speaker_role':role,'start':None,'end':None,'callback_evidence':phones[0]})
    delayed_offer=re.compile(r'\b(?:puedo|podria|podre) dejar(?:le|lo)? (?:un |el )numero (?:de )?telefonico'
                             r'[^?!]{0,170}\?')
    for offer in delayed_offer.finditer(source):
        tail=source[offer.end():offer.end()+260]
        answer=re.search(r'\ba ver[, ]+(?:digame|diselo|digalo)[.!]',tail)
        if not answer or re.search(r'\b(?:no|dice que|dijo que)(?: le)?\s*$',source[max(0,offer.start()-50):offer.start()]):continue
        role=_role_at(text,segments,offer.end()+answer.start())
        if role in {'GESTOR','TITULAR'}:continue
        for phone in callback_numbers(source[offer.start():offer.end()+260]):
            number_position=offer.start()+phone['text_start']
            if (number_position>offer.end()+answer.end()
                    and _role_at(text,segments,number_position) not in {'TITULAR','TERCERO','INTERLOCUTOR'}):
                acceptances.append({'text':offer.group()+' '+answer.group(),
                    'method':'SOLICITA_DICTADO_TRAS_ESPERA_CON_CONTACTO_COMPLETO','speaker_role':role,
                    'start':None,'end':None,'callback_evidence':phone})
                break
    from app.services.message_contact_evidence import message_contact_evidence, directed_relay_message
    extended = message_contact_evidence(text, segments)
    from app.services.message_dialogue_evidence import dialogue_message_evidence
    dialogue = dialogue_message_evidence(text,segments)
    from app.services.message_dialogue_evidence import ready_after_note_wait
    dialogue['acceptance'].extend(ready_after_note_wait(text,segments))
    from app.services.message_dialogue_evidence import information_relay_acceptance
    dialogue['acceptance'].extend(information_relay_acceptance(text,segments))
    from app.services.message_dialogue_evidence import existing_callback_confirmation
    dialogue['acceptance'].extend(existing_callback_confirmation(text,segments))
    from app.services.message_dialogue_evidence import asks_to_hear_callback
    dialogue['acceptance'].extend(asks_to_hear_callback(text,segments))
    from app.services.contact_dialogue_resolution import contact_dialogue_evidence
    resolved=contact_dialogue_evidence(text,segments)
    for key in ['family','acceptance','work_relationships','third_party_relationships']:
        extended[key].extend(dialogue[key]);extended[key].extend(resolved[key])
    from app.services.recado_receipt_resolution import callback_acknowledgements
    extended['acceptance'].extend(callback_acknowledgements(text,segments))
    from app.services.status_message_evidence import extra_message_receipt
    extended['acceptance'].extend(extra_message_receipt(text,segments))
    families.extend(extended['family'])
    acceptances.extend(extended['acceptance'])
    from app.services.message_contact_evidence import callback_permission_evidence
    acceptances.extend(callback_permission_evidence(text, segments))
    return {"family": families, "acceptance": acceptances,
            "refusal": refusals, "unknown_recipient": unknown,
            'directed_messages': directed_relay_message(text, segments),
            'third_party_relationships': extended['third_party_relationships'],
            'work_relationships': extended['work_relationships']}


def directed_callback_message(text, segments=()):
    """Contenido del mensaje de retorno; no acredita recepción ni dígitos."""
    found = []
    source, cursor = normalize(text), 0
    for unit in sentence_evidence(text, segments):
        s = normalize(unit['text'])
        position = source.find(s, cursor)
        if position < 0:
            continue
        cursor = position + len(s)
        if unit['speaker_role'] in {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}:
            continue
        if any(c in s for c in '?¿"«»“”'):
            continue
        match = re.search(r'\ba (?:ese|este) numero[, ]+que se comunique con nosotros\b', s)
        if not match:
            continue
        # No convertir una negación, cita o ejemplo condicional en un mensaje
        # realmente proporcionado. La aceptación se valida por separado.
        prefix = s[:match.start()]
        if re.search(r'\b(?:no|dice|dicen|dijo|dijeron|diga|digale|repita|supongamos|si|cuando)\b', prefix):
            continue
        if re.search(r'\b(?:pero no|es un ejemplo|hipoteticamente)\b', s[match.end():]):
            continue
        # Debe existir dictado cercano, no solo «a ese número». Contar los
        # fragmentos no reconstruye un teléfono ni certifica sus dígitos: ASR
        # puede repetir grupos. Tampoco se toma el dictado conocido del tercero.
        begin = max(0, position-220)
        nearby = source[begin:position+match.start()]
        digits = sum(len(number.group()) for number in re.finditer(r'\b\d{1,10}\b', nearby)
                     if _role_at(text, segments, begin+number.start()) not in
                     {'TITULAR', 'TERCERO', 'INTERLOCUTOR'})
        if digits < 10:
            continue
        found.append(dict(unit, method='INSTRUCCION_DE_RETORNO_AL_CONTACTO_DADO'))
    return found


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
    units=sentence_evidence(text, segments)
    payment_context=False
    # Solo separadores tipográficos de marcas YA autorizadas; no coincidencia
    # difusa ni bancos sin convenio. La evidencia conserva la frase encontrada.
    def brand_pattern(variant):
        words = re.split(r"[ /-]+", normalize(variant))
        return r"[ /-]+".join(re.sub(r"(?<=\d)(?=[a-z])", r"[ -]*", re.escape(w)) for w in words)

    patterns = [(place, re.compile(r"(?<!\w)" + brand_pattern(v) + r"(?!\w)"))
                for place, variants in catalog.items() for v in variants]
    catalog_start = re.compile(r"^(?:" + "|".join(brand_pattern(v)
        for variants in catalog.values() for v in variants) + r")(?!\w)")
    positive_offer = re.compile(r"\b(?:puede pagar|puede aplicar pago|lo puede (?:hacer|realizar)|"
                                r"puede realizar(?:lo|le)|pueden ir|pagar en|o en)\b")
    for index, unit in enumerate(units):
        s = normalize(unit["text"])
        new_context=bool(re.search(
            r"\b(?:donde|lugares|establecimientos|tiendas?)\b.*\b(?:pagar|pagos?|cubrir|depositar|abonar)\b|"
            r"\b(?:pagar|pagos?|cubrir|depositar|abonar)\b.*\b(?:donde|lugares|establecimientos|tiendas?)\b",s))
        if unit["speaker_role"] in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            payment_context=new_context and ('?' in s or '¿' in s)
            continue
        matches = [(m.start(), m.end(), place, m.group())
                   for place, pattern in patterns for m in pattern.finditer(s)]
        # Compras, retiros y consultas en una tienda no son ofertas de pago.
        other_action = bool(re.search(
            r"\b(?:compras?|comprar|retirar (?:dinero|efectivo)|retiro de (?:dinero|efectivo)|aclaracion|consulta)\b", s))
        instruction=re.search(r"\b(?:puede pagar(?:lo|los)?|puede aplicar pago|podra pagar(?:lo|los)?|puede realizar|realizar (?:su |el )?pago|"
                         r"(?:puede|puedes|puedo) (?:usted )?(?:aplicar|hacer|realizar) (?:lo que es |lo que eso )?(?:su |el |un |los )?pagos?|"
                         r"pago ya sea que se aplique|(?:realiza|realice|realizando|aplique|aplica|aplicando|efectuar|hacer) (?:su |el |un )?pago|"
                         r"pagos? (?:ya )?(?:se )?(?:lo )?(?:realizan|realiza|aplican|aplica|aplique|hacen|efectuan)\b|"
                         r"(?:el )?pago (?:lo )?(?:estaria|puede|podria) (?:aplicando|realizando|generar|efectuar|aplicar|hacer)|"
                         r"pagos? los? puede (?:estar )?(?:realizando|aplicando|hacer|realizar)|pueden aplicar(?: el pago)?|"
                         r"pague|pagar(?:lo|los)? en|pago en|pago de servicios?|deposite|depositar en|"
                         r"lugares de pago|opciones de pago|convenio (?:numero )?\d)\b", s)
        # Pronombres/conjugaciones ASR del ofrecimiento, con destino de pago
        # explícito o marcas autorizadas; nunca se cuentan acciones ajenas.
        implicit = re.search(r"\b(?:lo puede (?:hacer|aplicar|realizar)|puede (?:hacerlo|aplicarlo|realizarlo|realizarle)|"
                             r"los puede estar realizando|(?:tenia|tiene) que realizarlo)\b", s)
        destination = bool(matches or re.search(r"\b(?:tiendas? de conveniencia|establecimientos)\b", s)
                           or (payment_context and re.search(r"\ben (?:una|un|tiendas?)\b", s)))
        # «Puede ser en ...» sigue una pregunta/instrucción de pago cercana.
        # Dos frases es el límite: no heredar el tema del inicio de la llamada.
        recent_payment = any(re.search(r"\b(?:pago|pagar|deposito|transferencia)\b", normalize(u['text']))
                             for u in units[max(0, index-2):index+1])
        contextual_offer = re.search(r"\b(?:puede ser en|hay otros lugares)\b", s)
        if contextual_offer and recent_payment and len({m[2] for m in matches}) >= 2 and not other_action:
            implicit = implicit or contextual_offer
        asr_payment = re.search(r"\blo puede ser el pago\b", s)
        if not instruction and not other_action:
            instruction = asr_payment or (implicit if destination else None)
        # Mantener solo enumeraciones consecutivas de esa oferta. Un cambio
        # de tema o un turno del cliente cierra la lista; no toda la llamada.
        enumeration = re.match(r"^(?:normalmente )?(?:las?|los?) "
            r"(?:tiendas? de conveniencia|establecimientos autorizados|sitios de conveniencia)\b", s)
        numeric_list = bool(re.match(r"^\d", s) and len({m[2] for m in matches}) >= 2)
        continuation=bool(payment_context and (enumeration or numeric_list or re.match(
            r"^[¿?]?(?:en |a la |a |o |tambien |farmacias |tiendas |kiosco\b|7[- ])",s) or catalog_start.match(s))
            and not re.search(r"\b(?:tarjeta|producto|origen|compre|comprobante|telefono|numero)\b",s)
            and not other_action)
        negated_instruction = bool(instruction and re.search(
            r"\bno (?:se |lo )?$", s[max(0, instruction.start()-12):instruction.start()]))
        alternative = bool(negated_instruction and any(m.start() > instruction.start()
            and not re.search(r"\bno (?:se |lo )?$", s[max(0, m.start()-12):m.start()])
            for m in positive_offer.finditer(s)))
        payment_context=bool(not other_action and (not negated_instruction or alternative) and (new_context or instruction or continuation
            or (payment_context and re.fullmatch(r"(?:si[, ]+)?(?:directamente en )?tienda[.!?]*", s))))
        if (not instruction and not continuation) or other_action:
            continue
        if negated_instruction and not alternative:
            continue
        selected = []
        for start, end, place, phrase in sorted(matches, key=lambda x: -(x[1]-x[0])):
            if any(start < b and end > a for a, b in selected):
                continue
            selected.append((start, end))
            before = s[max(0, start-100):start]
            if instruction and start < instruction.start() and re.search(r"\b(?:su|la) (?:tarjeta|producto) (?:es|de|va en relacion)\b|\b(?:tienda de origen|producto de)\b|\b(?:tarjeta|producto)(?: (?:tipo|visa|de|es|la|tienda|departamental)){0,5}\s*$",s[:start]):
                continue
            # Negación de ESA opción; «no en Guadalajara, puede pagar en
            # Kiosko» no niega la segunda cláusula afirmativa.
            negative=re.search(r"\bno\b.{0,80}\b(?:pagar|pague|en)\b",before)
            positive=list(positive_offer.finditer(before))
            if negative and not (positive and positive[-1].start()>negative.start()
                    and not re.search(r"\bno (?:se )?$",before[max(0,positive[-1].start()-12):positive[-1].start()])):
                continue
            found[place] = dict(unit, phrase=phrase, place=place)
    return list(found.values())


SENSITIVE = re.compile(
    r"\b(?:saldo (?:pendiente|vencido|total|de\s+\d[\d.,]*|es\s+\d[\d.,]*)|"
    r"(?:registra|presenta) (?:una )?falta de pago|por un atraso que presenta|por (?:el )?atraso (?:de|en|que presenta) (?:su|la) tarjeta|"
    r"(?:tiene|presenta|cuenta con) (?:un |una |dos |tres |cuatro |\d+ )?(?:deuda|adeudo|atraso|mens(?:u)?alidad(?:es)?)|"
    r"(?:\d+|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|dieciseis|diecisiete|dieciocho|diecinueve|veinte) (?:mes(?:es)?|anos?|mens(?:u)?alidad(?:es)?)(?: de)? (?:atraso|vencid[ao]s?)|"
    r"mens(?:u)?alidades vencidas|(?:meses|anos) de atraso|"
    r"(?:\d+|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|veinte) (?:meses?|anos?) (?:que no (?:se )?(?:ha )?(?:efectuado|realizado|aplicado|presentado|registrado|recibido|presenta|efectua|realiza|registra|recibe)|sin (?:realizar|efectuar|registrar)) (?:un |el |su |ningun )?(?:pago|abono)|"
    r"(?:deuda|adeudo|pago minimo|monto) (?:de |es |por )?\d[\d.,]*|"
    r"(?:adeuda|debe)\s+(?:\d[\d.,]*|mil|cien|doscientos|trescientos|quinientos)|"
    r"(?:su|una|la) deuda|(?:su|un|el) adeudo|cubrir (?:el |su )?atraso|respecto a su atraso|por (?:el |su )?atraso|"
    r"negativa de pago|recuperacion (?:del|de su|en el) saldo|"
    r"deudo con su tarjeta|la deudo que presenta|el adebro|mes(?:es)? de atras o|(?:tiene|presenta) solidades vencidas|"
    r"(?:tiene|presenta) (?:lo que es )?(?:una|su|la) cuenta extrajudicial|"
    r"(?:su |la )?cuenta(?: se encuentra| esta)? en extrajudicial|se encuentra en extrajudicial (?:su |la )?tarjeta|"
    r"(?:su|la|esa) cuenta[^.!?]{0,65}\b(?:se encuentra|esta|asignada|canalizada) (?:en |a |al )?(?:el |la )?area de cobranza|"
    r"detener (?:la|su) demanda (?:de tipo )?mercantil|por la trazo de su tarjeta|"
    r"demanda (?:de|por) (?:pago|incumplimiento)|pagos? vencidos?|incumplimiento (?:al|del|de) (?:contrato|pago)|"
    r"(?:sobre|respecto a) (?:el|su) atraso (?:que presenta|de su (?:tarjeta|cuenta))|"
    r"(?:cuenta|tarjeta)(?:[^.!?]{0,45}?) (?:se (?:canalizo|turno|envio)|fue (?:canalizada|turnada|enviada)) (?:al |a (?:el |un )?)?(?:area de |departamento )?juridico|"
    r"(?:tiene|maneja|cuenta con) (?:una |la |su )?tarjeta)\b")
CARD = re.compile(r"\b(?:tarjeta|referencia|plastico|numero de cuenta)\s*(?:(?:numero|de pago|es|de)\s*)?(?:\d[ -]?){15}\d\b")


def financial_answer_evidence(text,segments=()):
    """Importe respondido a una pregunta de saldo, conservando contexto y rol."""
    from app.services.reported_payment_amounts import NUMBER
    units=sentence_evidence(text,segments);found=[];source=normalize(text);recipient_role=None
    for index,question in enumerate(units):
        if question['speaker_role'] in {'TITULAR','TERCERO','INTERLOCUTOR'}:
            recipient_role=question['speaker_role']
        q=normalize(question['text'])
        if '?' not in q or not re.search(r'\b(?:de )?cuanto\b',q):continue
        if re.search(r'\b(?:telefono|folio|referencia|digitos|terminacion|fecha|dias|horas|pago)\b',q):continue
        explicit=bool(re.search(r'\b(?:saldo|deuda|adeudo|monto|total)\b',q))
        position=source.find(q)
        prior=source[max(0,position-650):position]
        asr_context=bool(re.search(r'\b(?:tal|lo que presenta)\b',q) and re.search(r'\bsaldo (?:pendiente|vencido)\b',prior))
        if not (explicit or asr_context):continue
        for answer in units[index+1:index+3]:
            a=normalize(answer['text'])
            if re.fullmatch(r'(?:disculpe|perdon)[.!]?',a):continue
            match=re.fullmatch(r'(?:(?:como le menciono|son|es|por|la cantidad es|la cantidad de)[, ]+){0,3}'
                               rf'\$?\s*(?P<amount>{NUMBER})(?:\s*pesos?)?[.!]?',a)
            if match and match['amount'] not in {'un','una','uno'}:
                found.append(dict(answer,question_text=question['text'],phrase=match['amount'],
                                  recipient_role=recipient_role,method='IMPORTE_RESPONDIDO_A_PREGUNTA_DE_SALDO'))
            break
    return found


def assess_home_recovery_warning(text,segments=(),mora=''):
    applies=mora in {'1PV','2PV'};evidence=[]
    if applies:
        for unit in sentence_evidence(text,segments):
            s=normalize(unit['text'])
            match=re.search(r'\b(?:se estara|estaremos|se va a estar|vamos a estar) trabajando sobre '
                            r'(?:la )?recuperacion total en (?:el |su )?domicil(?:io)?\b',s)
            match = match or re.search(
                r'\b(?:visita (?:ocular )?[^.!?]{0,120}recuperacion|recuperacion sobre la visita)\b',s)
            if not match:continue
            prefix=s[:match.start()]
            if (re.search(r'\b(?:no|nunca)\s*$',prefix)
                    or re.search(r'\b(?:dice que|dijo que|me dijeron que)\b[^.!?]{0,90}$',prefix)
                    or '?' in s or '¿' in s):continue
            if unit['speaker_role'] in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
            evidence.append(dict(unit,phrase=match.group(),confirmed=unit['speaker_role']=='GESTOR'))
    confirmed=any(e['confirmed'] for e in evidence)
    return {'applies':applies,'confirmed':confirmed,'review_required':bool(evidence) and not confirmed,'evidence':evidence}


def reported_card_clarification(text,segments=()):
    """Pérdida/robo reportado, folio confirmado y seguimiento de resolución."""
    source=normalize(text)
    loss=False
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role']=='GESTOR' or '?' in unit['text'] or '¿' in unit['text']:continue
        s=normalize(unit['text'])
        for m in re.finditer(r'\b(?:yo )?(?:perdi (?:la|mi) tarjeta|me robaron (?:la|mi) tarjeta)\b',s):
            if not re.search(r'\b(?:no|no se si|no es verdad que|supongamos que|dice que|dijo que|si hubiera)\s*$',s[:m.start()]):loss=True
    folio=False
    for m in re.finditer(r'\b(?:le (?:otorgaron|atorgaron|dieron)|tiene|cuenta con)[^?!]{0,30}\bfolio\b[^?!]{0,15}\?\s*(?P<answer>si|asi es)\b',source):
        if (_role_at(text,segments,m.start('answer'))!='GESTOR'
                and not re.search(r'\b(?:no|dice que|dijo que)\s*$',source[max(0,m.start()-35):m.start()])
                and not re.match(r'\s*(?:\?|[, ]+pero no)',source[m.end():])):folio=True
    followup=bool(re.search(r'\b(?:resolucion|dictamen?|proceso tardaba|proceso tarda)\b',source)
                  and re.search(r'\b(?:comuniquese|marcar[ae]?|seguimiento|verificar|me dijeron)\b',source))
    cancellation = False
    for unit in sentence_evidence(text, segments):
        value = normalize(unit['text'])
        if unit['speaker_role'] == 'GESTOR' or '?' in value or '¿' in value:
            continue
        match = re.search(r'\b(?:(?:esta|esa|mi|la) tarjeta (?:ya )?la tengo cancelada|'
                          r'(?:mi tarjeta|mi cuenta) (?:ya )?esta cancelada|ya cancele (?:mi |la )?tarjeta)\b', value)
        if match and not re.search(r'\b(?:no|dice que|dijo que|si|supongamos que)\s*$',value[:match.start()]):
            cancellation = True
    cancel_folio = re.search(r'\b(?:tendra|tendras|tiene|cuenta con) (?:usted )?(?:(?:un|el) )?'
                            r'numero de folio de cancelacion[?., ]*'
                            r'(?P<answer>claro|si|lo tengo|por supuesto)\b',source)
    cancellation_confirmed = False
    if cancel_folio and _role_at(text,segments,cancel_folio.start('answer')) not in {'GESTOR'}:
        tail=source[cancel_folio.end():cancel_folio.end()+280]
        folio_digits=re.search(r'\d[\d, .-]{3,}',tail)
        is_phone = bool(folio_digits and re.search(r'\b(?:telefono|whatsapp|numero de contacto)\b',tail[:folio_digits.start()]))
        cancelled_followup=bool(re.search(r'\b(?:ponerlo|poniendo|registrando) (?:aqui |lo )?en (?:el )?sistema\b',source)
            and re.search(r'\b(?:no le generen mas llamadas|evitar.*llamadas|no.*llamadas)\b',source))
        cancellation_confirmed=bool(cancellation and folio_digits and not is_phone and cancelled_followup
            and len(re.sub(r'\D','',folio_digits.group())) >= 4
            and not re.search(r'\bno (?:tengo|cuento con).*folio\b',tail))
    explicit_cancel=recipient_statement(text,segments,r'\b(?:esa|esta|mi|la) tarjeta (?:ya esta|ya no se usa)|\bya tengo el (?:codigo|folio)\b[^.!?]{0,80}\bcancelada\b')
    folio_reference=re.search(r'\b(?:folio|codigo)\b[^.!?]{0,130}\b(?:[a-z]{2,6}[- ]*)?\d{4,10}\b',source)
    recorded=agent_statement(text,segments,r'\b(?:lo metemos|lo manejamos|manejamos|se registra|registramos|paso el reporte)\b[^.!?]{0,65}\baclaracion\b')
    cancelled_followup=bool(explicit_cancel and folio_reference and recorded and re.search(r'\bcancelad[ao]\b',source))
    cancellation_confirmed=bool(cancellation_confirmed or cancelled_followup)
    return {'confirmed':bool(loss and folio and followup) or cancellation_confirmed,
            'reported_cancellation':cancellation, 'cancellation_followup':cancellation_confirmed,
            'reported_loss':bool(loss),
            'case_number_acknowledged':folio,'resolution_followup':followup,
            'method':('CANCELACION_REPORTADA_FOLIO_Y_REGISTRO_EN_SISTEMA' if cancellation_confirmed else 'PERDIDA_REPORTADA_FOLIO_CONFIRMADO_Y_SEGUIMIENTO')}


def sensitive_financial_matches(text):
    """«Saldo pendiente» sin importe está permitido por aclaración del usuario.

    Se mantiene protección para importes, mora, deuda explícita y tarjeta completa.
    La mención genérica no convierte teléfonos o terminaciones en montos.
    """
    # Importación local: este módulo también proporciona normalize al extractor.
    from app.services.reported_payment_amounts import NUMBER
    source = normalize(text)
    matches = []
    for match in SENSITIVE.finditer(source):
        if match.group() in {'saldo pendiente','saldo vencido'}:
            tail = source[match.end():match.end()+200]
            immediate = re.match(
                rf'[\s,.:]*(?:(?:es|de|por|son|asciende a|la cantidad de|un total de|con un monto de)\s+){{0,4}}'
                rf'(?P<currency>\$?)\s*(?P<amount>{NUMBER})(?!\w)', tail)
            if (immediate and immediate['amount'] in {'un', 'uno', 'una'}
                    and not immediate['currency']
                    and not re.match(r'\s*pesos?\b', tail[immediate.end():])):
                immediate = None  # «de una tarjeta» no comunica un importe de un peso.
            explicit_money = re.match(
                rf'[^.!?]{{0,120}}?\b(?:por|de|es|son|monto|cantidad)\s+'
                rf'\$?\s*(?:{NUMBER})\s+pesos?\b', tail)
            if not immediate and not explicit_money:
                continue
        matches.append(match)
    # Importes anunciados como términos actuales, no un pago histórico que
    # el familiar informa. Conservar palabras de enlace como «por la cantidad».
    amount_phrases=[
        rf'\b(?:saldo (?:tal|total)|pago minimo)\b[^.!?]{{0,45}}?\b(?:cantidad|monto) (?:de |por )?\$?\s*{NUMBER}\b',
        rf'\bpara (?:liquidar|regularizar|ponerse al corriente)\b[, ]*(?:es|seria|sera) (?:por |de )?(?:(?:la )?(?:cantidad|monto) (?:de |por )?)?\$?\s*{NUMBER}\b',
        rf'\bpago que se (?:esta )?requiriendo\b[^.!?]{{0,70}}?\b(?:cantidad|monto) (?:de |por )?\$?\s*{NUMBER}\b',
        rf'\bno (?:se )?(?:ha |han )?(?:realizado|efectuado|registrado|hecho|generado) (?:ningun |un |el |su )?pago (?:en|desde hace) (?:{NUMBER}) (?:meses?|anos?)\b',
    ]
    for pattern in amount_phrases:matches.extend(re.finditer(pattern,source))
    # «Se le está dictaminando su negativa» declara un estado financiero
    # aun cuando ASR omite «de pago». Exigir el contexto de cobro y excluir
    # una negativa a recibir un recado o proporcionar datos.
    for match in re.finditer(r"\bse (?:le )?esta (?:dictaminando|ditaminando|registrando) (?:a |como )?(?:su |la |una )?negativa\b", source):
        before=source[max(0,match.start()-160):match.start()]
        after=source[match.end():match.end()+140]
        if re.search(r"\b(?:no|nunca)\s*$", before):continue
        if re.match(r"\s+a (?:recibir|aceptar|tomar|dar|proporcionar)\b",after):continue
        if re.search(r"\b(?:pago|pagar|cobro|deuda|adeudo|tarjeta)\b",before+' '+after):matches.append(match)
    return matches + list(CARD.finditer(source))


def assess_privacy(text, segments=(), *, third_party_confirmed=False,
                   expected_third_party=False, titular=False, legacy_financial=False):
    evidence = []
    allowed_mentions = []
    last_recipient = None
    privacy_units = sentence_evidence(text, segments)
    for unit_index, unit in enumerate(privacy_units):
        role = unit["speaker_role"]
        if role in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            last_recipient = role
        s = normalize(unit["text"])
        matches = sensitive_financial_matches(s)
        # Un punto o un corte ASR no debe ocultar «Saldo pendiente. Son $500».
        # El rol decisivo es el de quien proporciona el importe, nunca el de
        # un familiar que informa su propio pago en el turno siguiente.
        if (not matches and re.search(r'\bsaldo (?:pendiente|vencido)\s*[.,:]?$', s)
                and unit_index+1 < len(privacy_units)):
            following = privacy_units[unit_index+1]
            combined = s+' '+normalize(following['text'])
            joined_matches = [m for m in sensitive_financial_matches(combined)
                              if m.group() in {'saldo pendiente','saldo vencido'} and m.start() < len(s)]
            if joined_matches and following['speaker_role'] not in {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}:
                role = following['speaker_role']
                unit = dict(unit, text=unit['text']+' '+following['text'], speaker_role=role, end=following['end'])
                s = combined
                matches = joined_matches
        sensitive_spans = {(m.start(), m.end()) for m in matches}
        if any(m.group() in {'saldo pendiente','saldo vencido'} and (m.start(), m.end()) not in sensitive_spans
               for m in SENSITIVE.finditer(s)):
            allowed_mentions.append(dict(unit, policy=('SALDO_VENCIDO_SIN_IMPORTE_PERMITIDO' if 'saldo vencido' in s else 'SALDO_PENDIENTE_SIN_IMPORTE_PERMITIDO')))
        for match in matches:
            prefix = s[max(0, match.start()-30):match.start()]
            hypothetical = bool("?" in s or "¿" in s or re.search(r"\b(?:si|no|nunca)\s*$", prefix)
                                or re.search(r"\b(?:no tiene|sin (?:deuda|adeudo|atraso)|si tuviera|en caso de)\b", s))
            protected = third_party_confirmed and last_recipient != "TITULAR"
            asr_uncertainty=bool(re.fullmatch(r"por la trazo de su tarjeta|deudo con su tarjeta|la deudo que presenta|el adebro|mes(?:es)? de atras o|(?:tiene|presenta) solidades vencidas",match.group()))
            scoped_role=None
            if role=="NO DETERMINADO" and protected and not hypothetical and not asr_uncertainty:
                from app.services.scoped_institutional_speech import institutional_clause_evidence
                scoped_role=institutional_clause_evidence(unit['text'],match.group())
            effective_role="GESTOR" if scoped_role else role
            confirmed = effective_role == "GESTOR" and protected and not hypothetical and not asr_uncertainty
            uncertain = (effective_role == "NO DETERMINADO" or hypothetical or asr_uncertainty
                         or (role == "GESTOR" and not titular and last_recipient != "TITULAR" and not protected))
            relevant = third_party_confirmed or expected_third_party or not titular
            evidence.append(dict(unit, phrase=match.group(), confirmed=confirmed, role_evidence=scoped_role,
                                 review_required=bool(relevant and uncertain)))
    # Conserva los bloqueos previos que aún no tienen un extractor específico.
    if legacy_financial and not evidence and (third_party_confirmed or (expected_third_party and not titular) or not titular):
        evidence.append({"text": "Señal financiera contextual sin atribución de voz confirmada.",
                         "speaker_role": "NO DETERMINADO", "start": None, "end": None,
                         "phrase": "", "confirmed": False, "review_required": True})
    for answer in financial_answer_evidence(text,segments):
        role=answer['speaker_role']
        if role in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        protected=third_party_confirmed and answer.get('recipient_role')!='TITULAR'
        disclosed=role=='GESTOR' and protected
        relevant=third_party_confirmed or expected_third_party or not titular
        uncertain=role=='NO DETERMINADO' or (role=='GESTOR' and not titular and not protected
                                            and answer.get('recipient_role')!='TITULAR')
        evidence.append(dict(answer,confirmed=bool(disclosed),
                             review_required=bool(relevant and uncertain)))
    confirmed = any(e["confirmed"] for e in evidence)
    review = any(e["review_required"] for e in evidence) and not confirmed
    return {"confirmed_disclosure": confirmed, "review_required": review,
            "third_party_confirmed": bool(third_party_confirmed), "evidence": evidence,
            "allowed_generic_balance_mentions": allowed_mentions,
            "reason": ("Divulgación atribuida al gestor ante un tercero confirmado." if confirmed else
                       "Posible divulgación financiera; confirmar hablante y destinatario en audio." if review else
                       "Sin divulgación a terceros confirmada.")}


def dictated_privacy_email(text,segments=()):
    """Correo dictado: exige privacidad, arroba y dominio literal autorizado.

    No reconstruye letras dudosas ni sustituye un dominio parecido. Conserva
    la evidencia de dictado sin afirmar validación de voz o entrega de correo.
    """
    source=normalize(text)
    for start in re.finditer(r'\b(?:es privacidad|correo (?:es|seria) privacidad|le (?:voy a )?dictar (?:el |un )?correo)\b',source):
        if _role_at(text,segments,start.start()) in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        if re.search(r'\bno\s*$',source[max(0,start.start()-8):start.start()]):continue
        block=source[start.start():start.start()+900]
        match=re.search(r'\bprivacidad(?P<one>1)?\b(?P<bridge>.{0,400}?)\barroba\b'
                        r'(?P<domain>.{0,350}?(?<![\w.@-])bradesco\.com\.mx(?![\w-]|\.[\w.-]))',block)
        if not match:continue
        if re.search(r'\bnumero (?:dos|tres|cuatro|cinco|seis|siete|ocho|nueve|\d{2,}|[2-9])\b',match['bridge']):continue
        if re.search(r'\bno (?:es|era|diga)\b',match['domain']):continue
        one=match['one'] or re.search(r'\b(?:numero )?(?:1|uno)\b',match['bridge'])
        return {'detected':True,'address':'privacidad'+('1' if one else '')+'@bradesco.com.mx',
                'method':'DICTADO_CON_DOMINIO_LITERAL','evidence':match.group()}
    from app.services.arco_context_evidence import spoken_privacy_email
    return spoken_privacy_email(text,segments)
