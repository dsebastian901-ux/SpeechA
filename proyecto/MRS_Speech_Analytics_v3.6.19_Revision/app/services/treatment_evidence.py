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
    units = sentence_evidence(text, segments)
    for index, unit in enumerate(units):
        if unit['speaker_role'] == 'GESTOR':
            continue
        value = normalize(unit['text'])
        matches = [m for phrase in phrases for m in re.finditer(re.escape(normalize(phrase)), value)]
        matches.extend(variants.finditer(value))
        previous = normalize(units[index-1]['text']) if index and units[index-1]['speaker_role'] != 'GESTOR' else ''
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
            if re.match(r'(?:me|nos|se)\b', match.group()) and re.search(r'\b(?:mi esposo|mi esposa|mi pareja|mi vecino|mi vecina|mi jefe|mi jefa|mis companeros de trabajo)\b', before) and not service_actor.search(value):
                continue
            if value.rfind('¿', 0, match.start()) > max(value.rfind(c, 0, match.start()) for c in '.!?'):
                continue
            evidence.append(dict(unit, phrase=match.group()))
    return evidence


def dismissive_message_evidence(text, segments=()):
    evidence = []
    pattern = re.compile(r'\b(?:nada mas|solo) (?:seria|es|va a ser) (?:como )?(?:un )?chisme\b')
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
        r'\b(?:una|la|su)chingada\b|\bmaldit[ao]s?[.!?¡¿ ]*$', normalize(text))]
