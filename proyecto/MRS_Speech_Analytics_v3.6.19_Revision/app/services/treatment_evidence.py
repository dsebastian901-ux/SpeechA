"""Quejas y expresiones despectivas: evidencia textual sin inventar tono."""
import re

from app.services.conversation_evidence import normalize, sentence_evidence


def mistreatment_reports(text, segments, phrases):
    evidence = []
    variants = re.compile(
        r'\bme contest(?:o|aron|aban|aba) (?:muy )?mal\b|'
        r'\b(?:una? |su companer[oa] |tu companer[oa] )?me amenazo\b|'
        r'\b(?:me|nos) (?:atendieron|atendio|atienden|atendian|trataron|trato|tratan|trataban|hablaron|hablo|hablan) '
        r'(?:(?:muy|bien|bastante|demasiado|sumamente|super) )?(?:mal|pesimo|pesimamente|groseramente|groser[oa]s?|agresiv[oa]s?|'
        r'de mala (?:manera|forma)|de (?:forma|manera) (?:grosera|agresiva)|con malos (?:modos|tratos))\b|'
        r'\b(?:me|nos) (?:estuvo|estaban|estuvieron|estaba) (?:gritando|insultando|agrediendo|amenazando|ofendiendo)\b|'
        r'\b(?:me|nos) (?:grito|insulto|agredio|ofendio|humillo|humillaron|amenazaron)\b|'
        r'\b(?:se burlo|se burlaron) de mi\b')
    prior_call = re.compile(r'\b(?:llamadas? (?:anterior(?:es)?|pasadas?)|vez pasada|ultima (?:vez|llamada)|'
                            r'(?:me (?:marco|llamo|hablo)|me (?:marcaron|llamaron|hablaron)) (?:antes|ayer)|'
                            r'(?:asesor|asesora|gestor|gestora|companero|companera) (?:anterior|de ayer))\b')
    service_actor = re.compile(r'\b(?:su (?:companero|companera|asesor|asesora|gestor|gestora)|'
                               r'(?:la persona|el asesor|la asesora|el gestor|la gestora) que me (?:llamo|marco|atendio|hablo))\b')
    bad_service = re.compile(r'\b(?:mala atencion|mal servicio|mal trato|agresion(?:es)?|'
                             r'falta de comunicacion|no hay (?:una )?buena comunicacion|'
                             r'(?:atencion|actitud|trato) (?:muy )?(?:mal[oa]|pesim[oa]|agresiv[oa]|groser[oa]|prepotente)|'
                             r'(?:fue|era|estuvo|se porto|fueron|eran|estuvieron|se portaron) (?:muy )?(?:agresiv[oa]s?|groser[oa]s?|'
                             r'prepotentes?|despotas?|altaner[oa]s?)|me falto al respeto|'
                             r'(?:la|lo|le) (?:atendieron|atendio|trataron|trato|hablaron|hablo) (?:muy )?'
                             r'(?:mal|pesimo|de mala manera))\b')
    accusatory_question = re.compile(
        r'\b(?:usted|tu) (?:fue|fuiste|es|eres) (?:la|el) (?:que|quien) me '
        r'(?:insulto|agredio|ofendio|amenazo|grito)\b')
    paid_source=normalize(text)
    paid_report=bool(re.search(r'\bya (?:lo |les )?pague\b',paid_source))
    cancelled_report=bool(re.search(r'\b(?:tarjeta (?:ya )?esta cancelada|ya (?:la |lo )?cancele|dio de baja la tarjeta)\b',paid_source))
    paid_call_complaint = bool(re.search(r'\b(?:mi cuenta ya esta liquidada|ceros? mi cuenta)\b',paid_source)
        and re.search(r'\b(?:respecto (?:a )?esta molestia|me molesta|estoy molest[oa]|no he tenido buenos comentarios anteriores)\b',paid_source))
    from app.services.context_rules import unknown_debtor_statement
    wrong_line_report = unknown_debtor_statement(text,segments)
    units = sentence_evidence(text, segments)
    for index, unit in enumerate(units):
        if unit['speaker_role'] == 'GESTOR':
            continue
        value = normalize(unit['text'])
        matches = [m for phrase in phrases for m in re.finditer(re.escape(normalize(phrase)), value)]
        matches.extend(variants.finditer(value))
        if wrong_line_report:
            matches.extend(re.finditer(r'\b(?:ya )?me canso de decirles\b|\b(?:ya )?(?:estoy|soy|estamos) hart[oa]s?\b[^.!?]{0,100}\b(?:pregunta y pregunte|preguntando|marque y marque|llamando)\b',value))
        if paid_call_complaint:
            matches.extend(re.finditer(r'\b(?:a que se debe que|por que) me (?:sigan|siguen) llamando\b',value))
        matches.extend(re.finditer(
            r'\b(?:nunca me contest(?:a|an)|'
            r'me (?:cortaba|cortaban|cortaron) la llamada|me colg(?:aron|o)|'
            r'me (?:dice|dices|dijo) que me calle|'
            r'nadie me quiso resolver|'
            r'me hablo (?:bien|muy) enojad[oa]|'
            r'me (?:mentaba|ventaba) la madre|'
            r'los del juridico[^.!?]{0,45}(?:muy|sumamente) groser[oa]s?)\b',value))
        if re.search(r'\b(?:llevo|he tratado|tratando|comunicarme|arreglar)\b',value):
            matches.extend(re.finditer(r'\bno me (?:han )?contestad[oa]\b|\bno me contestan\b',value))
        previous = normalize(units[index-1]['text']) if index and units[index-1]['speaker_role'] != 'GESTOR' else ''
        if re.search(r'\b(?:les (?:marque|mande|envie)|hable y mande|mande muchos mensajes|llamadas por whatsapp)\b',value+' '+previous):
            matches.extend(re.finditer(r'\bno me (?:contestaron|respondieron|respondia|respondio)\b',value))
        phone_context = bool(re.search(r'\b(?:llamadas?|llame|llamar|marcan|marcando|marcado|marcaron)\b', value+' '+previous))
        if cancelled_report:
            matches.extend(re.finditer(r'\b(?:es molesto que esten (?:marque y marque|llamando)|'
                r'(?:me |nos )?(?:sigan|siguen|estan) (?:molestando|hostigando)|'
                r'me (?:marcan|llaman) a cada rato)\b',value))
        if phone_context:
            matches.extend(re.finditer(r'\b(?:me tienen|estoy) inundad[oa] de llamadas\b',value))
            if paid_report:
                matches.extend(re.finditer(r'\b(?:(?:ya )?(?:le )?estoy recibiendo (?:las )?llamadas|me (?:llaman|marcan|hablan)) a cada rato\b',value))
            matches.extend(re.finditer(r'\b(?:no (?:me )?dejan(?: a uno)?[^.!?]{0,65}\b(?:tranquil[oa]|en paz)|'
                r'me (?:estan|han estado|estuvieron) (?:hostigando|acosando)|'
                r'no me (?:sigan|siguieran) (?:molestando|hostigando|acosando)|'
                r'nunca me han (?:contestado|atendido))\b', value))
        complaint_context=bool(re.search(r'\b(?:aclaracion|reportar|reporte|investigar|investigacion|tarjeta|compras|companeros?|cobrar|cobranza|estado de cuenta|desglose|folio)\b',value+' '+previous))
        if complaint_context:
            # Queja expresa de capacidad/solución del servicio; no inferir
            # maltrato de una duda bancaria ni de una hipótesis del gestor.
            matches.extend(re.finditer(r'\b(?:incompetencia de (?:tu|su|este|ese) equipo|'
                r'no tienen (?:al |el )?personal capacitado para (?:resolver|atender))\b',value))
            matches.extend(re.finditer(r'\b(?:nunca|no) me (?:dijeron|dijo|avisaron|aviso|informaron|informo|explicaron|explico)\b[^.!?]{0,100}\b(?:costo|comision|anualidad)\b',value))
            matches.extend(re.finditer(r'\b(?:nunca me avisaron|no me (?:avisaron|dieron solucion)|'
                r'no me (?:lo |la )?quisieron (?:dar|resolver)|'
                r'(?:me (?:enganaron|engano)|no se vale que enganen)|'
                r'(?:muy|son|fueron|estan) (?:prepotentes|prepotantes|preputantes))\b',value))
            matches.extend(re.finditer(r'\bno (?:les )?pedi (?:la |esa )?tarjeta\b',value))
            if re.search(r'\b(?:estado de cuenta|desglose|folio)\b',value+' '+previous):
                matches.extend(re.finditer(r'\b(?:ya fui[^.!?]{0,30}(?:no|tampoco) me lo dan|no me (?:dan|dieron|quieren dar) (?:el )?(?:estado de cuenta|desglose|folio))\b',value))
        if re.search(r'\b(?:ya pague|ya lo pague|ya les pague|capturas? de que ya pague)\b',value):
            matches.extend(re.finditer(r'\b(?:ya )?no (?:estarme|me esten|me sigan) (?:hablando|marcando|llamando)\b',value))
        repeated_work_interruption=re.search(
            r'\bme han estado (?:hablando|marcando|llamando) toda la manana\b[^.!?]{0,100}'
            r'\bme estoy saliendo de mi trabajo\b',value)
        if repeated_work_interruption:
            matches.append(repeated_work_interruption)
        matches.extend(re.finditer(r'\b(?:hasta )?parece que (?:le|me|nos) (?:estan|estaban) '
                                    r'(?:amenazando|agrediendo|hostigando)\b',value))
        matches.extend(re.finditer(r'\b(?:no puedo hablar con nadie[, ]+nadie me contesta|'
                                    r'me dejo en la linea y nadie me contesto)\b',value))
        if prior_call.search(value) or service_actor.search(value) or prior_call.search(previous) or service_actor.search(previous):
            matches.extend(bad_service.finditer(value))
        matches.extend(re.finditer(r'\b(?:ayer|antes|la vez pasada)[^.!?]{0,65}me (?:hablaba|hablo|llamo|marco)[^.!?]{0,65}\b(?:groser[oa]|agresiv[oa]|prepotente)\b',value))
        for match in matches:
            before = value[max(0, match.start()-50):match.start()]
            if re.search(r'\b(?:no|nunca|jamas|nadie)\s*$', before):
                continue
            # Negar/rechazar una queja, preguntar o describir una posibilidad
            # no equivale a denunciar un maltrato recibido.
            if re.search(r'\b(?:no es cierto que|no es verdad que|no dije que|no he dicho que|'
                         r'no hubo|nunca hubo|sin|no fue|no recib[ií]|si (?:alguien|alguna vez))\s*$', before):
                continue
            if re.search(r'\b(?:no es cierto que|no es verdad que|no dije que|no he dicho que)\b[^.!?]{0,45}$',before):continue
            conditional = re.search(r'\b(?:si|en caso de que)\b[^,;.!?]{0,45}$', before)
            affirmative = bool(re.search(r'\bsí\b', unit['text'], re.I))
            if conditional and not affirmative and (conditional.group().startswith('en caso de que') or
                    re.search(r'\b(?:podria|puedo quejarme|puede quejarse|podriamos|ocurriera|pasara)\b', value[match.end():])):
                continue
            if re.match(r'(?:me|nos|se|nunca me|no me)\b', match.group()) and re.search(r'\b(?:mi esposo|mi esposa|mi pareja|mi vecino|mi vecina|mi jefe|mi jefa|mis companeros de trabajo)\b', before) and not service_actor.search(value):
                continue
            if (value.rfind('¿', 0, match.start()) > max(value.rfind(c, 0, match.start()) for c in '.!?')
                    and not accusatory_question.search(value) and not (paid_call_complaint and 'llamando' in match.group())):
                continue
            evidence.append(dict(unit, phrase=match.group()))
    return evidence


def dismissive_message_evidence(text, segments=()):
    evidence = []
    pattern = re.compile(
        r'\b(?:nada mas|solo) (?:seria|es|va a ser) (?:como )?(?:un )?chisme\b|'
        r'\b(?:que falta de educacion|(?:es |ese es )?(?:el )?problema de usted|'
        r'que responsable senor[, ]+pero bueno|ni le puse una pistola)\b')
    for unit in sentence_evidence(text, segments):
        if unit['speaker_role'] in {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}:
            continue
        value = normalize(unit['text'])
        for match in pattern.finditer(value):
            prefix = value[max(0, match.start()-65):match.start()]
            if re.search(r'\b(?:no|nunca|dice que|dijo que|me dijeron que|usted dijo que)\s*$', prefix):
                continue
            evidence.append(dict(unit, phrase=match.group()))
    return evidence


def offensive_asr_variants(text):
    """Variantes acotadas; no tomar «tarjetaunching» como insulto confirmado."""
    return [m.group() for m in re.finditer(
        r'\bching(?:uy|ui|ue)\s*(?:y\s*)?ching(?:uy|ui|ue)\b|'
        r'\bcagando\b|\b(?:ah|a)[, ]+chingas\b|\b(?:una|la|su)chingada\b|\bmaldit[ao]s?[.!?¡¿ ]*$', normalize(text))]
