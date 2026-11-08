"""Hechos locales de interlocución; no asigna voces por alternancia ni por Excel."""
import re
from app.services.conversation_evidence import normalize, sentence_evidence, _role_at, KIN
from app.services.message_contact_evidence import _outside_question

QUOTED = re.compile(r'\b(?:dice que|dijo que|diga que|repita que|por ejemplo|si fuera|si fuese|si tuviera|no es cierto que)\b[^.!?]{0,55}$')
RELATION = r'(?:con quien (?:tengo|tuve) (?:el )?gusto[^?!.]{0,80}|que (?:parentesco|parentezco|parantesco|aparentesco|relacion)\b[^?!.]{0,110}|que es (?:usted|de usted)\b[^?!.]{0,90}|(?:usted(?: es)?|es usted|conocid[oa])[^?!.]{0,55}\b(?:familiar|conocid[oa]|amig[oa]|familia)\b[^?!.]{0,60})'
CONTACT = r'(?:amig[oa]|conocid[oa]|vecin[oa])'


def _recipient(source, text, segments, start, end):
    return (_role_at(text,segments,start)not in{'GESTOR','TITULAR'}
        and _outside_question(source,start,end)
        and not QUOTED.search(source[max(0,start-90):start]))


def _record(source, match, text, segments, method, field='answer', phrase=None):
    return {'text':match.group(),'phrase':phrase or match[field], 'speaker_role':_role_at(text,segments,match.start(field)),
            'start':None,'end':None,'human_verified':False,'method':method}


def contact_dialogue_evidence(text, segments=()):
    source=normalize(text);result={'family':[],'third_party_relationships':[],'work_relationships':[],'acceptance':[]}
    answer=r'(?:(?:no|si|ah|este)[, ]+){0,2}(?:(?:yo )?(?:soy|es|somos|era) )?(?:(?:un|una|su|mi) )?(?:su)?'
    pattern=re.compile(r'\b'+RELATION+r'[?.]\s*(?P<answer>'+answer+r'(?P<kin>'+KIN+r'|familia(?:r)?))\b')
    for m in pattern.finditer(source):
        if _recipient(source,text,segments,m.start('answer'),m.end('answer')):
            if re.search(r'\bno (?:soy|es|somos|era)\b',m['answer']):continue
            result['family'].append(_record(source,m,text,segments,'PARENTESCO_EN_RESPUESTA_LOCAL',phrase=m['kin']))
    # «Soy hija» y «habla su esposo» son autoidentificación de un tercero.
    direct=re.compile(r'\b(?P<answer>(?:(?:yo )?soy (?:su )?|(?:le )?habl[ao] su |no[, ]+es su )(?P<kin>'+KIN+r'))\b')
    for m in direct.finditer(source):
        if not _recipient(source,text,segments,m.start(),m.end()):continue
        if re.search(r'\b(?:no|nunca|no es|no soy)\s*$',source[max(0,m.start()-50):m.start()]):continue
        result['family'].append(_record(source,m,text,segments,'AUTOIDENTIFICACION_FAMILIAR',phrase=m['kin']))
    patterns=[
        re.compile(r'\b'+RELATION+r'[?.]\s*(?P<answer>'+answer+CONTACT+r')\b'),
        re.compile(r'\b(?P<answer>no[, ]+con su '+CONTACT+r')\b'),
        re.compile(r'\b(?:es (?:usted )?(?:su )?'+CONTACT+r'|(?:usted )?(?:lo|la|le) conoce(?:s)?)\?\s*(?P<answer>si|asi es|correcto)\b'),
    ]
    patterns.append(re.compile(r'\b(?:amig[oa][, ]+conocid[oa]|conocid[oa][, ]+amig[oa])\s*[?.]\s*(?P<answer>(?:si[, ]+)?(?:amig[oa]|conocid[oa]))\b'))
    for p in patterns:
        for m in p.finditer(source):
            if not _recipient(source,text,segments,m.start('answer'),m.end('answer')):continue
            if re.search(r'\bno (?:soy|es|somos)\b',m['answer']):continue
            if re.search(r'\bno\s*$',source[max(0,m.start()-25):m.start()]):continue
            result['third_party_relationships'].append(_record(source,m,text,segments,'CONOCIMIENTO_AFIRMATIVO_EN_DIALOGO'))
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role']in{'GESTOR','TITULAR'}:continue
        value=normalize(unit['text'])
        if re.search(r'\b(?:ya no trabaja|ya no trabajo) con nosotros\b',value) and '?'not in value:
            result['work_relationships'].append(dict(unit,phrase='ya no trabaja con nosotros',method='CONTACTO_LABORAL_REPORTADO',human_verified=False))
        if re.search(r'\b(?:fue mi vecin[oa]|era mi pareja|eramos esposos|somos vecin[oa]s)\b',value)and '?'not in value:
            result['third_party_relationships'].append(dict(unit,phrase=value,method='VINCULO_CONOCIDO_REPORTADO',human_verified=False))
    work=re.compile(r'\b'+RELATION+r'[?.]\s*(?P<answer>(?:(?:yo )?soy (?:su |una? )?)?(?:compan(?:ero|era|ia) de(?:l)? trabajo|companero de la chamba))\b')
    for m in work.finditer(source):
        if _recipient(source,text,segments,m.start('answer'),m.end('answer')):
            result['work_relationships'].append(_record(source,m,text,segments,'RESPUESTA_LABORAL_LOCAL'))
    # Una pregunta familiar respondida con sí acredita ese parentesco concreto.
    confirm=re.compile(r'\b(?:usted )?es (?:usted )?(?:su )?(?P<kin>'+KIN+r') (?:de [^?!.]{2,70})?\?\s*(?P<answer>si|asi es|correcto)\b')
    for m in confirm.finditer(source):
        if _recipient(source,text,segments,m.start('answer'),m.end('answer')):
            result['family'].append(_record(source,m,text,segments,'PARENTESCO_ESPECIFICO_CONFIRMADO',phrase=m['kin']))
    # Preparación y recepción reales del mensaje, independientes de parentesco.
    offer=re.compile(r'\b(?:puedo|podria|podre|pudiera|permitiria) (?:dejar(?:le|lo|selo)?|dar(?:le|lo)?) '
        r'(?:con usted (?:un |el )?(?:recado|mensaje)|(?:un |el )?(?:recado|mensaje)(?: con usted)?)'
        r'[^?!.]{0,80}[?.]\s*(?P<answer>(?:a ver[, ]+)?(?:si[, ]+)?(?:digame(?: usted)?|diganme|claro[, ]+digamos|claro|si|aja))\b')
    for m in offer.finditer(source):
        if not _recipient(source,text,segments,m.start('answer'),m.end('answer')):continue
        if re.search(r'\b(?:no|dice que|dijo que|diga que)(?: le)?\s*$',source[max(0,m.start()-60):m.start()]):continue
        if re.search(r'\b(?:pero no|no puedo|no quiero|si tengo tiempo)\b',source[m.end():m.end()+60]):continue
        result['acceptance'].append(_record(source,m,text,segments,'ACEPTACION_LOCAL_DE_OFERTA_DE_RECADO'))
    from app.services.message_dialogue_evidence import callback_available
    if callback_available(text,segments):
        for unit in sentence_evidence(text,segments):
            if unit['speaker_role']in{'GESTOR','TITULAR'}:continue
            value=normalize(unit['text'])
            if re.fullmatch(r'(?:(?:ah|ok|si|bueno)[, ]+){0,2}(?:le (?:doy|paso|comento|aviso) (?:el |su )?(?:numero|recado)|yo le (?:comento|aviso)|pasame la razon|voy a capturar)[.!]?',value):
                result['acceptance'].append(dict(unit,method='RECEPTOR_CONFIRMA_AVISO_O_CAPTURA',human_verified=False))
    return result


def expanded_unknown_response(text,segments=()):
    source=normalize(text);none={'confirmed':False,'method':'SIN_DESCONOCIMIENTO_ADICIONAL','evidence':''}
    related=contact_dialogue_evidence(text,segments)
    if any(related[k]for k in ['family','third_party_relationships','work_relationships']):return none
    patterns=[
        re.compile(r'\b(?:conocid[oa]|amig[oa])[, ]+(?:amig[oa][, ]+)?familia(?:r|s)?\b[^?!.]{0,100}[?.]\s*(?P<answer>(?:pues[, ]+)?no)\b'),
        re.compile(r'\b(?:algun |es algun )?(?:amigo|conocido|familiar|vecino)[^?!.]{0,75}\b(?:familiar|conocido|vecino)\b[^?!.]{0,80}\?\s*(?P<answer>(?:pues[, ]+)?no)\b'),
        re.compile(r'\b(?P<answer>(?:yo )?no (?:tengo conocido|conozco (?:a )?(?:esa persona|ese individuo|el nombre)|soy la persona que (?:buscan|estan buscando)))\b'),
    ]
    for p in patterns:
        for m in p.finditer(source):
            if re.match(r'[, ]*(?:esto|este|es|soy|somos|estoy|trabaja|pero|tampoco)\b',source[m.end():m.end()+45]):continue
            if _recipient(source,text,segments,m.start('answer'),m.end('answer'))and not re.search(r'\b(?:no|dice que|diga que)\s*$',source[max(0,m.start()-50):m.start()]):
                return {'confirmed':True,'method':'NEGATIVA_EXPLICITA_EN_CONTEXTO_DE_CONTACTO','evidence':m.group(),'human_verified':False}
    # Número equivocado + adquisición/antigüedad propia y sin vínculo declarado.
    wrong=re.search(r'\b(?P<answer>(?:no[, ]+)?(?:esta|estas|se ha|se) equivocad[oa])\b',source)
    if wrong and _recipient(source,text,segments,wrong.start(),wrong.end()):
        if re.search(r'\b(?:compre|comprar|adquiri|adquirir|mi linea|con (?:este|el|mi|la) (?:numero|linea)|este numero (?:lo tengo|ya no))\b',source):
            return {'confirmed':True,'method':'NUMERO_EQUIVOCADO_Y_LINEA_PROPIA','evidence':wrong.group(),'human_verified':False}
    return none


def declared_intermediary(text,segments=()):
    """Respuesta al nombre solicitado; la pregunta posterior no borra la ausencia."""
    source=normalize(text);none={'confirmed':False,'method':'SIN_RESPUESTA_INTERMEDIARIA','evidence':''}
    prompt=r'(?:me (?:puede |podria |podre |pueden )?comunicar (?:por favor |de favor )?con|me comunico con|seria tan amable de comunicarme (?:por favor )?con|tengo(?: el)? (?:gusto|uso) con|hablo con|se encuentra)'
    pattern=re.compile(r'\b'+prompt+r'\s+(?P<identity>[^?!.]{2,105})[?.]\s*(?P<answer>(?:ah[, ]+|este[, ]+|no[, ]+){0,2}'
        r'(?:no se encuentra(?:n)?|no esta|salio|se le olvido (?:el |su )?telefono))\b')
    negative_identity=re.compile(r'\bes usted(?: (?:el|la) titular)?\?\s*(?P<answer>no(?:[, ]+(?:pero )?digame)?)\b')
    for p in (pattern,negative_identity):
        for m in p.finditer(source):
            if p is pattern:
                from app.services.contextual_identity_evidence import valid_nominal_request,BAD_IDENTITY
                if not valid_nominal_request(source,m.start(),m['identity'])or BAD_IDENTITY.search(m['identity'])or re.search(r'\b(?:aplicacion|extracto|sistema|pago|corte)\b',m['identity']):continue
            if _role_at(text,segments,m.start('answer'))in{'GESTOR','TITULAR'}:continue
            before=source[max(0,m.start()-70):m.start()]
            if QUOTED.search(before)or re.search(r'\bno\s*$',before):continue
            tail=source[m.end():m.end()+150]
            if re.match(r'\s*\?',tail):continue
            if re.search(r'\b(?:se lo comunico|ya se lo paso|te hablan|ahora habla (?:el|la) titular|soy yo|ella habla|el habla|soy (?:el|la) titular)\b',source[m.end():]):continue
            return {'confirmed':True,'method':'RESPUESTA_DE_AUSENCIA_O_NO_IDENTIDAD_A_SOLICITUD_NOMINAL','evidence':m.group(),'human_verified':False}
    return none
