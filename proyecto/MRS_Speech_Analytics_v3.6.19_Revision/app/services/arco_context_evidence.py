"""Elementos ARCO expresados en dictado y respuestas de conversación.

Solo normaliza formas explícitas; no completa dominios ni inventa documentos.
"""
import re
from app.services.conversation_evidence import normalize, _role_at, sentence_evidence


def spoken_privacy_email(text,segments=()):
    source=normalize(text)
    none={'detected':False,'address':'','method':'SIN_DICTADO_CONFIRMABLE','evidence':''}
    pattern=re.compile(r'\bprivacidad(?:(?P<digit>1)(?=arroba|a roba|\b)|\b)(?P<local>[^@]{0,140}?)(?<![a-z])(?:arroba|a\s+roba)\s*'
        r'(?P<domain>.{0,350}?bradesco\b.{0,150}?(?:\bpunto[,. ]+com[,. ]+(?:(?:si|aja|ok)[,. ]+)*punto[,. ]+(?:mx|eme\s+equis)\b|\.com\.mx\b))')
    for anchor in re.finditer(r'\bprivacidad',source):
        match=pattern.match(source,anchor.start())
        if not match:continue
        if _role_at(text,segments,match.start()) in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        before=source[max(0,match.start()-70):match.start()]
        block=match.group()
        if re.search(r'\b(?:no (?:es|diga)|no|dice que|dijo que|diga que|si fuera)\s*$',before):continue
        if re.search(r'\b(?:gmail|hotmail|outlook|yahoo|bradescard|bancoazteca|otro dominio|no es)\b',match['domain']):continue
        if re.search(r'\b(?:dos|tres|cuatro|cinco|seis|siete|ocho|nueve|[2-9]|\d{2,})\b',match['local']):continue
        # Exigir que bradesco sea el dominio dictado, sin omitir otro dominio
        # previo ni añadir .com cuando solo se oyó/dictó «punto mx».
        after_at=match['domain'].lstrip(' .,;?¿')
        if not re.match(r'(?:(?:aja|si|arroba)[, .?¿]+)*bradesco\b',after_at):continue
        suffix=source[match.end():match.end()+35]
        repeated_suffix=re.match(r'^[., ]*(?:punto com punto mx)\b',suffix)
        if not repeated_suffix and (re.match(r'\.[a-z0-9-]{2,}',suffix)
                or re.match(r'[., ]*punto\s+(?:com|mx|org|net|[a-z]{2,10})\b',suffix)):continue
        one=bool(match['digit'] or re.search(r'\b(?:numero )?(?:1|uno)\b',match['local']))
        return {'detected':True,'address':'privacidad'+('1' if one else '')+'@bradesco.com.mx',
                'method':'DOMINIO_COMPLETO_DICTADO_CON_PUNTOS','evidence':block}
    return none


def removal_process_explanation(text,segments=()):
    units=[u for u in sentence_evidence(text,segments) if u['speaker_role'] not in {'TITULAR','TERCERO','INTERLOCUTOR'}]
    source=normalize(' '.join(u['text'] for u in units))
    rights=bool(re.search(r'\bderechos? (?:a )?arco\b',source) or dictated_rights_mention(text,segments))
    removal=re.search(r'\b(?:sea borrado|borrar|borrado|eliminar|eliminado|retirar|retirado|dar de baja|sacar)\b'
                      r'.{0,80}\b(?:mi |su |el |este )?numero\b.{0,80}\bbase de datos\b',source)
    instructions=re.search(r'\b(?:correo|asunto|leyenda|escribir|escriba|enviar|mande|adjuntar|adjuntando)\b',source)
    denied=re.search(r'\bno (?:se puede|puede|podra|debe|vamos a) (?:borrar|eliminar|retirar|ejercer)\b',source)
    return bool(rights and removal and instructions and not denied and not explicit_arco_denial(text,segments))


def line_tenure_reply(text,segments=()):
    source=normalize(text)
    none={'confirmed':False,'method':'SIN_RESPUESTA_CONTEXTO_LINEA','evidence':'','numeric_years':None}
    duration=r'(?:un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|\d+)\s+(?:anos?|mes(?:es)?|semanas?|dias?)'
    pattern=re.compile(r'\b(?:cuanto tiempo|desde (?:hace )?cuando|hace cuanto(?: tiempo)?)\b'
        r'[^?!.]{0,100}\b(?:linea|numero|telefono)\b[^?!.]{0,40}[?.]\s*'
        r'(?:(?:gestor|interlocutor|cliente|tercero|titular|familiar)\s*:\s*)?'
        r'(?:(?:no|si|pues|como|aproximadamente|mas de|casi|apenas|ya)[, ]+){0,3}'
        r'(?:(?:yo )?(?:tengo|llevo|hace|cuento con)\s+)?(?:(?:como|aproximadamente|mas de|casi|apenas|unos) )?(?P<answer>'+duration+r')\b')
    for match in pattern.finditer(source):
        if _role_at(text,segments,match.start('answer'))=='GESTOR':continue
        before=source[max(0,match.start()-60):match.start()]
        if re.search(r'\b(?:diga que|dice que|dijo que|supongamos)\b',before):continue
        question=match.group().split('?')[0]
        if re.search(r'\b(?:recibiendo|llamadas|marcandole)\b',question):continue
        return {'confirmed':True,'method':'RESPUESTA_DURACION_TRAS_PREGUNTA_LINEA',
                'evidence':match.group(),'speaker_role':_role_at(text,segments,match.start('answer')),
                'numeric_years':None}
    return none


def wrong_number_reply(text,segments=()):
    source=normalize(text)
    pattern=re.compile(r'\b(?:tengo(?: el)? gusto con|me (?:puede|puedo|podria|podre) comunicar (?:por favor )?con|'
                       r'me comunico con)\s+[^.!?]{2,110}[.?]\s*'
                       r'(?P<answer>(?:no[, ]+)?(?:esta|estas|se ha|se han|se) equivocad[oa])\b')
    for match in pattern.finditer(source):
        if _role_at(text,segments,match.start('answer'))=='GESTOR':continue
        if re.match(r'\s*\?',source[match.end():]):continue
        if re.search(r'\b(?:no|dice que|dijo que|diga que)\s*$',source[max(0,match.start()-50):match.start()]):continue
        # Una negativa de número dirigida al gestor no puede borrar una
        # identidad familiar o de titular explícita en la misma conversación.
        contradictions=[u for u in sentence_evidence(text,segments)
                        if u['speaker_role']!='GESTOR' and re.search(
                            r'\b(?:soy yo|soy su (?:espos[oa]|herman[oa]|hij[oa]|madre|padre)|'
                            r'es mi (?:espos[oa]|herman[oa]|hij[oa]|mama|papa)|si (?:lo|la) conozco)\b',normalize(u['text']))]
        if contradictions:continue
        return {'confirmed':True,'method':'RESPUESTA_NUMERO_EQUIVOCADO_TRAS_SOLICITUD_NOMINAL',
                'evidence':match.group(),'speaker_role':_role_at(text,segments,match.start('answer'))}
    return {'confirmed':False,'method':'SIN_RESPUESTA_NUMERO_EQUIVOCADO','evidence':''}


def dictated_rights_mention(text,segments=()):
    source=normalize(text)
    pattern=re.compile(r'\bderechos?\b[. ,]*(?:(?:mi|a|aja|si|ok)[. ,]+){0,4}arco\b')
    for match in pattern.finditer(source):
        roles=[_role_at(text,segments,match.start()),_role_at(text,segments,match.end()-3)]
        if any(r in {'TITULAR','TERCERO','INTERLOCUTOR'} for r in roles):continue
        if re.search(r'\b(?:no (?:existen|aplican)|no|diga que|dice que|dijo que)\s*$',source[max(0,match.start()-70):match.start()]):continue
        return True
    return False


def positive_knowledge_denial(text,segments=(), *, ignore_relationships=False):
    """«¿Le conoce? No» niega conocimiento; «¿No le conoce? No» es ambiguo."""
    source=normalize(text)
    pattern=re.compile(r'\b(?:lo|la|le) conoce(?:s)?(?: (?:usted|a [^?!.]{1,65}))?(?:[, ]+(?:senorita|senora|senor))?\?\s*'
                       r'(?:(?:gestor|interlocutor|cliente|tercero|titular|familiar)\s*:\s*)?'
                       r'(?P<answer>no(?:[, ]+(?:senorita|senora|senor|para nada|no|la verdad no))?)(?=[.!?,]|$)')
    for match in pattern.finditer(source):
        before=source[max(0,match.start()-65):match.start()]
        if re.search(r'\b(?:no|dice que|dijo que|diga que|si)\s*$',before):continue
        if _role_at(text,segments,match.start('answer'))=='GESTOR':continue
        if re.match(r'\s*\?',source[match.end():]):continue
        from app.services.message_contact_evidence import message_contact_evidence
        related=message_contact_evidence(text,segments)
        if not ignore_relationships and any(related[k] for k in ['family','third_party_relationships','work_relationships']):continue
        return {'confirmed':True,'method':'NIEGA_CONOCIMIENTO_TRAS_PREGUNTA_AFIRMATIVA',
                'evidence':match.group(),'speaker_role':_role_at(text,segments,match.start('answer'))}
    return {'confirmed':False,'method':'SIN_NEGATIVA_A_PREGUNTA_AFIRMATIVA','evidence':''}


def explicit_arco_denial(text,segments=()):
    from app.services.conversation_evidence import agent_statement
    return agent_statement(text,segments,
        r'\bno (?:es necesario|se requiere|hace falta|tiene que|debe) (?:usted )?'
        r'(?:ejercer|tramitar|solicitar)\b[^.!?]{0,45}\bderechos? (?:a )?arco\b')
