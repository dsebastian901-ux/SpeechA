"""Identificación nominal y conversación propia según el criterio operativo del usuario."""
import re
import unicodedata

from app.services.conversation_evidence import normalize, sentence_evidence, _role_at, KIN


BAD_IDENTITY = re.compile(
    r'\b(?:familiar|espos[oa]|madre|padre|herman[oa]|referencia|quien|ustedes?|'
    r'banco|despacho|corporativo|cobranza|pago|deuda|cuenta|departamento|encargad[oa]|'
    r'tarjeta|dinero|cantidad|telefono|linea|numero|servicio|abogado)\b')
COUNTER = re.compile(
    r'\b(?:no soy (?:esa persona|ese senor|el titular|la titular)|'
    r'soy (?:su )?(?:espos[oa]|madre|padre|herman[oa]|hij[oa]|sobrin[oa]|familiar|referencia|amig[oa]|vecin[oa])|'
    r'es mi (?:espos[oa]|madre|padre|herman[oa]|hij[oa])|'
    r'no es mi (?:tarjeta|cuenta)|no (?:lo|la) conozco|no conocemos a|'
    r'no se encuentra(?: aqui| en casa| ahora)?(?=[.!?]|$)|no esta (?:aqui|en casa)|esta trabajando|'
    # Exigir pronombre completo o parentesco. «Hablo por su producto» y
    # «me habló por el mismo motivo» NO son declaraciones de intermediario.
    r'(?:pago|pague|pagar(?:lo|la)?|pagando|llamo|hablo) (?:por|a nombre de) '
    r'(?:ella\b|el(?=[,;.!?]|$)|(?:el |la )(?:titular|senor|senora|cliente)\b|'
    r'(?:mi |su )(?:espos[oa]|madre|padre|herman[oa]|hij[oa]|familiar)\b)|'
    r'(?:cuenta|tarjeta) de mi (?:espos[oa]|madre|padre|herman[oa]|hij[oa])|'
    r'(?:solicite|saque|tramite|contrate|adquiri) (?:la |una )?tarjeta (?:para|a nombre de) (?:ella|mi (?:espos[oa]|madre|padre|hij[oa]|herman[oa]))|'
    r'se lo comunico|le paso (?:al|con|a la)|lo busco|la busco)\b')
OWN_ACCOUNT = re.compile(
    r'\b(?:mi (?:tarjeta|cuenta|saldo|adeudo|deuda|credito|contrato|estado de cuenta|aplicacion|pago)|mis pagos|'
    r'yo (?:tengo|tenia|saque|solicite|tramite|contrate) (?:mi |la |una )?(?:tarjeta|cuenta)|'
    r'(?:(?:ya|yo) ){0,2}(?:lo pague|pague|hice (?:mi |el |un )?pago|realice (?:mi |el |un )?pago|he pagado|he depositado)|'
    r'me (?:bloquearon|cancelaron) (?:mi |la )?tarjeta|'
    r'no me la (?:podian|podia|pudieron) desbloquear|'
    r'(?:yo )?di (?:el |mi |un )?pago(?: inicial)?|'
    r'yo (?:pago|pagaba|iba a pagar|estoy pagando|estaba pagando|estuve pagando)|'
    r'(?:les|le) (?:depositaba|depositare|deposito|abonaba|abonare|abono|pagaba|pagare)|'
    r'(?:yo )?(?:quiero|me quiero|quisiera) (?:ponerme al corriente|poner al corriente mi cuenta)|'
    r'me (?:estan|siguen|han estado) cobrando|'
    r'(?:yo )?(?:tenia|tengo) que pagar|yo (?:se que debo|les debo)|lo que yo les debo|'
    r'(?:yo )?no estoy negad[oa] a pagar|'
    r'(?:ya |yo )?(?:lo hice|lo realice)|'
    r'(?:este|el) mes (?:yo )?(?:tengo|tenia) (?:un |el |mi )?pago minimo|'
    r'no (?:(?:te|le|les|lo) )?(?:voy a|pienso|quiero) (?:pagar|depositar)|yo no (?:les )?debo nada|(?:yo )?quiero pagar(?:lo|la)|(?:la |mi tarjeta la )?quiero (?:cancelar|dar de baja)|yo lo deje de pagar|por eso lo deje de pagar|'
    r'he (?:querido|intentado) (?:hacer|realizar) (?:una |la |mi )?transferencia|'
    r'no he podido (?:realizarlo|ir(?: porque| hasta))|'
    r'ya les digo si puedo o no|'
    r'ya tengo el (?:codigo|folio)(?=[^.!?]{0,80}cancelad)|'
    r'(?:yo )?(?:requeriria|necesito|quiero|requiero) que me (?:entreguen|den|envien) primero|'
    r'no les voy a completar|me (?:atrase|he atrasado)|'
    r'no he (?:usado|utilizado) (?:mi |la |esa |esta )?tarjeta|'
    r'(?:yo )?(?:ya )?(?:voy a pagar|voy a depositar|voy a abonar)|'
    r'(?:enseguida|ahorita|ahora(?: mismo)?) (?:hago|realizo) (?:el |mi )?pago|'
    r'no (?:he podido|pude) (?:hacer|realizar) (?:el |mi |un )pago|'
    r'(?:le|les) (?:voy a poder|puedo) (?:ahorita )?(?:dar|pagar|depositar|abonar) (?:los? |unos? )?(?:\d|mil|dos mil|tres mil|cuatro mil|cinco mil)|'
    r'(?:lo |le )?he podido realizar (?:el |mi )?pago|'
    r'no (?:lo |le )?he podido realizar(?:lo)?|'
    r'no lo he hecho|el contrato que (?:hicimos|hice|firme)|'
    r'(?:me gustaria|mi intencion es) (?:liquidar|pagar)|'
    r'no cuento con (?:esa|la) cantidad|no me niego a pagar|'
    r'no puedo (?:hacer|generar|formalizar) (?:un |algun )?convenio|'
    r'lo puedo (?:pagar|abonar|depositar)|'
    r'no (?:he podido|puedo|pude) (?:ir a )?(?:pagar|depositar|abonar|realizar (?:mi|el) pago))\b')


def valid_nominal_request(source, start, identity):
    """Una ausencia/ubicación no puede interpretarse como nombre solicitado."""
    name=re.sub(r'\b(?:senorita|senora|senor|caballero|perdon|disculpe|disculpa|digame|diganme|dime|por favor)\b',' ',identity)
    # La ruta histórica de confirmación directa «¿es usted?» valida su
    # respuesta por separado; una cortesía no vacía jamás es un nombre.
    if identity.strip() and not re.search(r'[a-z]{2,}',name):return False
    if re.search(r'\b'+KIN+r'\b',identity):return False
    if re.search(r'\b(?:aqui|ahi|alla|ahorita|actualmente|domicilio|casa|hospital|hospitalizado|internado|trabajando)\b',identity):
        return False
    prefix=source[max(0,start-80):start]
    return not re.search(r'\b(?:no|no se|ya no|dice que|dijo que|diga que|repita que)\s*$',prefix)


def nonholder_counter_evidence(text,segments=()):
    """Distinguir buscar a una persona de buscar la fecha de su propio pago."""
    source=normalize(text);found=[]
    for match in COUNTER.finditer(source):
        from app.services.speech_scope import personal_family_background
        if personal_family_background(source,match.start(),match.end()):continue
        role=_role_at(text,segments,match.start())
        if role=='GESTOR':continue
        from app.services.message_contact_evidence import _outside_question
        if not _outside_question(source,match.start(),match.end()):continue
        before=source[max(0,match.start()-160):match.start()]
        if re.search(r'\b(?:dice que|dijo que|diga que|repita que|por ejemplo|si fuera)\b[^.!?]{0,100}$',before):continue
        if match.group()=='esta trabajando'and not re.search(r'\b(?:el|ella|mi|su|no esta|no se encuentra)\b',before):continue
        if match.group()in{'lo busco','la busco'}:
            financial_search=re.search(r'\b(?:fecha|comprobante|recibo|folio|registro|pago realizado)\b',before)
            person_search=re.search(r'\b(?:comunicar con|se encuentra|hablo con|gusto con|busco a)\b[^.!?]{2,90}[.?][^.!?]{0,70}$',before)
            if financial_search and not person_search:continue
        found.append({'phrase':match.group(),'position':match.start(),'speaker_role':role})
    return found


def personal_financial_statement(value):
    """Autorreferencia financiera que identifica contexto, nunca una promesa firme."""
    source=normalize(value)
    expression=re.compile(r'\b(?:yo (?:creo que|pienso que) (?:la |lo )?(?:liquido|pago|cubro)|'
        r'(?:yo )?hago (?:el|mi|un) pago|'
        r'(?:yo )?voy a (?:saldar|liquidar|cubrir) (?:el |mi |la )?(?:total|saldo|cantidad|tarjeta|cuenta)|'
        r'(?:segun )?yo (?:ya )?(?:no (?:tenia|debia)|tenia) (?:nada|saldo|(?:ese |el |mi )?pago))\b')
    for match in expression.finditer(source):
        before=source[max(0,match.start()-100):match.start()]
        if re.search(r'\b(?:dice que|dijo que|diga|repita|supongamos|si tuviera|si fuera|cuando|para que)\b[^.!?]{0,65}$',before):continue
        return match
    return None


def own_marker_is_instruction(value,marker):
    """«Cuando lo realice» del gestor no es «yo lo realicé»."""
    before=normalize(value)[:marker.start()]
    if not re.search(r'\b(?:cuando|en cuanto|para que|si|que)(?: (?:usted|lo|le|se|ya)){0,3}\s*$',before):return False
    personal=marker.group().startswith(('mi ','mis ','me estan cobrando','me siguen cobrando','me han estado cobrando'))
    if personal:return False
    verbatim=re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(value)).lower()).strip()
    return not re.search(r'\b(?:pagué|realicé|hice)\b',verbatim[marker.start():marker.end()])


def proxy_account_evidence(text, segments=()):
    """Cuenta de otra persona declarada por el interlocutor; no certifica parentesco."""
    pattern=re.compile(r'\b(?:(?:le )?habl[ao] su (?:espos[oa]|herman[oa]|hij[oa]|madre|padre)|no[, ]+es su (?:espos[oa]|herman[oa]|hij[oa]|madre|padre)|(?:estados? de cuenta|cuenta|tarjeta) de (?:ella|el|la titular|el titular)|'
                       r'no esta ya[, ]+(?:pero )?digame)\b')
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role'] in {'GESTOR','TITULAR'}:continue
        value=normalize(unit['text'])
        for match in pattern.finditer(value):
            if '?' in value or re.search(r'\b(?:no|dijo que|dice que|diga que|si fuera)\s*$',value[:match.start()]):continue
            return True
    return False


def contextual_holder_confirmation(text, segments, identification):
    """No basta un sí, un agradecimiento, el Excel o la falta de parentesco.

    Se requieren pregunta nominal, respuesta afirmativa y declaración sobre
    la cuenta/pago propio. La voz conocida del gestor y los terceros no aportan
    esa declaración. No crea una confirmación humana ni diariza el audio.
    """
    source=normalize(text)
    none={'confirmed':False,'method':'SIN_CONTEXTO_NOMINAL_COMPLETO','evidence':''}
    from app.services.contact_evidence_graph import nonholder_context
    if proxy_account_evidence(text,segments) or nonholder_context(text,segments):return none
    explicit = re.search(r'\bcon (?:el senor|la senora|la senorita) (?P<identity>[a-z ]{3,85}?)\s*[,?.]?\s+(?P<answer>a sus ordenes|para servirle|su servidor|su servidora)\b',source)
    if explicit and valid_nominal_request(source,explicit.start(),explicit['identity']) and not BAD_IDENTITY.search(explicit['identity']) and _role_at(text,segments,explicit.start('answer')) not in {'GESTOR','TERCERO'}:
        return {'confirmed':True,'method':'IDENTIFICACION_NOMINAL_CON_RESPUESTA_DE_SERVICIO','evidence':explicit.group(),'speaker_role':'NO DETERMINADO','human_verified':False}
    named_self=re.compile(r'\b(?:busco (?:a |al |el |la )?|encuentro |encuentra |encuentre |se encuentra |me comunico con )(?P<identity>[^.!?]{3,100}?)(?:[.!?]\s*|\s+)(?P<answer>(?:si[, ]+)?(?:con ella habla|con el habla|ella habla|el habla))\b')
    for m in named_self.finditer(source):
        if (valid_nominal_request(source,m.start(),m['identity']) and not BAD_IDENTITY.search(m['identity'])
                and _role_at(text,segments,m.start('answer')) not in {'GESTOR','TERCERO'}
                and not re.match(r'\s*\?',source[m.end():])):
            return {'confirmed':True,'method':'RESPUESTA_EXPLICITA_A_BUSQUEDA_NOMINAL','evidence':m.group(),'human_verified':False,'speaker_role':'NO DETERMINADO'}
    requests=[
        re.compile(rf'\b{identification}\s+(?P<identity>[^.!?]{{2,100}}?)[.?]\s*(?P<answer>si[, ]+habla)[.!](?!\s*\?)'),
        re.compile(r'\b(?:cual es|es)\s+(?P<identity>(?:el senor|la senora|la senorita)\s+[^.!?]{3,75}?)\?\s*(?P<answer>si|asi es|correcto)\b'),
        re.compile(r'\b(?:usted es|es usted)\s+(?P<identity>[^.!?]{3,85}?)\?\s*(?P<answer>si|asi es|correcto)\b'),
        re.compile(r'\b(?:buenos dias|buenas dias|buenas tardes)[, .]*con\s+'
                   r'(?P<identity>[a-z ]{3,85}?) por favor[, .?]\s*(?P<answer>)'),
        re.compile(r'\bme (?:podre|podria|pudo|pude|he podido|voy a poder) (?:a )?(?:comunicar|comentar) (?:de favor )?con\s+'
                   r'(?P<identity>[^.!?]{2,100}?)[.!?]\s*(?P<answer>)'),
        re.compile(rf'\b{identification}\s+(?P<identity>[^.!?]{{2,100}}?)[.!?]\s*'
                   r'(?P<answer>si|asi es|correcto|aja)\b'),
        re.compile(r'\bcon\s+(?P<identity>(?:el senor|la senora|la senorita)\s+[^.!?]{2,90}?)[.?]\s*'
                   r'(?P<answer>(?:si[, ]+)?(?:servidor|servidora|al habla|ella habla|el habla|digame|diganme|dime)|si|asi es|correcto|aja)\b'),
        re.compile(rf'\b{identification}\s+(?P<identity>[^.!?]{{2,100}}?)(?:[.?]|,\s*gracias\b)\s*(?P<answer>)'),
        re.compile(r'\bcon\s+(?P<identity>(?:el senor|la senora|la senorita)\s+[^.!?]{2,90}?)(?:[.?]|,\s*gracias\b)\s*(?P<answer>)'),
        re.compile(rf'\b{identification}\s+(?P<identity>[^,.!?]{{3,90}}?),\s*'
                   r'(?=le marcamos|le (?:hablo|hablamos)|me (?:estoy comunicando|presento)|mi nombre es)'
                   r'(?P<answer>)'),
        re.compile(rf'\b{identification}\s+(?P<identity>[^.!?]{{3,90}}?)\s+'
                   r'(?=(?:no )?(?:me estoy comunicando|estoy comunicando|le marcamos|mi nombre es|me presento)\b)'
                   r'(?P<answer>)'),
    ]
    units=[];cursor=0
    for unit in sentence_evidence(text,segments):
        value=normalize(unit['text']);start=source.find(value,cursor)
        if start>=0:
            cursor=start+len(value);units.append((start,cursor,unit,value))
    for pattern in requests:
        for request in pattern.finditer(source):
            identity=request['identity']
            if not valid_nominal_request(source,request.start(),identity):continue
            if BAD_IDENTITY.search(identity) or re.search(r'\d|\b(?:que|cual|cuanto)\b',identity):continue
            person=re.sub(r'^(?:(?:el|la) )?(?:senorita|senora|senor|caballero)\s*','',identity).strip(', ')
            if not re.search(r'[a-z]{2,}',person):continue
            answer=request['answer']
            if request.start()>600 and not answer:continue
            prefix=source[max(0,request.start()-75):request.start()]
            if re.search(r'\b(?:dijo que|me dijo|me dijeron|diga que|repita que|el cliente dice|usted dijo|si alguien pregunta)\b',prefix):continue
            if answer and _role_at(text,segments,request.start('answer')) in {'GESTOR','TERCERO'}:continue
            after=source[request.end():request.end()+75]
            if re.search(r'\b(?:espere|permita|se lo comunico|lo busco|la busco|le paso|no esta)\b',after):continue
            if re.match(r'\s+(?:me espera|me permite|quiere|puede|necesita|consigo|tuviera)\b',after):continue
            if re.fullmatch(r'(?:si[, ]+)?(?:habla|servidor|servidora|al habla|ella habla|el habla|digame|diganme|dime)',answer):
                return {'confirmed':True,'method':'RESPUESTA_EXPLICITA_TRAS_NOMBRE_CON_TRATAMIENTO',
                        'evidence':request.group(),'speaker_role':'NO DETERMINADO'}
            for start,end,unit,value in units:
                if end<=request.end() or unit['speaker_role'] in {'GESTOR','TERCERO'}:continue
                if re.search(r'\b(?:yo soy|soy|hablo) (?:de |del |de la )?(?:cobranza|despacho|corporativo|juridico)\b',value):continue
                # Conservar solo declaraciones; una pregunta del gestor sobre
                # «mi pago» no demuestra autorreferencia del interlocutor.
                statement=re.sub(r'¿[^?]*\?', ' ',value).strip()
                if '?' in statement:statement=statement.rsplit('?',1)[-1].strip()
                if not statement:continue
                if re.search(r'\b(?:si tuviera|si tuviese|si yo tuviera|supongamos que|'
                             r'diga|digale|repita|usted dice|usted dijo|el cliente dice)\b',statement):continue
                if not re.search(r'\b(?:tarjeta|cuenta|pagos?|pagar|deposito|depositar|transferencia|saldo|cubierto|cubrir|cantidad|pesos)\b',
                                 source[max(request.end(),start-180):end]):continue
                own=OWN_ACCOUNT.search(statement)
                if not own:continue
                if own.group().startswith('ya les digo') and re.search(r'\b(?:whatsapp|numero|anotar|comprobante)\b',source[max(start-100,request.end()):start]):continue
                if 'entreguen' in own.group() or 'envien' in own.group() or 'que me den' in own.group():
                    if not re.search(r'\b(?:carta finiquito|carta convenio|carta de no adeudo)\b',source[max(request.end(),start-250):end]):continue
                before=statement[:own.start()]
                if re.search(r'\bse\s*$',before):continue
                conditional=re.search(r'\b(?:que|cuando|si|para que)(?:\s+(?:se|usted|yo|ya|lo|le|me)){0,3}\s*$',before)
                verbatim=re.sub(r'\s+',' ',unicodedata.normalize('NFC',unit['text']).lower()).strip()
                accented_past=re.search(r'\b(?:pagué|realicé)\b',verbatim[own.start():own.end()])
                # «Me dijeron que MI cuenta...» y «por qué ME están cobrando»
                # acreditan autorreferencia, sin certificar el saldo o el pago.
                # Las órdenes, voces conocidas e hipótesis se excluyen arriba.
                personal_financial_state=own.group().startswith(('mi ','mis ','me estan cobrando','me siguen cobrando','me han estado cobrando'))
                if conditional and not personal_financial_state and not accented_past and not re.search(r'\bes que\s*$',before) and not (re.search(r'\bsi yo\s*$',before) and own.group().startswith('no he usado')):continue
                return {'confirmed':True,'method':('IDENTIFICACION_NOMINAL_Y_CONVERSACION_PROPIA' if answer else
                                                   'AUTORREFERENCIA_FINANCIERA_TRAS_PREGUNTA_NOMINAL'),
                        'evidence':request.group()+' / '+unit['text'],
                        'speaker_role':unit['speaker_role'],
                        'policy_source':'CRITERIO_USUARIO_CONTEXTO_COMPLETO',
                        'human_verified':False}
            from app.services.dialogue_evaluation import scan_dialogue
            own_events = [e for e in scan_dialogue(text,segments)['events']
                          if (e['kind']=='OWN_FINANCES' or (e['kind']=='PENDING_DECISION' and 'antes de pagarlo' in e['phrase'])) and e['position']>=request.end()]
            if own_events:
                event=own_events[-1]
                return {'confirmed':True,'method':'CONTEXTO_NOMINAL_Y_HECHO_FINANCIERO_PROPIO',
                        'evidence':request.group()+' / '+event['evidence'],
                        'speaker_role':event['speaker_role'],'human_verified':False,
                        'event_id':event['id'],'policy_source':'CRITERIO_USUARIO_CONTEXTO_COMPLETO'}
            from app.services.conversation_evidence import payment_commitment
            commitment=payment_commitment(text,segments)
            commitment_text=normalize(commitment.get('evidence')or'')
            bare_reply=bool(re.search(r'\?\s*(?:si|claro|correcto|de acuerdo|esta bien)[.!]?$',commitment_text))
            substantive_commitment=not bare_reply or bool(re.search(r'\b(?:hoy|manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo|dia \d{1,2}|\d{2,}|mil|pesos)\b',commitment_text))
            if (commitment['accepted'] and substantive_commitment and source.find(normalize(commitment['evidence'])) >= request.end()
                    and re.search(r'\b(?:pago|pagar|deposito|monto)\b',commitment['evidence'])):
                return {'confirmed':True,'method':'PREGUNTA_NOMINAL_Y_CONFIRMACION_DE_PAGO_PROPIO',
                        'evidence':request.group()+' / '+commitment['evidence'],
                        'speaker_role':'NO DETERMINADO','human_verified':False,
                        'policy_source':'CRITERIO_USUARIO_CONTEXTO_COMPLETO'}
    return none
