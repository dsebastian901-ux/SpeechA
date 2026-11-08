"""Evidencia de recado para dictaminación: propósito, recepción y contacto separados.

No asigna voz acústica, no certifica dígitos ni modifica la transcripción.
"""
import re
from app.services.conversation_evidence import normalize, _role_at
from app.services.message_contact_evidence import BAD_PREFIX, _outside_question


def return_purpose(text, segments=()):
    source=normalize(text);found=[]
    patterns=[
        r'\bque se (?:comunique|contacte)\b',
        r'\bse (?:tiene que|debe(?: de)?) comunicar\b',
        r'\bpara que (?:posteriormente )?(?:(?:el|la) (?:senor(?:a|ita)?|titular) [^.!?]{1,65}?)?se (?:pueda |puede )?comunicar(?: con nosotros)?\b',
        r'\b(?:es |seria )?(?:muy )?importante (?:que )?(?:(?:el|la) (?:senor(?:a|ita)?|titular) [^.!?]{1,65}?)?(?:se comunique|su comunicacion|la comunicacion)\b',
        r'\b(?:que |para que )?(?:me|nos) (?:pueda |puede )?(?:regalar|regala|regale|regresar|regrese) (?:una? |la )llamada\b',
        r'\b(?:indiquele|digale|mencionele)\b[^.!?]{0,140}\b(?:que se comunique|se comunique|regrese la llamada)\b',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern,source):
            before=source[max(0,m.start()-80):m.start()]
            if _role_at(text,segments,m.start())in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
            if re.search(r'\b(?:no|dice que|dijo que|diga que|repita que|por ejemplo|supongamos que|si)\s*$',before):continue
            if re.search(r'\bno (?:se )?(?:comunique|comunicar|regale|regrese)\b',m.group()):continue
            found.append({'text':m.group(),'method':'PROPOSITO_EXPLICITO_DE_RETORNO','human_verified':False})
    return found


def extra_message_receipt(text,segments=()):
    from app.services.message_dialogue_evidence import callback_available,agent_continuation
    source=normalize(text);found=[]
    if not callback_available(text,segments)or not return_purpose(text,segments):return found
    prompts=[
        r'(?:le |me )?(?:puedo|podria|podrian|podre|pudiera|permitiria) (?:entonces )?dejar(?:le)? (?:un |el )?(?:recado|mensaje)(?: con usted)?',
        r'(?:tiene|tendra|tendria|puede|podria|puedria) (?:usted )?(?:(?:con que|donde) (?:anotar|apuntar)|anotar un numero(?: telefonico)?)',
        r'(?:tome|toma|tom[eé]) nota(?:[, ]+por favor)?(?:[^.!?]{0,65}\bnumero[^.!?]{0,70})?',
    ]
    # Respuesta local afirmativa: admite ASR sin puntuación entre pregunta y
    # respuesta. No permite atravesar otra instrucción ni inventa un «sí».
    for prompt in prompts:
        p=re.compile(r'\b(?P<prompt>'+prompt+r')[^.!?]{0,180}?[?. ,]+\s*'
            r'(?P<answer>si(?:[, ]+diga(?:me|nme))?|claro(?: que si)?|aja|a ver[, ]+diga(?:me|nme))\b')
        for m in p.finditer(source):
            before=source[max(0,m.start()-85):m.start()]
            if _role_at(text,segments,m.start('answer'))in{'GESTOR','TITULAR'}:continue
            if BAD_PREFIX.search(before)or re.search(r'\b(?:diga que|dice que|dijo que|repita que|por ejemplo|supongamos que|si)\s*$',before):continue
            if re.match(r'\s*\?',source[m.end():]):continue
            if re.search(r'\b(?:pero no|no puedo|no quiero|solo si|si tengo tiempo)\b',source[m.end():m.end()+65]):continue
            if agent_continuation(source,m.start('answer'),m.end()):continue
            found.append({'text':m.group(),'phrase':m['answer'],'method':'RESPUESTA_LOCAL_A_DICTADO_CON_RETORNO_Y_CONTACTO',
                          'speaker_role':_role_at(text,segments,m.start('answer')),'human_verified':False,
                          'contact_digits_verified':False})
    from app.services.message_contact_evidence import callback_dictation_fragments
    from app.services.payment_reference_validation import callback_numbers
    fragments=callback_dictation_fragments(text)+callback_numbers(text)
    for fragment in fragments:
        value=normalize(fragment['text']);at=source.find(value)
        if at<0:continue
        tail=source[at+len(value):at+len(value)+130]
        ack=re.match(r'[,.?!¿ ]*(?P<answer>si[, ]+es correcto)\b',tail)
        if not ack:
            ack=re.match(r'[,. ]*(?:le (?:corroboro|corroporo|confirmo)[^.!?]{0,75}[, ]*)?¿?correcto\?\s*(?P<answer>si)\b',tail)
        if not ack:continue
        pos=at+len(value)+ack.start('answer')
        if _role_at(text,segments,pos)in{'GESTOR','TITULAR'}:continue
        if re.match(r'\s*(?:\?|[, ]*pero no)',tail[ack.end():]):continue
        found.append({'text':fragment['text']+' '+ack.group(),'method':'CONFIRMA_DICTADO_TELEFONICO_EN_RESPUESTA_LOCAL',
            'speaker_role':_role_at(text,segments,pos),'human_verified':False,'contact_digits_verified':False})
    # Promesa de retransmitir el aviso tras un contacto proporcionado.
    for m in re.finditer(r'\b(?P<answer>(?:(?:ok|si|claro)[, ]+)?(?:yo )?le (?:informo|paso (?:el |su )recado|doy (?:el |su )recado))\b',source):
        if _role_at(text,segments,m.start())in{'GESTOR','TITULAR'}or not _outside_question(source,m.start(),m.end()):continue
        if BAD_PREFIX.search(source[max(0,m.start()-70):m.start()]):continue
        if re.search(r'\b(?:diga|digale|repita|gracias por)\b[^.!?]{0,55}$',source[max(0,m.start()-80):m.start()]):continue
        found.append({'text':m.group(),'method':'RECEPTOR_CONFIRMA_RETRANSMISION_DEL_CONTACTO','speaker_role':_role_at(text,segments,m.start()),'human_verified':False})
    return found
