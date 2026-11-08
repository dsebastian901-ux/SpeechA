"""Recepción de recados por turnos de dictado y lectura de vuelta.

La evidencia procede del texto ASR. No certifica voces ni corrige dígitos.
"""
import re
from app.services.conversation_evidence import normalize,sentence_evidence,_role_at,KIN
from app.services.message_contact_evidence import BAD_PREFIX,MESSAGE,_outside_question,_item
from app.services.payment_reference_validation import callback_numbers,TOKEN,_digits


def agent_continuation(source,start,end):
    before=source[max(0,start-55):start]
    after=source[end:end+100]
    return bool(re.search(r'\b(?:como|lo que|tal como|por eso)\s*$',before)
        or re.match(r'[, :]*(?:hablo|hablamos|nos comunicamos|me comunico|estamos (?:hablando|llamando)|mi nombre es|aqui seria importante|aqui es importante|le reitero|soy (?:el|la) asesor)\b',after))


def phone_present(text):
    from app.services.message_contact_evidence import callback_dictation_fragments
    return bool(callback_numbers(text)or callback_dictation_fragments(text))


def _answer_ok(text,segments,source,match):
    if _role_at(text,segments,match.start('answer'))in{'GESTOR','TITULAR'}:return False
    tail=source[match.end():match.end()+75]
    if re.match(r'\s*\?',tail):return False
    if re.search(r'\b(?:pero no|no puedo|no quiero|no le voy|solo si|si tengo tiempo|si puedo|cuando pueda|en caso de)\b',tail):return False
    return not BAD_PREFIX.search(source[max(0,match.start()-70):match.start()])


def dialogue_message_evidence(text,segments=()):
    source=normalize(text);result={'family':[],'work_relationships':[],'third_party_relationships':[],'acceptance':[]}
    family=re.compile(r'\b(?:que (?:relacion|parentesco|parentezco)(?: que)?\b[^?!.]{0,115}|'
                      r'que es (?:de usted|usted (?:del|de la|de el))[^?!.]{0,60})[?.]\s*'
                      r'(?P<answer>(?:(?:soy|es|con) )?(?:mi |su )?'+KIN+r')\b')
    for match in family.finditer(source):
        if _answer_ok(text,segments,source,match):
            result['family'].append(_item(source,match,'PARENTESCO_EN_RESPUESTA_DIRECTA',text,segments,'answer'))
    acquaintance=re.compile(r'\bque (?:parentesco|parentezco|relacion)\b[^?!.]{0,120}[?.]\s*(?P<answer>(?:soy |es )?(?:su |un |una )?(?:amig[oa]|conocid[oa]|vecin[oa]))\b')
    for match in acquaintance.finditer(source):
        if (_answer_ok(text,segments,source,match) and not re.search(r'\bno es (?:un |mi |su )?(?:conocid[oa]|amig[oa])\b',source[match.end():])):
            result['third_party_relationships'].append(_item(source,match,'CONOCIDO_EN_RESPUESTA_A_RELACION',text,segments,'answer'))
    nominal_relative=re.compile(r'\b(?:o es usted|es usted (?:el |la )?titular)[?. ]+no[, ]+(?P<answer>su '+KIN+r')\b')
    for match in nominal_relative.finditer(source):
        if _answer_ok(text,segments,source,match):result['family'].append(_item(source,match,'RESPONDE_PARIENTE_A_IDENTIFICACION',text,segments,'answer'))
    work=re.compile(r'\b(?:es (?:un |una |mi |su )?compan(?:ero|era) (?:mi[oa] )?de trabajo|'
                    r'(?:yo )?trabajo con (?:el|ella))\b')
    for match in work.finditer(source):
        if (_role_at(text,segments,match.start())not in{'GESTOR','TITULAR'}
                and _outside_question(source,match.start(),match.end())
                and not BAD_PREFIX.search(source[max(0,match.start()-65):match.start()])):
            result['work_relationships'].append(_item(source,match,'RELACION_LABORAL_DECLARADA',text,segments))
    note=re.compile(r'\b(?:(?:(?:no se si )?tenga|tiene|tendra|tendria|tienen|tienes) (?:usted )?'
                    r'(?:donde (?:anotar|apuntar|escribir|tomar notas?)|con que (?:anotar|apuntar))|'
                    r'me indica para dictarselo(?:[, ]+por favor)?)'
                    r'[^?!.]{0,95}[?.]\s*(?:(?:ah|eh)[, ]+)?'
                    r'(?P<answer>si(?:[, ]+(?:claro|digame|diganme))?|claro(?:[, ]+la escucho| que si)?|aja(?:[, ]+diga(?:me|nme))?|'
                    r'a ver(?:[, ]+a ver){0,2}[, ]+(?:digame|diganme|demelo)|listo|ya)\b')
    for match in note.finditer(source):
        nearby=source[max(0,match.start()-400):match.end()+950]
        if _answer_ok(text,segments,source,match)and MESSAGE.search(nearby):
            result['acceptance'].append(_item(source,match,'RESPUESTA_A_PREPARACION_DEL_DICTADO',text,segments,'answer'))
    # La solicitud de repetir y la lectura de vuelta acreditan participación;
    # solo se admiten en tema telefónico con un dictado completo o fraccionado.
    repeat=re.compile(r'\b(?:(?:me (?:lo )?(?:puede|podria|pudiera) (?:repetir|rectificar|corroborar|confirmar))|'
                      r'me (?:lo )?(?:repite|rectifica|corrobora))[^?!.]{0,35}[?.]\s*')
    for match in repeat.finditer(source):
        nearby=source[max(0,match.start()-850):match.end()+450]
        before=source[max(0,match.start()-750):match.start()]
        topics=list(re.finditer(r'\b(?:numero(?: telefonico)?|telefono|saldo|monto|importe|tarjeta|referencia|pesos)\b',before))
        if not topics or topics[-1].group()not in{'numero','numero telefonico','telefono'}:continue
        if BAD_PREFIX.search(source[max(0,match.start()-65):match.start()]):continue
        tail=source[match.end():match.end()+210];tokens=list(TOKEN.finditer(tail))
        if not tokens or tokens[0].start()>35:continue
        if not re.fullmatch(r'[\W_]*(?:(?:a ver|si|aja)[\W_]*)*',tail[:tokens[0].start()]):continue
        group=[tokens[0]]
        for token in tokens[1:]:
            if not re.fullmatch(r'[\W_]*(?:(?:si|aja|ah|ok|correcto|a ver)[\W_]*)*',tail[group[-1].end():token.start()]):break
            group.append(token)
        digits=[_digits(t.group())for t in group]
        if any(v is None for v in digits)or len(group)<2 or sum(len(v)for v in digits)<4:continue
        answer_pos=match.end()+group[0].start()
        if _role_at(text,segments,answer_pos)=='GESTOR':continue
        if not phone_present(nearby):continue
        result['acceptance'].append({'text':source[match.start():match.end()+group[-1].end()],
            'method':'LECTURA_DE_VUELTA_TRAS_SOLICITUD_TELEFONICA','speaker_role':_role_at(text,segments,answer_pos),
            'start':None,'end':None,'human_verified':False,'contact_digits_verified':False})
    # Confirmaciones explícitas posteriores al mensaje; nunca un gracias del
    # gestor, una aprobación hipotética ni un «ok» sin mensaje al que responder.
    units=sentence_evidence(text,segments)
    for index,unit in enumerate(units):
        if not index or unit['speaker_role']in{'GESTOR','TITULAR'}:continue
        value=normalize(unit['text']).strip()
        if not re.fullmatch(r'(?:(?:ah|ok|si)[, ]+){0,2}(?:me parece bien|esta bien|claro que si)[.!]?',value):continue
        previous=normalize(units[index-1]['text'])
        if (units[index-1]['speaker_role']not in{'TERCERO','TITULAR','INTERLOCUTOR'}and re.search(
                r'\b(?:se (?:puede |pueda )?comunicar|se comunique|se contacte|comunicarse|contactarse)\b',previous)
                and phone_present(source)):
            result['acceptance'].append(dict(unit,method='CONFIRMA_RECEPCION_TRAS_MENSAJE_CON_CONTACTO',human_verified=False))
    return result


def accepted_callback_request(text,segments,acceptance):
    """Una solicitud aceptada cuyo propósito y teléfono sí se proporcionan.

    La forma interrogativa de ofrecer el recado no invalida el mensaje si el
    interlocutor lo recibe. No acredita parentesco ni identidad del titular.
    """
    if not acceptance or not callback_available(text,segments):return []
    source=normalize(text);found=[]
    pattern=re.compile(r'\b(?:(?:le )?(?:puedo|podria|podre|pudiera|podemos) (?:dejar(?:le)?|dictar(?:le)?|proporcionar(?:le)?)|(?:le )?(?:estaria|estoy) (?:otorgando|proporcionando|compartiendo)|le voy a (?:dejar|dar|compartir)) '
                       r'(?:(?:lo que es|lo que seria) )?(?:un |el )?(?:numero|telefono|recado|mensaje)'
                       r'[^.!?]{0,180}\bpara que\b[^.!?]{0,110}\b'
                       r'(?:se pueda comunicar|se puede comunicar|se comunique|se tiene que comunicar|se debe(?: de)? comunicar|pueda comunicarse|se contacte|se ponga en contacto|se pueda poner en contacto)\b')
    for match in pattern.finditer(source):
        if _role_at(text,segments,match.start())in{'TERCERO','TITULAR','INTERLOCUTOR'}:continue
        if re.search(r'\b(?:no|dijo que|dice que|diga que|repita que|por ejemplo|si)\s*$',source[max(0,match.start()-85):match.start()]):continue
        purpose=match.group().split('para que',1)[1]
        if not re.search(r'\b(?:el senor|la senora|la senorita|el titular|la titular|el caballero|ella|el)\b',purpose):continue
        if re.search(r'\bno (?:se |pueda )?(?:comunique|comunicar|contacte)\b',purpose):continue
        found.append({'text':match.group(),'method':'OFERTA_DE_RETORNO_ACEPTADA_Y_CONTACTO_DICTADO',
            'speaker_role':_role_at(text,segments,match.start()),'human_verified':False,
            'recipient_acceptance':[e.get('text','')for e in acceptance]})
    return found


def ready_after_note_wait(text,segments=()):
    source=normalize(text);found=[]
    pattern=re.compile(r'\b(?:(?:no se si )?tenga|tiene|tendra|tendria) (?:usted )?¿?(?:donde|con que) (?:anotar|apuntar|notar|escribir|tomar notas?)'
                       r'[^?!.]{0,55}[?.]\s*(?P<wait>(?:a ver[, ]+)?(?:permitame|espere|un momento|un segundito|dame un segundo)[^.!?]{0,35})[.!?]')
    for match in pattern.finditer(source):
        if _role_at(text,segments,match.start('wait'))in{'GESTOR','TITULAR'}:continue
        if BAD_PREFIX.search(source[max(0,match.start()-65):match.start()]):continue
        tail=source[match.end():match.end()+650]
        ready=re.search(r'\b(?:a ver(?:[, ]+(?:digame|demelo))?|listo|ya[, ]+(?:digame|lo tengo)|ahora si)\s*[.!?,]',tail[:180])
        if not ready or not phone_present(source[max(0,match.start()-400):match.end()+650]):continue
        if re.search(r'\bno (?:puedo|quiero|tengo (?:donde|con que))\b',tail[:ready.end()]):continue
        found.append({'text':match.group()+' '+tail[:ready.end()],
            'method':'ESPERA_Y_PREPARACION_CONFIRMADA_ANTES_DEL_DICTADO',
            'speaker_role':_role_at(text,segments,match.start('wait')),'start':None,'end':None,'human_verified':False})
    return found


def information_relay_acceptance(text,segments=()):
    # Aceptar que le dejen información no demuestra que se haya transmitido.
    if not callback_available(text,segments):return []
    source=normalize(text);found=[]
    pattern=re.compile(r'\b(?:cree que )?le (?:puedo|pueda|podria|pudiera) dejar (?:una |la |esta )(?:pequena )?informacion (?:a |con )usted'
                       r'[^?!.]{0,130}[?.]\s*(?P<answer>si|claro(?: que si)?|de acuerdo|esta bien)\b')
    for match in pattern.finditer(source):
        if not _answer_ok(text,segments,source,match):continue
        if re.search(r'\b(?:si cree que|por ejemplo|diga que|dice que)\s*$',source[max(0,match.start()-90):match.start()]):continue
        found.append(dict(_item(source,match,'ACEPTA_INFORMACION_PARA_OTRA_PERSONA',text,segments,'answer'),relay_purpose_confirmed=True))
    return found


def recipient_relay_with_callback(text,segments,acceptance):
    if not callback_available(text,segments):return False
    return any(re.search(r'\byo le (?:paso|doy|transmito|aviso) (?:el |su )?(?:recado|mensaje|razon|informacion)\b',normalize(e.get('text','')))
        for e in acceptance)


def existing_callback_confirmation(text,segments=()):
    """Contacto ya anotado o recibido y reconocido; no reconstruye su número."""
    source=normalize(text);found=[]
    possession=re.compile(r'\b(?P<answer>ya (?:lo |le )?(?:tengo|tenemos) anotado(?: aqui)?|ya (?:tengo|tenemos) (?:anotado )?(?:el |ese )numero)\b')
    for match in possession.finditer(source):
        before=source[max(0,match.start()-700):match.start()]
        if (_role_at(text,segments,match.start('answer'))in{'GESTOR','TITULAR'}
                or BAD_PREFIX.search(before[-70:])or not _outside_question(source,match.start(),match.end())):continue
        topics=list(re.finditer(r'\b(?:numero|telefono|saldo|monto|pesos|tarjeta|referencia)\b',before))
        if not topics or topics[-1].group()not in{'numero','telefono'}:continue
        if not MESSAGE.search(before):continue
        found.append(_item(source,match,'CONTACTO_PREVIAMENTE_ANOTADO_POR_RECEPTOR',text,segments,'answer'))
    recognised=re.compile(r'\b(?:es|a) (?:el |ese )numero que (?:a )?usted me dio\?\s*(?P<answer>asi es|si|correcto)\b')
    for match in recognised.finditer(source):
        before=source[max(0,match.start()-1500):match.start()]
        if not re.search(r'\b(?:numero telefonico|telefono|conmutador|numero para que se pueda comunicar)\b',before):continue
        if not MESSAGE.search(before):continue
        if re.match(r'\s*\?',source[match.end():])or re.search(r'\b(?:no|diga que|dice que|dijo que)\s*$',source[max(0,match.start()-70):match.start()]):continue
        if _role_at(text,segments,match.start('answer'))in{'TERCERO','TITULAR','INTERLOCUTOR'}:continue
        found.append(_item(source,match,'RECONOCE_CONTACTO_PROPORCIONADO_EN_EL_DIALOGO',text,segments))
    repeated=re.compile(r'\b(?P<answer>(?:si[, ]+)?(?:de hecho[, ]+)?es el mismo numero)\b')
    for match in repeated.finditer(source):
        before=source[max(0,match.start()-650):match.start()]
        if not re.search(r'\b(?:repetir|repita|corroborar|corrobora|anotar|nota|dictar|dictado)\b',before):continue
        if not MESSAGE.search(before)or not phone_present(before):continue
        if re.match(r'\s*(?:\?|de (?:la |su )?(?:tarjeta|cuenta|titular))',source[match.end():]):continue
        if _role_at(text,segments,match.start('answer'))in{'GESTOR','TITULAR'}or BAD_PREFIX.search(before[-70:]):continue
        found.append(_item(source,match,'RECONOCE_CONTACTO_REPETIDO_TRAS_DICTADO',text,segments,'answer'))
    return found


def callback_available(text,segments=()):
    return phone_present(text)or bool(existing_callback_confirmation(text,segments))


def callback_modal_instruction(text,segments=()):
    found=[]
    pattern=re.compile(r'\bse (?:tiene que|debe(?: de)?) comunicar\b')
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role']in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        value=normalize(unit['text'])
        for match in pattern.finditer(value):
            if re.search(r'\b(?:no|dice que|dijo que|diga que|si)\s*$',value[max(0,match.start()-65):match.start()]):continue
            found.append(dict(unit,phrase=match.group(),method='INSTRUCCION_MODAL_DE_RETORNO'))
    return found


def asks_to_hear_callback(text,segments=()):
    source=normalize(text);found=[]
    pattern=re.compile(r'\b(?P<answer>me (?:lo )?(?:puede|podria|pudiera) (?:decir|dictar)(?: (?:el|ese) numero)?)\s*[?.]')
    for match in pattern.finditer(source):
        before=source[max(0,match.start()-750):match.start()]
        if not _answer_ok(text,segments,source,match):continue
        topics=list(re.finditer(r'\b(?:numero|telefono|saldo|monto|importe|tarjeta|referencia)\b',before))
        if not topics or topics[-1].group()not in{'numero','telefono'}:continue
        if not re.search(r'\b(?:se (?:pueda |puede )?poner en contacto|se comunique|se pueda comunicar)\b',before):continue
        if not phone_present(source[max(0,match.start()-750):match.end()+550]):continue
        found.append(_item(source,match,'SOLICITA_ESCUCHAR_CONTACTO_OFRECIDO',text,segments,'answer'))
    return found


def negated_return_only(text):
    source=normalize(text)
    core=r'(?:se (?:pueda |puede )?comunicar|se comunique|pueda comunicarse|se contacte|se ponga en contacto|se pueda poner en contacto|se tiene que comunicar|se debe(?: de)? comunicar|(?:nos |me )?(?:llame|marque))'
    matches=list(re.finditer(r'\b'+core+r'\b',source));negative=[];positive=[]
    for match in matches:
        prefix=source[max(0,match.start()-60):match.start()]
        if re.search(r'\bno\s*$',prefix):negative.append(match)
        else:positive.append(match)
    return bool(negative and not positive)


def delivered_intermediary_message(text,segments,acceptance):
    """La dirección del recado y su recepción pueden estar en turnos distintos."""
    if not acceptance or not callback_available(text,segments)or negated_return_only(text):return []
    source=normalize(text);found=[]
    returning=bool(re.search(r'\b(?:se (?:pueda |puede )?comunicar|se comunique|se tiene que comunicar|se debe(?: de)? comunicar|comunicarse|se pueda poner en contacto|se ponga en contacto)\b',source))
    if not returning:return []
    pattern=re.compile(r'\b(?:le )?(?:puedo|podria|podre|pudiera|podemos|pueda) (?:dejar(?:le)?|dar(?:le)?) '
                       r'(?:un |el |algun |algun tipo de )?(?:recado|mensaje|mensajito|informacion)\b[^.!?]{0,160}'
                       r'\b(?:con usted|a usted|se lo (?:pueda |puede |pudiera )?(?:proporcione|proporcionar|pase|pasar|deje|comparta|compartir))\b')
    for match in pattern.finditer(source):
        if _role_at(text,segments,match.start())in{'TERCERO','TITULAR','INTERLOCUTOR'}:continue
        before=source[max(0,match.start()-80):match.start()]
        if re.search(r'\b(?:no|dijo que|dice que|diga que|repita que|por ejemplo|si)\s*$',before):continue
        found.append({'text':match.group(),'method':'RECADO_DIRIGIDO_A_INTERMEDIARIO_Y_RECIBIDO_CON_CONTACTO',
            'human_verified':False,'speaker_role':_role_at(text,segments,match.start())})
    return found
