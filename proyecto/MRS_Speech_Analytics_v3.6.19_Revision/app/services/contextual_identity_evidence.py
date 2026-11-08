"""Identificación nominal y conversación propia según el criterio operativo del usuario."""
import re
import unicodedata

from app.services.conversation_evidence import normalize, sentence_evidence, _role_at


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
    r'(?:pago|pague|pagar(?:lo|la)?|pagando|llamo|hablo) (?:por|a nombre de) (?:el|ella|mi |su )|'
    r'(?:cuenta|tarjeta) de mi (?:espos[oa]|madre|padre|herman[oa]|hij[oa])|'
    r'(?:solicite|saque|tramite|contrate|adquiri) (?:la |una )?tarjeta (?:para|a nombre de) (?:ella|mi (?:espos[oa]|madre|padre|hij[oa]|herman[oa]))|'
    r'se lo comunico|le paso (?:al|con|a la)|lo busco|la busco)\b')
OWN_ACCOUNT = re.compile(
    r'\b(?:mi (?:tarjeta|cuenta|saldo|estado de cuenta|aplicacion|pago)|mis pagos|'
    r'yo (?:tengo|tenia|saque|solicite|tramite|contrate) (?:mi |la |una )?(?:tarjeta|cuenta)|'
    r'(?:ya |yo )?(?:lo pague|pague|hice (?:mi|el) pago|realice (?:mi|el) pago|he pagado|he depositado)|'
    r'(?:ya |yo )?(?:lo hice|lo realice)|'
    r'(?:este|el) mes (?:yo )?(?:tengo|tenia) (?:un |el |mi )?pago minimo|'
    r'(?:yo )?quiero pagar(?:lo|la)|'
    r'he (?:querido|intentado) (?:hacer|realizar) (?:una |la |mi )?transferencia|'
    r'no he podido (?:realizarlo|ir(?: porque| hasta))|'
    r'ya les digo si puedo o no|'
    r'(?:yo )?(?:requeriria|necesito|quiero|requiero) que me (?:entreguen|den|envien) primero|'
    r'no les voy a completar|me (?:atrase|he atrasado)|'
    r'no he (?:usado|utilizado) (?:mi |la |esa |esta )?tarjeta|'
    r'(?:yo )?(?:ya )?(?:voy a pagar|voy a depositar|voy a abonar)|'
    r'(?:lo |le )?he podido realizar (?:el |mi )?pago|'
    r'no (?:lo |le )?he podido realizar(?:lo)?|'
    r'no lo he hecho|el contrato que (?:hicimos|hice|firme)|'
    r'(?:me gustaria|mi intencion es) (?:liquidar|pagar)|'
    r'no cuento con (?:esa|la) cantidad|no me niego a pagar|'
    r'lo puedo (?:pagar|abonar|depositar)|'
    r'no (?:he podido|puedo|pude) (?:ir a )?(?:pagar|depositar|abonar|realizar (?:mi|el) pago))\b')


def valid_nominal_request(source, start, identity):
    """Una ausencia/ubicación no puede interpretarse como nombre solicitado."""
    if re.search(r'\b(?:aqui|ahi|alla|ahorita|actualmente|domicilio|casa|hospital|hospitalizado|internado|trabajando)\b',identity):
        return False
    prefix=source[max(0,start-80):start]
    return not re.search(r'\b(?:no|no se|ya no|dice que|dijo que|diga que|repita que)\s*$',prefix)


def proxy_account_evidence(text, segments=()):
    """Cuenta de otra persona declarada por el interlocutor; no certifica parentesco."""
    pattern=re.compile(r'\b(?:(?:estados? de cuenta|cuenta|tarjeta) de (?:ella|el|la titular|el titular)|'
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
    if COUNTER.search(source) or proxy_account_evidence(text,segments):return none
    explicit = re.search(r'\bcon (?:el senor|la senora|la senorita) (?P<identity>[a-z ]{3,85}?)\s*[,?.]?\s+(?P<answer>a sus ordenes|para servirle|su servidor|su servidora)\b',source)
    if explicit and valid_nominal_request(source,explicit.start(),explicit['identity']) and not BAD_IDENTITY.search(explicit['identity']) and _role_at(text,segments,explicit.start('answer')) not in {'GESTOR','TERCERO'}:
        return {'confirmed':True,'method':'IDENTIFICACION_NOMINAL_CON_RESPUESTA_DE_SERVICIO','evidence':explicit.group(),'speaker_role':'NO DETERMINADO','human_verified':False}
    requests=[
        re.compile(r'\b(?:buenos dias|buenas dias|buenas tardes)[, .]*con\s+'
                   r'(?P<identity>[a-z ]{3,85}?) por favor[, .?]\s*(?P<answer>)'),
        re.compile(r'\bme (?:podre|podria|pudo|pude|he podido|voy a poder) (?:a )?(?:comunicar|comentar) (?:de favor )?con\s+'
                   r'(?P<identity>[^.!?]{2,100}?)[.?]\s*(?P<answer>)'),
        re.compile(rf'\b{identification}\s+(?P<identity>[^.!?]{{2,100}}?)[.?]\s*'
                   r'(?P<answer>si|asi es|correcto|aja)\b'),
        re.compile(r'\bcon\s+(?P<identity>(?:el senor|la senora|la senorita)\s+[^.!?]{2,90}?)[.?]\s*'
                   r'(?P<answer>(?:si[, ]+)?(?:servidor|servidora|al habla|ella habla|el habla|digame|diganme|dime)|si|asi es|correcto|aja)\b'),
        re.compile(rf'\b{identification}\s+(?P<identity>[^.!?]{{2,100}}?)(?:[.?]|,\s*gracias\b)\s*(?P<answer>)'),
        re.compile(r'\bcon\s+(?P<identity>(?:el senor|la senora|la senorita)\s+[^.!?]{2,90}?)(?:[.?]|,\s*gracias\b)\s*(?P<answer>)'),
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
            if BAD_IDENTITY.search(identity) or re.search(r'\d',identity):continue
            person=re.sub(r'^(?:(?:el|la) )?(?:senorita|senora|senor|caballero)\s*','',identity).strip(', ')
            if not re.search(r'[a-z]{2,}',person):continue
            answer=request['answer']
            if request.start()>600 and not answer:continue
            prefix=source[max(0,request.start()-75):request.start()]
            if re.search(r'\b(?:dijo que|me dijo|el cliente dice|usted dijo|si alguien pregunta)\b',prefix):continue
            if answer and _role_at(text,segments,request.start('answer')) in {'GESTOR','TERCERO'}:continue
            after=source[request.end():request.end()+75]
            if re.search(r'\b(?:espere|permita|se lo comunico|lo busco|la busco|le paso|no esta)\b',after):continue
            if re.match(r'\s+(?:me espera|me permite|quiere|puede|necesita|consigo|tuviera)\b',after):continue
            if pattern is requests[3] and answer not in {'si','asi es','correcto','aja'}:
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
                if conditional and not accented_past and not re.search(r'\bes que\s*$',before) and not (re.search(r'\bsi yo\s*$',before) and own.group().startswith('no he usado')):continue
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
            if (commitment['accepted'] and source.find(normalize(commitment['evidence'])) >= request.end()
                    and re.search(r'\b(?:pago|pagar|deposito|monto)\b',commitment['evidence'])):
                return {'confirmed':True,'method':'PREGUNTA_NOMINAL_Y_CONFIRMACION_DE_PAGO_PROPIO',
                        'evidence':request.group()+' / '+commitment['evidence'],
                        'speaker_role':'NO DETERMINADO','human_verified':False,
                        'policy_source':'CRITERIO_USUARIO_CONTEXTO_COMPLETO'}
    return none
