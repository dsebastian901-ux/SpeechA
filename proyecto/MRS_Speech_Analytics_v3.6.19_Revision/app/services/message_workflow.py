"""Recepción y contacto como hechos ordenados, sin reconstruir voces o números."""
import re
from app.services.conversation_evidence import normalize, _role_at
from app.services.message_contact_evidence import _outside_question, BAD_PREFIX


def receipt_events(text, segments=()):
    source=normalize(text);events=[]
    patterns=[
        r'\b(?P<answer>(?:claro[.!]\s*)?si[, ]+diga(?:me|nme))[.!]\s*(?:es (?:el )?)?(?=cincuenta|\d{2})',
        r'\bquedamos al pendiente (?:de )?que le pase el recado[^.!?]{0,25}[.!]\s*(?P<answer>claro[, ]+claro que si|claro que si|si[, ]+claro)\b',
        r'\ble (?:puedo|podria|podre|pudiera) dejar (?:un |el )?numero (?:de contacto|telefonico)[^.!?]{0,160}[.?]\s*(?P<answer>si(?:[, ]+claro)?|claro(?: que si)?|diga(?:me|nme))\b',
        r'\b(?:tiene|tendra|tendria|tienes) (?:usted )?(?:donde|con que) (?:anotar|apuntar|tomar nota)[^.!?]{0,65}[?]\s*(?P<answer>(?:si[, ]+)?(?:claro(?: que si)?|diga(?:me|nme)|a ver[, ]+diga(?:me|nme)|si))\b',
        r'\b(?:puedo|podria|podre|pudiera) dejar(?:le|lo)? (?:con usted )?(?:un |el )?(?:recado|mensaje)[^.!?]{0,80}[?]\s*(?P<answer>(?:si[, ]+)?(?:diga(?:me|nme)|claro(?: que si)?|si|de acuerdo))\b',
        r'\b(?P<answer>(?:si[, ]+)?(?:yo le (?:comento|aviso)(?=\s*(?:[,!.]|$|cuando (?:lo|la) vea|en cuanto (?:lo|la) vea))|(?:yo )?le paso (?:el |su )?(?:recado|mensaje|numero)|lo tengo anotado|ya lo anote|ya tome (?:el |su )?numero))\b',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern,source):
            pos=match.start('answer');end=match.end('answer')
            if 'cincuenta' in pattern and not re.search(r'\b(?:anot\w*|numero telefonico|telefono)\b',source[max(0,match.start()-160):match.start()]):continue
            if 'anotar|apuntar|tomar nota' in pattern and not re.search(r'\b(?:recado|mensaje|se comunique|comunicarse|contacto)\b',source[max(0,match.start()-500):match.end()+500]):continue
            if _role_at(text,segments,pos)in{'GESTOR','TITULAR'}:continue
            if not _outside_question(source,pos,end)or BAD_PREFIX.search(source[max(0,match.start()-70):match.start()]):continue
            tail=source[end:end+90]
            if re.match(r'\s*\?',tail)or re.search(r'^\s*[, ]*(?:pero no|no puedo|no quiero|si tengo tiempo)\b',tail):continue
            # «Sí, a ese número que se comunique» continúa instrucciones del
            # gestor. No equivale a una respuesta de recepción.
            if re.match(r'[, ]*(?:a ese numero|hablo|hablamos|me presento|mi nombre|le reitero)\b',tail):continue
            events.append({'text':match.group(),'position':pos,'normalized_end':end,
                'method':'RECEPCION_LOCAL_DEL_MENSAJE','speaker_role':_role_at(text,segments,pos),
                'start':None,'end':None,'human_verified':False,'contact_digits_verified':False})
    return events


def directed_notification(text,segments=()):
    """Aviso dirigido al ausente con retorno para negociar, no autopresentación."""
    source=normalize(text);found=[]
    pattern=re.compile(r'\ble puede (?:mencionar|comentar|indicar)\b[^.!?]{0,250}')
    from app.services.message_dialogue_evidence import callback_available
    if not callback_available(text,segments):return found
    for match in pattern.finditer(source):
        if _role_at(text,segments,match.start())in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        if BAD_PREFIX.search(source[max(0,match.start()-70):match.start()]):continue
        if not re.search(r'\b(?:familiar|el senor|la senora|su hermano|su hermana)\b',match.group()):continue
        if not re.search(r'\b(?:nos estamos comunicando|hablamos|se comunica)\b',match.group()):continue
        tail=source[match.end():]
        if not re.search(r'\b(?:conciliacion de pago|negociar|negociacion|llegar a un acuerdo)\b',tail):continue
        found.append({'text':match.group(),'method':'AVISO_DIRIGIDO_CON_CONTACTO_PARA_NEGOCIAR','human_verified':False})
    return found


def workflow_validation(text,segments,assessment,body,refusal,delivery,human=None):
    from app.services.message_dialogue_evidence import callback_available,existing_callback_confirmation
    source=normalize(text);events=[]
    for evidence in assessment.get('acceptance',[]):
        fragment=normalize(evidence.get('text',''));position=evidence.get('position')
        if position is None:position=source.find(fragment)if fragment else-1
        if position>=0:events.append(dict(evidence,position=position,kind='RECEPTION'))
    human=human or{}
    supplied=bool(callback_available(text,segments))
    known=existing_callback_confirmation(text,segments)
    valid=bool(assessment.get('acceptance') and body and supplied and not refusal.get('confirmed'))
    if human.get('valid')and human.get('message_delivered')and human.get('callback_delivered'):
        valid=True
    # Una negativa temporal a anotar no invalida recepción posterior y
    # contacto efectivamente disponible. Una negativa final sí prevalece.
    if delivery.get('review_required'):
        valid=False
        if events and supplied and body and not refusal.get('confirmed'):
            last=max(e['position']for e in events)
            negatives=list(re.finditer(r'\bno (?:puedo anotar|tengo (?:donde|con que) anotar)\b',source))
            if negatives and last>negatives[-1].end():valid=True
    return {'complete':valid,'recipient_accepted':bool(assessment.get('acceptance')),
        'directed_body':bool(body),'callback_available':supplied,
        'previous_contact_confirmed':bool(known),'final_refusal':bool(refusal.get('confirmed')),
        'events':sorted(events,key=lambda e:e['position']),
        'method':'HECHOS_ORDENADOS_DE_RECEPCION_Y_CONTACTO','human_verified':bool(human.get('valid')),
        'conditional_relay_does_not_cancel_receipt':True}
