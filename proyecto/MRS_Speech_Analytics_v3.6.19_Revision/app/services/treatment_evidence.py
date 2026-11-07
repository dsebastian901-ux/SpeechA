"""Quejas y expresiones despectivas: evidencia textual sin inventar tono."""
import re

from app.services.conversation_evidence import normalize, sentence_evidence


def mistreatment_reports(text, segments, phrases):
    evidence = []
    variants = re.compile(
        r'\bme contest(?:o|aron|aban|aba) (?:muy )?mal\b|'
        r'\b(?:una? |su companer[oa] |tu companer[oa] )?me amenazo\b|'
        r'\b(?:me|nos) (?:atendieron|atendio|atienden|atendian|trataron|trato|tratan|trataban|hablaron|hablo|hablan) '
        r'(?:(?:muy|bastante|demasiado) )?(?:mal|pesimo|pesimamente|groseramente|groser[oa]s?|agresiv[oa]s?|'
        r'de mala (?:manera|forma)|de (?:forma|manera) (?:grosera|agresiva)|con malos (?:modos|tratos))\b|'
        r'\b(?:me|nos) (?:estuvo|estaban|estuvieron|estaba) (?:gritando|insultando|agrediendo|amenazando|ofendiendo)\b|'
        r'\b(?:me|nos) (?:grito|insulto|agredio|ofendio|humillo|humillaron|amenazaron)\b|'
        r'\b(?:se burlo|se burlaron) de mi\b')
    prior_call = re.compile(r'\b(?:llamada (?:anterior|pasada)|vez pasada|ultima (?:vez|llamada)|'
                            r'(?:me (?:marco|llamo|hablo)|me (?:marcaron|llamaron|hablaron)) (?:antes|ayer)|'
                            r'(?:asesor|asesora|gestor|gestora|companero|companera) (?:anterior|de ayer))\b')
    service_actor = re.compile(r'\b(?:su (?:companero|companera|asesor|asesora|gestor|gestora)|'
                               r'(?:la persona|el asesor|la asesora|el gestor|la gestora) que me (?:llamo|marco|atendio|hablo))\b')
    bad_service = re.compile(r'\b(?:mala atencion|mal servicio|mal trato|agresion(?:es)?|'
                             r'(?:atencion|actitud|trato) (?:muy )?(?:mal[oa]|pesim[oa]|agresiv[oa]|groser[oa]|prepotente)|'
                             r'(?:fue|era|estuvo|se porto|fueron|eran|estuvieron|se portaron) (?:muy )?(?:agresiv[oa]s?|groser[oa]s?|'
                             r'prepotentes?|despotas?|altaner[oa]s?)|me falto al respeto|'
                             r'(?:la|lo|le) (?:atendieron|atendio|trataron|trato|hablaron|hablo) (?:muy )?'
                             r'(?:mal|pesimo|de mala manera))\b')
    accusatory_question = re.compile(
        r'\b(?:usted|tu) (?:fue|fuiste|es|eres) (?:la|el) (?:que|quien) me '
        r'(?:insulto|agredio|ofendio|amenazo|grito)\b')
    paid_source=normalize(text)
    paid_call_complaint = bool(re.search(r'\b(?:mi cuenta ya esta liquidada|ceros? mi cuenta)\b',paid_source)
        and re.search(r'\b(?:respecto (?:a )?esta molestia|me molesta|estoy molest[oa]|no he tenido buenos comentarios anteriores)\b',paid_source))
    units = sentence_evidence(text, segments)
    for index, unit in enumerate(units):
        if unit['speaker_role'] == 'GESTOR':
            continue
        value = normalize(unit['text'])
        matches = [m for phrase in phrases for m in re.finditer(re.escape(normalize(phrase)), value)]
        matches.extend(variants.finditer(value))
        if paid_call_complaint:
            matches.extend(re.finditer(r'\b(?:a que se debe que|por que) me (?:sigan|siguen) llamando\b',value))
        matches.extend(re.finditer(
            r'\b(?:nunca me contest(?:a|an)|'
            r'me (?:cortaban|cortaron) la llamada|me colg(?:aron|o)|'
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
        if phone_context:
            matches.extend(re.finditer(r'\b(?:no (?:me )?dejan(?: a uno)?[^.!?]{0,65}\b(?:tranquil[oa]|en paz)|'
                r'me (?:estan|han estado|estuvieron) (?:hostigando|acosando)|'
                r'no me (?:sigan|siguieran) (?:molestando|hostigando|acosando)|'
                r'nunca me han (?:contestado|atendido))\b', value))
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
        for match in matches:
            before = value[max(0, match.start()-50):match.start()]
            if re.search(r'\b(?:no|nunca|jamas|nadie)\s*$', before):
                continue
            # Negar/rechazar una queja, preguntar o describir una posibilidad
            # no equivale a denunciar un maltrato recibido.
            if re.search(r'\b(?:no es cierto que|no es verdad que|no dije que|no he dicho que|'
                         r'no hubo|nunca hubo|sin|no fue|no recib[ií]|si (?:alguien|alguna vez))\s*$', before):
                continue
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
        r'\b(?:ah|a)[, ]+chingas\b|\b(?:una|la|su)chingada\b|\bmaldit[ao]s?[.!?¡¿ ]*$', normalize(text))]
