"""Referentes y actos explícitos: evitar faltas por palabras aisladas."""
import re

from app.services.conversation_evidence import normalize, sentence_evidence


UNKNOWN = re.compile(
    r'\b(?:no (?:lo|la) conozco|ni (?:lo|la) conozco|no conozco a|'
    r'no se quien es|nunca (?:lo|la) he conocido|nunca ha vivido aqui|'
    r'numero (?:es )?(?:equivocado|incorrecto))\b')


def unknown_debtor_statement(text, segments=()):
    """Desconocer al gestor, su nombre o su propósito no desconoce al deudor."""
    for unit in sentence_evidence(text, segments):
        if unit['speaker_role'] == 'GESTOR':
            continue
        value = normalize(unit['text'])
        if '?' in value or '¿' in value:
            continue
        for match in UNKNOWN.finditer(value):
            before = value[max(0, match.start()-70):match.start()]
            after = value[match.end():match.end()+100]
            if re.search(r'\b(?:no|dice que|dijo que|me dijo que|repita que)\s*$', before):
                continue
            if re.match(
                r'\s*[,;:]?\s*(?:usted\b|ustedes\b|su (?:nombre|proposito)\b|'
                r'(?:el|la|al|a la) (?:gestor[ae]?|asesor[ae]?|ejecutiv[oa]|persona que (?:me habla|me llamo|me atendio))\b)', after):
                continue
            if re.search(r'\b(?:el gestor|la gestora|el asesor|la asesora|quien me atendio|quien me llamo)\s*[,;:]?\s*$', before):
                continue
            return True
    return False


def prohibited_threat(text, segments=(), mora=''):
    """Amenaza operativa directa; no distancia, citas ni palabras del cliente.

    La construcción prospectiva explícita («le vamos a quitar su casa») es
    evidencia textual de amenaza. No convierte una mención suelta o un rol
    desconocido en certeza de tono acústico.
    """
    asset = (
        r'\b(?:vamos a|voy a|se va a|se van a|van a|procederemos a|procederan a|le vamos a)\s+'
        r'(?:embargar|retirar|quitar|recoger)\b.{0,45}\b(?:bienes|muebles|casa|vehiculo|propiedad)\b|'
        r'\b(?:embargaremos|retiraremos|quitaremos|recogeremos|embargaran|retiraran|quitaran|recogeran)\b'
        r'.{0,45}\b(?:bienes|muebles|casa|vehiculo|propiedad)\b|'
        r'\b(?:lo|la) vamos a (?:embargar|demandar)\b|\bva a ir a la carcel\b')
    visit = (
        r'\b(?:vamos a|voy a|se va a|se puede|procederemos a)\s+'
        r'(?:realizar|generar|presentar|efectuar|hacer|programar|agendar)\s+(?:una?\s+)?'
        r'(?:visita|diligencia|cobro)\b.{0,60}\b(?:domicilio|domiciliaria|casa|recuperacion)\b|'
        r'\b(?:se realizara|se programara|se generara|se presentara|realizaremos|programaremos|enviaremos)\s+(?:una?\s+)?'
        r'(?:visita|diligencia|cobro)\b.{0,60}\b(?:domicilio|domiciliaria|casa|recuperacion)\b|'
        r'\b(?:iremos|acudiremos)\s+a\s+(?:su\s+)?(?:domicilio|casa)\b')
    pattern = re.compile(asset + ('|' + visit if mora in {'1PV', '2PV'} else ''))
    evidence = []
    for unit in sentence_evidence(text, segments):
        if unit['speaker_role'] in {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}:
            continue
        for clause in re.split(r'[;,]', normalize(unit['text'])):
            if '?' in clause or '¿' in clause:
                continue
            for match in pattern.finditer(clause):
                prefix = clause[:match.start()]
                if re.search(r'\b(?:no|nunca|jamas)\s*$', prefix):
                    continue
                if re.search(r'\b(?:me dijeron|me dijo|dice|dijo|dijeron|usted dijo|me amenazo) que\b[^.!?]{0,100}$', prefix):
                    continue
                evidence.append(dict(unit, phrase=match.group()))
    return evidence


def announced_hangup(text, segments=()):
    unilateral, callback = [], []
    pattern = re.compile(r'\b(?:le voy a colgar|voy a colgar la llamada|le cuelgo|procedo a colgar|terminare la llamada)\b')
    for unit in sentence_evidence(text, segments):
        if unit['speaker_role'] in {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}:
            continue
        value = normalize(unit['text'])
        match = pattern.search(value)
        if not match:
            continue
        if re.search(r'\b(?:no|nunca|dice que|dijo que)\s*$', value[:match.start()]):
            continue
        if (re.search(r'\b(?:si gusta|si quiere|si le parece)\b[^.!?]{0,85}$', value[:match.start()])
                and re.search(r'\b(?:(?:se la|la|le) (?:regreso|devuelvo)|le vuelvo a llamar)\b', value[match.end():])):
            callback.append(unit)
        elif '?' not in value and '¿' not in value:
            unilateral.append(unit)
    return {'unilateral': unilateral, 'callback': callback}
