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
    r'(?:yo )?quiero pagar(?:lo|la)|no les voy a completar|me (?:atrase|he atrasado)|'
    r'no he (?:usado|utilizado) (?:mi |la |esa |esta )?tarjeta|'
    r'(?:yo )?(?:ya )?(?:voy a pagar|voy a depositar|voy a abonar)|'
    r'no (?:he podido|puedo|pude) (?:ir a )?(?:pagar|depositar|abonar|realizar (?:mi|el) pago))\b')


def contextual_holder_confirmation(text, segments, identification):
    """No basta un sí, un agradecimiento, el Excel o la falta de parentesco.

    Se requieren pregunta nominal, respuesta afirmativa y declaración sobre
    la cuenta/pago propio. La voz conocida del gestor y los terceros no aportan
    esa declaración. No crea una confirmación humana ni diariza el audio.
    """
    source=normalize(text)
    none={'confirmed':False,'method':'SIN_CONTEXTO_NOMINAL_COMPLETO','evidence':''}
    if COUNTER.search(source):return none
    requests=[
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
            if pattern is requests[1] and answer not in {'si','asi es','correcto','aja'}:
                return {'confirmed':True,'method':'RESPUESTA_EXPLICITA_TRAS_NOMBRE_CON_TRATAMIENTO',
                        'evidence':request.group(),'speaker_role':'NO DETERMINADO'}
            for start,end,unit,value in units:
                if end<=request.end() or unit['speaker_role'] in {'GESTOR','TERCERO'}:continue
                # Conservar solo declaraciones; una pregunta del gestor sobre
                # «mi pago» no demuestra autorreferencia del interlocutor.
                statement=value.split('¿',1)[0].strip() if '¿' in value else value
                if not statement or '?' in statement:continue
                if re.search(r'\b(?:si tuviera|si tuviese|si yo tuviera|supongamos que|'
                             r'diga|digale|repita|usted dice|usted dijo|el cliente dice)\b',statement):continue
                if not re.search(r'\b(?:tarjeta|cuenta|pagos?|pagar|deposito|depositar|saldo|cubierto|cubrir|cantidad|pesos)\b',
                                 source[max(request.end(),start-180):end]):continue
                own=OWN_ACCOUNT.search(statement)
                if not own:continue
                before=statement[:own.start()]
                if re.search(r'\bse\s*$',before):continue
                conditional=re.search(r'\b(?:que|cuando|si|para que)(?:\s+(?:se|usted|yo|ya|lo|le|me)){0,3}\s*$',before)
                verbatim=re.sub(r'\s+',' ',unicodedata.normalize('NFC',unit['text']).lower()).strip()
                accented_past=re.search(r'\b(?:pagué|realicé)\b',verbatim[own.start():own.end()])
                if conditional and not accented_past and not re.search(r'\bes que\s*$',before):continue
                return {'confirmed':True,'method':('IDENTIFICACION_NOMINAL_Y_CONVERSACION_PROPIA' if answer else
                                                   'AUTORREFERENCIA_FINANCIERA_TRAS_PREGUNTA_NOMINAL'),
                        'evidence':request.group()+' / '+unit['text'],
                        'speaker_role':unit['speaker_role'],
                        'policy_source':'CRITERIO_USUARIO_CONTEXTO_COMPLETO',
                        'human_verified':False}
    return none
