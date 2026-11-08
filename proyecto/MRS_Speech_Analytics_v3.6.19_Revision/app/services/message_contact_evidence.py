"""Relación y recepción del recado mediante respuestas locales de la conversación.

No utiliza nombres, filas, estatus Excel ni IDs de hablante como prueba de voz.
"""
import re
from app.services.conversation_evidence import normalize, sentence_evidence, _role_at, KIN

BAD_PREFIX = re.compile(r'\b(?:no|no es|no soy|no era|no se si|creo que|tal vez|quizas|'
                        r'diga que|dijo que|dice que|repita que|gracias por|si fuera|si fuese)\s*$')
MESSAGE = re.compile(r'\b(?:recado|mensaje|mensajito|que (?:se comunique|(?:le |nos |me )?(?:marque|llame))|'
                     r'(?:se|pueda) comunicar|se comunique|se tiene que comunicar|se debe(?: de)? comunicar|se contacte|se ponga en contacto|se pueda poner en contacto|se puede poner en contacto|contactarse|comunicarse|para que (?:el|ella))\b')


def _recipient(text, segments, position):
    return _role_at(text, segments, position) not in {'GESTOR', 'TITULAR'}


def _outside_question(source, start, end):
    left=max(source.rfind(c,0,start) for c in '.!?¿,;')
    right=min((p for c in '.!?¿,;' if (p:=source.find(c,end))>=0),default=len(source))
    return not ((left>=0 and source[left]=='¿') or (right<len(source) and source[right]=='?')
                or re.match(r'\s*[,;]?\s*¿?(?:verdad|correcto|cierto)\b',source[end:]))


def _item(source, match, method, text, segments, key=None):
    position=match.start(key) if key else match.start()
    return {'text':match.group(),'phrase':match[key] if key else match.group(),
            'method':method,'speaker_role':_role_at(text,segments,position),
            'start':None,'end':None,'human_verified':False}


def message_contact_evidence(text,segments=()):
    source=normalize(text)
    result={'family':[],'acceptance':[],'third_party_relationships':[], 'work_relationships':[]}
    # La pregunta que sigue a una coma no convierte «es mi madre» en pregunta.
    declaration=re.compile(r'\b(?:(?:soy|era) (?:su |un |una )?familiar|soy su '+KIN+r'|(?:es|era) mi '+KIN+r')\b')
    for match in declaration.finditer(source):
        if (_recipient(text,segments,match.start()) and _outside_question(source,match.start(),match.end())
                and not BAD_PREFIX.search(source[max(0,match.start()-65):match.start()])):
            result['family'].append(_item(source,match,'DECLARACION_LOCAL_PARENTESCO',text,segments))
    relation=re.compile(r'\bque (?:relacion|parentesco|parentezco)\b[^?!.]{0,110}[?.]\s*'
                        r'(?P<answer>(?:(?:con |de |soy |es )?(?:mi|su) )?'+KIN+r')\b')
    for match in relation.finditer(source):
        if (_recipient(text,segments,match.start('answer'))
                and not re.match(r'\s*\?',source[match.end():])
                and not BAD_PREFIX.search(source[max(0,match.start()-60):match.start()])):
            result['family'].append(_item(source,match,'RESPUESTA_A_RELACION',text,segments,'answer'))
    family_reply=re.compile(r'\b(?:es (?:usted )?(?:su )?familiar|es familiar del (?:senor|titular)|es familiar de la (?:senora|titular))\b[^?!.]{0,85}[?.]\s*(?P<answer>'+KIN+r')\b')
    for match in family_reply.finditer(source):
        if (_recipient(text,segments,match.start('answer')) and not re.match(r'\s*\?',source[match.end():])
                and not BAD_PREFIX.search(source[max(0,match.start()-65):match.start()])):
            result['family'].append(_item(source,match,'RESPUESTA_PARENTESCO_A_PREGUNTA_FAMILIAR',text,segments,'answer'))
    confirmed_kin=re.compile(r'\bes (?:usted )?su (?P<kin>'+KIN+r')(?:[, ]+no)?[?.]\s*(?P<answer>si|asi es|correcto)\b')
    for match in confirmed_kin.finditer(source):
        if (_recipient(text,segments,match.start('answer')) and not re.match(r'\s*\?',source[match.end():])
                and not re.search(r'\b(?:creo|tal vez|quizas|puede ser|no se|supongo|pero no)\b',source[match.end():match.end()+45].split('.')[0])
                and not BAD_PREFIX.search(source[max(0,match.start()-65):match.start()])):
            result['family'].append(_item(source,match,'CONFIRMA_PREGUNTA_DE_PARENTESCO',text,segments,'kin'))
    work=re.compile(r'\b(?:soy (?:su |una? )?compan(?:ero|era) de trabajo|'
                    r'soy (?:un|una) (?:conocid[oa]|amig[oa]|vecin[oa])|(?:es|era) mi (?:compan(?:ero|era) de trabajo|vecin[oa]|conocid[oa]))\b')
    for match in work.finditer(source):
        if (_recipient(text,segments,match.start()) and _outside_question(source,match.start(),match.end())
                and not BAD_PREFIX.search(source[max(0,match.start()-60):match.start()])):
            target='work_relationships' if 'trabajo' in match.group() else 'third_party_relationships'
            result[target].append(_item(source,match,'RELACION_EXPLICITA_EN_CONVERSACION',text,segments))
    bare_work=re.compile(r'\b(?:que es usted|que (?:relacion|parentesco)\b)[^?!.]{0,95}[?.]\s*'
                         r'(?P<answer>(?:(?:mi|su) )?compan(?:ero|era) de(?:l)? trabajo)\b')
    for match in bare_work.finditer(source):
        if _recipient(text,segments,match.start('answer')) and not re.match(r'\s*\?',source[match.end():]):
            result['work_relationships'].append(_item(source,match,'RESPUESTA_CONTACTO_TRABAJO',text,segments,'answer'))
    listed_relation=re.compile(r'\b(?:conocid[oa]|amig[oa])[, ]+(?:amig[oa][, ]+)?familiar[?.]\s*'
                               r'(?P<answer>(?:es )?mi '+KIN+r'|(?:soy )?su '+KIN+r')\b')
    for match in listed_relation.finditer(source):
        if (_recipient(text,segments,match.start('answer'))
                and not re.match(r'\s*\?',source[match.end():])
                and not BAD_PREFIX.search(source[max(0,match.start()-55):match.start()])):
            result['family'].append(_item(source,match,'RESPUESTA_A_LISTA_DE_RELACIONES',text,segments,'answer'))
    # Recepción demostrada por petición de dictado y un mensaje real cercano.
    note=re.compile(r'\b(?:tiene|tienes|tendra|tendria) (?:usted )?'
                    r'(?:donde (?:anotar|a notar|notar|apuntar|tomar nota)|con que (?:anotar|a notar|notar|apuntar))'
                    r'[^?!.]{0,85}[?.]\s*'
                    r'(?:(?:me indica|me dice)[, ]*(?:por favor)?[,.? ]+)?'
                    r'(?P<answer>si(?:[, ]+(?:claro|digame|diganme))?|aja|claro(?: que si)?|a ver[, ]+digame)\b')
    for match in note.finditer(source):
        nearby=source[max(0,match.start()-400):match.end()+700]
        if (MESSAGE.search(nearby) and _recipient(text,segments,match.start('answer'))
                and not BAD_PREFIX.search(source[max(0,match.start()-60):match.start()])
                and not re.match(r'\s*\?',source[match.end():])
                and not re.search(r'\b(?:pero no|no puedo|no quiero|no le voy)\b',source[match.end():match.end()+75])):
            result['acceptance'].append(_item(source,match,'ACEPTA_ANOTAR_CONTACTO_PARA_RECADO',text,segments,'answer'))
    from app.services.payment_reference_validation import callback_numbers
    offers=list(re.finditer(r'\b(?:le (?:voy a )?(?:dejar|dictar)|le (?:dejo|puedo dejar|puedo dictar|puedo proporcionar|quiero proporcionar|dejare)|'
                             r'puedo dejarle)\b[^.!?]{0,80}\b(?:numero|telefono|recado|mensaje)\b',source))
    dictate=re.compile(r'\b(?P<answer>(?:me lo |lo )?dicta(?: por favor)?|'
                       r'digame (?:usted )?el numero(?: por favor)?|si[, ]+diga(?:me|nme)|a ver[, ]+(?:diga(?:me|melo|nmelo)|dime))\b')
    written=re.compile(r'\b(?P<answer>(?:si[, ]+)?ya (?:lo (?:anote|apunte|tengo)|quedo anotado)|'
                       r'(?:yo )?le (?:digo|comento|aviso)(?: en cuanto (?:llegue|regrese))?)\b')
    for pattern,method in [(dictate,'PIDE_DICTADO_DEL_CONTACTO'),(written,'CONFIRMA_ANOTACION_O_AVISO')]:
        for match in pattern.finditer(source):
            before=source[max(0,match.start()-650):match.start()]
            nearby=before+source[match.start():match.end()+700]
            if not MESSAGE.search(nearby) or not _recipient(text,segments,match.start('answer')):continue
            if BAD_PREFIX.search(before[-65:]) or re.search(r'\b(?:diga|digale|repita|gracias por)\b[^.!?]{0,50}$',before):continue
            if pattern is written and not _outside_question(source,match.start(),match.end()):continue
            if pattern is written:
                from app.services.message_dialogue_evidence import agent_continuation
                if agent_continuation(source,match.start(),match.end()):continue
            if pattern is dictate and not any(0<=match.start()-o.end()<=650 for o in offers):continue
            if pattern is dictate and re.match(r'\s*(?:usted )?(?:que|cuanto|de que|por que|cual)\b',source[match.end():]):continue
            if pattern is dictate and not (callback_numbers(nearby) or callback_dictation_fragments(nearby)):continue
            result['acceptance'].append(_item(source,match,method,text,segments,'answer'))
    receive=re.compile(r'\b(?P<answer>(?:digame|paseme) (?:el |la |un |una )?(?:recado|mensaje|razon)(?: por favor)?)\b')
    for match in receive.finditer(source):
        before=source[max(0,match.start()-65):match.start()]
        if (_recipient(text,segments,match.start('answer')) and _outside_question(source,match.start(),match.end())
                and not BAD_PREFIX.search(before)
                and not re.search(r'\b(?:diga|digale|repita|gracias por)\b[^.!?]{0,40}$',before)):
            result['acceptance'].append(_item(source,match,'SOLICITA_RECIBIR_EL_RECADO',text,segments,'answer'))
    note_ack=re.compile(r'\b(?:tiene|puede|puedes) (?:usted )?(?:donde (?:anotar|apuntar|tomar nota)|tomar nota)\b[^?!.]{0,50}[?.]\s*(?P<answer>a ver)[.!]')
    for match in note_ack.finditer(source):
        nearby=source[max(0,match.start()-350):match.end()+550]
        if (_recipient(text,segments,match.start('answer')) and MESSAGE.search(nearby)
                and not BAD_PREFIX.search(source[max(0,match.start()-65):match.start()])
                and (callback_numbers(nearby) or callback_dictation_fragments(nearby))):
            result['acceptance'].append(_item(source,match,'ACEPTA_DICTADO_Y_CONTACTO_DETECTADO',text,segments,'answer'))
    confirm_work=re.compile(r'\b(?:es (?:su )?compan(?:ero|era) de(?:l)? trabajo|trabaja (?:con el|con ella|conmigo))\?\s*(?P<answer>si|asi es|correcto)\b')
    for match in confirm_work.finditer(source):
        if (_recipient(text,segments,match.start('answer'))
                and not re.match(r'\s*\?',source[match.end():])
                and not BAD_PREFIX.search(source[max(0,match.start()-60):match.start()])):
            result['work_relationships'].append(_item(source,match,'CONFIRMA_CONTACTO_DE_TRABAJO',text,segments,'answer'))
    return result


def directed_relay_message(text,segments=()):
    """Una instrucción de retorno dirigida a otra persona, sin atribuir voz."""
    result=[]
    pattern=re.compile(r'\b(?:digale|diganle|indique(?:le|nle)?|mencione(?:le)?|'
                       r'le puede mencionar|le puede indicar|le dice)\b'
                       r'[^.!?]{0,150}\b(?:se comunique|pueda comunicarse|se pueda comunicar|'
                       r'se contacte|se ponga en contacto|se pueda poner en contacto|se puede poner en contacto|contactarse|(?:nos |me |le )?(?:llame|marque))\b')
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role'] in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        value=normalize(unit['text'])
        for match in pattern.finditer(value):
            if re.search(r'\bno (?:se )?(?:comunique|contacte|ponga en contacto|llame|marque)\b',match.group()):continue
            before=value[max(0,match.start()-65):match.start()]
            if re.search(r'\b(?:no|dice que|dijo que|diga que|repita que|supongamos que|si pudiera)\s*$',before):continue
            # Una solicitud del cliente o una hipótesis no es mensaje dejado.
            left=max(value.rfind(c,0,match.start()) for c in '.!?¿')
            right=min((p for c in '.!?¿' if (p:=value.find(c,match.end()))>=0),default=len(value))
            if (left>=0 and value[left]=='¿') or (right<len(value) and value[right]=='?'):continue
            result.append(dict(unit,phrase=match.group(),method='INSTRUCCION_DE_RETORNO_PARA_TERCERO',human_verified=False))
    return result


def unfinished_callback_offer(text,segments=()):
    """Prometer dictar el contacto no demuestra que se haya proporcionado."""
    from app.services.payment_reference_validation import callback_numbers
    source=normalize(text)
    from app.services.message_dialogue_evidence import negated_return_only
    if negated_return_only(text):
        return {'review_required':True,'reason':'El retorno aparece negado sin una instrucción positiva alternativa; revisar el mensaje.','evidence':[]}
    offers=[]
    negative=re.search(r'\bno (?:se )?(?:comunique|contacte|ponga en contacto|llame|marque)\b',source)
    positive=re.search(r'(?<!no )\b(?:se comunique|se tiene que comunicar|se debe(?: de)? comunicar|se contacte|se ponga en contacto|(?:que |para que )(?:ella |el )?(?:nos |me )?(?:llame|marque))\b',source)
    if negative and not positive:
        return {'review_required':True,'reason':'La instrucción de retorno está negada en la transcripción; no se certifica un recado positivo.','evidence':[{'text':negative.group(),'method':'RETORNO_NEGADO_EN_TRANSCRIPCION'}]}
    pattern=re.compile(r'\b(?:le (?:voy a|puedo|podria|pudiera|quiero) (?:dejar|dictar|proporcionar|compartir|dar|otorgar)|'
                       r'le (?:dejare|dejo|dictaria|dejaria|daria|proporcionare|proporciono|estaria dejando)|seria (?:dejarle|dictarle))\b[^.!?]{0,60}\b(?:numero|telefono)\b')
    for match in pattern.finditer(source):
        if _role_at(text,segments,match.start()) in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        if BAD_PREFIX.search(source[max(0,match.start()-65):match.start()]):continue
        offers.append(match)
    for match in re.finditer(r'\b(?:al|el) siguiente numero(?: telefonico| de telefono)?\b',source):
        if _role_at(text,segments,match.start())not in {'TITULAR','TERCERO','INTERLOCUTOR'}:
            if not BAD_PREFIX.search(source[max(0,match.start()-65):match.start()]):offers.append(match)
    directed_phone = (r'\b(?:tiene|tendra|tenga) (?:usted )?(?:donde|con que) (?:anotar|a notar|notar|apuntar)'
                      r'[^.!?]{0,65}\bnumero\b')
    for match in re.finditer(directed_phone,source):
        if _role_at(text,segments,match.start())not in {'TITULAR','TERCERO','INTERLOCUTOR'}:
            if not BAD_PREFIX.search(source[max(0,match.start()-65):match.start()]):offers.append(match)
    for match in re.finditer(r'\bse lo voy dictando\b',source):
        if re.search(r'\b(?:numero|telefono)\b',source[max(0,match.start()-850):match.start()]):offers.append(match)
    none={'review_required':False,'reason':'','evidence':[]}
    # Si la llamada acaba durante un dictado interrogativo, los ecos del
    # mismo fragmento no convierten el contacto parcial en entrega completa.
    partial_note=re.search(r'\b(?:tiene|tendra|tenga) (?:usted )?(?:donde|con que) (?:anotar|notar|apuntar|tomar nota)\s*[?.]',source)
    if partial_note and re.search(r'\d',source[partial_note.end():]) and source.rstrip().endswith('?'):
        if not callback_numbers(source) and not callback_dictation_fragments(source):offers.append(partial_note)
    if not offers:return none
    from app.services.message_dialogue_evidence import existing_callback_confirmation
    if existing_callback_confirmation(text,segments):return none
    if callback_numbers(source) or callback_dictation_fragments(source):return none
    if re.search(r'\b(?:aqui lo tengo|ya lo tengo anotado|tengo (?:aqui |anotado )el numero)\b',source) and not re.search(r'\b(?:no lo tengo|lo tengo en (?:la |mi )?casa)\b',source):return none
    return {'review_required':True,'reason':'Se ofreció dictar un contacto, pero no se detectó que se proporcionara ni que ya estuviera disponible.',
            'evidence':[{'text':m.group(),'method':'OFERTA_CONTACTO_SIN_ENTREGA_DETECTADA'} for m in offers]}


def callback_dictation_fragments(text):
    """Detectar dictado/eco en contexto telefónico sin reconstruir un teléfono.

    El contador incluye las repeticiones verbales: NO certifica diez dígitos
    distintos ni valida cuál es el número. Solo acredita que hubo dictado.
    """
    from app.services.payment_reference_validation import TOKEN, _digits
    source=normalize(text);found=[]
    callback_token=re.compile(TOKEN.pattern+r'|(?<!\w)(?:veinticiete|veintitos|cincoenta(?: y (?:uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve))?|secenta)(?!\w)')
    gap=re.compile(r'[\s,.?¿!¡:;-]*(?:(?:aja|aha|ah|si|es|el|y|correcto|perdon|ok|no|como|a ver|se lo repito|nuevamente|lo repito|corroboro)[\s,.?¿!¡:;-]*)*')
    for cue in re.finditer(r'\b(?:numero(?: de (?:telefono|contacto)| telefonico)?|telefono)\b',source):
        before=source[max(0,cue.start()-80):cue.start()]
        if re.search(r'\b(?:no (?:le )?(?:voy a|puedo|quiero) (?:dar|dictar|dejar)|diga que|dice que|por ejemplo)\b',before):continue
        tail=source[cue.end():cue.end()+420];tokens=list(callback_token.finditer(tail))
        if not tokens or tokens[0].start()>180:continue
        if re.search(r'\b(?:tarjeta|terminacion|saldo|pesos|folio|referencia|fecha|mensualidades|pago)\b',tail[:tokens[0].start()]):continue
        groups=[[tokens[0]]]
        for token in tokens[1:]:
            if gap.fullmatch(tail[groups[-1][-1].end():token.start()]):groups[-1].append(token)
            else:groups.append([token])
        for group in groups:
            # Una corrección y un nuevo dictado pueden aparecer después del primero.
            prefix=tail[:group[0].start()]
            if re.search(r'\b(?:tarjeta|terminacion|saldo|pesos|folio|referencia|fecha|mensualidades|pago)\b',prefix):continue
            values=[_digits(t.group()) for t in group]
            uncertain=[t.group()for t,v in zip(group,values)if v is None]
            units=sum(len(v)if v is not None else 2 for v in values)
            collapsed=[]
            for token in group:
                value=token.group()
                if not collapsed or collapsed[-1]!=value:collapsed.append(value)
            without_adjacent_echoes=sum(len(_digits(v))if _digits(v)is not None else 2 for v in collapsed)
            if len(group)<3 or units<10 or without_adjacent_echoes<10:continue
            found.append({'text':tail[group[0].start():group[-1].end()],
                          'method':'DICTADO_TELEFONICO_CON_ECOS_SIN_RECONSTRUCCION',
                          'contact_digits_verified':False,'distinct_digits_count_known':False,'uncertain_number_words':uncertain})
    return found


def callback_permission_evidence(text,segments=()):
    """Aceptación de dictar/dejar el contacto, con propósito y entrega separados."""
    source=normalize(text);found=[]
    prompts=(
        r'(?:(?:le )?(?:puedo|podria|podre|pudiera|podemos) (?:(?:entonces|por favor|de favor) )?(?:dejar(?:le)?|dar(?:le)?|dictar(?:le)?|proporcionar(?:le)?) '
        r'(?:(?:lo que es|lo que seria) )?(?:(?:un|el|algun) )?(?:recado|mensaje|numero)[^?!.]{0,150}|'
        r'(?:le )?(?:puedo|podria|podre|pudiera) dejar[^?!.]{0,60}\b(?:un |el )numero (?:telefonico|de telefono|de llamada)[^?!.]{0,100}|'
        r'(?:me )?permite (?:dejarle|dictarle|proporcionarle) (?:un |el )numero[^?!.]{0,100}|'
        r'le dejo (?:un |el )numero[^?!.]{0,100}|'
        r'(?:lo |le )?(?:puede|podria|puedes|pudiera) (?:usted )?(?:anotar(?:lo)?|apuntar(?:lo)?|tomar nota)[^?!.]{0,80}|'
        r'(?:me )?(?:puede|podria|puedes) (?:usted )?(?:anotar|apuntar) (?:un |el )?numero[^?!.]{0,85}|'
        r'(?:tiene|tienen|tienes|tendra) (?:usted )?(?:donde|con que) (?:anotar|a notar|notar|apuntar|tomar notas?)[^?!.]{0,85})'
    )
    pattern=re.compile(r'\b(?P<prompt>'+prompts+r')[?.]\s*'
                       r'(?:(?:me indica|me dice)[, ]*(?:por favor)?[,.? ]+)?'
                       r'(?P<answer>(?:(?:eh|ah)[, ]+)?(?:(?:si[, ]+)?(?:claro(?: que si)?|de acuerdo|esta bien|ok)|si(?:[, ]+si)?|aja|listo|a ver[, ]+(?:digame|dime)))\b')
    for match in pattern.finditer(source):
        if not _recipient(text,segments,match.start('answer')):continue
        before=source[max(0,match.start()-65):match.start()]
        if re.search(r'\b(?:no|dice que|dijo que|diga que|repita que|por ejemplo|supongamos que|si)(?: le)?\s*$',before):continue
        tail=source[match.end():match.end()+85]
        if re.match(r'\s*\?',tail) or re.search(r'\b(?:pero no|no puedo|no quiero|no le voy|solo si)\b',tail):continue
        nearby=source[max(0,match.start()-400):match.end()+900]
        if not MESSAGE.search(nearby):continue
        relay=bool(re.search(r'\b(?:con usted|se lo (?:pueda |puede |podria |pudiera )?(?:proporcione|proporcionar|pase|pasar|comparta|compartir)|'
                             r'(?:cuando|en cuanto) (?:se encuentre|llegue|regrese)|para (?:el titular|la titular|ella|el senor|la senora))\b',match['prompt']))
        record=_item(source,match,'ACEPTA_DICTADO_O_RECADO_POR_PREGUNTA_DIRECTA',text,segments,'answer')
        record['relay_purpose_confirmed']=relay
        found.append(record)
    return found
