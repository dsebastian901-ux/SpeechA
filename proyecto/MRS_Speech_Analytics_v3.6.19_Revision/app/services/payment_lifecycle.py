"""Marcos de diálogo con objeto y posiciones, independientes del estatus Excel.

Una aceptación se vincula a la propuesta inmediata. Los números telefónicos,
comprobantes, citas y pagos históricos no son ofertas de pago actuales.
"""
import re
import unicodedata
from app.services.conversation_evidence import normalize, _role_at

PAYMENT=re.compile(r'\b(?:pago|pagar|depositar|abonar|deposito|abono|convenio|pesos|cantidad|monto)\b')
OTHER=re.compile(r'\b(?:whatsapp|telefono|numero|comprobante|recibo|ticket|folio|anotar|apuntar|correo|cita|consulta medica|documentos?)\b')
PAST=re.compile(r'\b(?:ya (?:lo |les )?pague|ya (?:hice|realice|efectue)|pague (?:ayer|hoy)|pago (?:recibido|efectuado|reportado)|(?:me|le) (?:habian dicho|dijeron)|la vez pasada|el mes pasado)\b')
QUOTE=re.compile(r'\b(?:dice que|dijo que|diga que|repita|por ejemplo|supongamos|usted dice|usted dijo)\b')
CONDITION=re.compile(r'\b(?:yo creo|a lo mejor|tal vez|quizas|si (?:puedo|consigo|me (?:dan|prestan|depositan))|no (?:puedo|podria) (?:confirmar|prometer)|no se (?:si|cuanto|cuando)|voy a (?:ver|tratar)|hare lo posible)\b')
FIRM=re.compile(r'^(?:(?:ah|bueno|ok|aja)[, ]+){0,2}(?:si(?:[, ]+(?:si|esta (?:muy )?bien))?|asi es|correcto|de acuerdo|esta (?:muy )?bien|claro(?: que si)?)(?=[,.! ]|$)')
DATE=re.compile(r'\b(?:hoy|manana|(?:el |este )?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)|(?:el )?dia \d{1,2}|\d{1,2} de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre))\b')
AMOUNT=re.compile(r'(?<!\w)(?:\$\s*\d[\d,.]*|\d[\d,.]*\s*pesos|(?:un |dos |tres |cuatro |cinco |seis |siete |ocho |nueve |diez )?mil|[a-z]+cientos|quinientos|(?:cantidad|monto|pago|deposito|abono) (?:de |por )?\d[\d,.]*)(?!\w)')


def frames(text, segments=()):
    source=normalize(text);result=[]
    # No partir importes decimales ni siglas; las preguntas sí cierran objeto.
    for match in re.finditer(r'.+?(?:[!?](?:\s|$)|\.(?=\s|$)|$)',source):
        value=match.group().strip()
        if not value:continue
        lo=match.start()+len(match.group())-len(match.group().lstrip())
        value=re.sub(r'^(?:gestor|agente|asesor|titular|cliente|interlocutor|tercero|familiar)\s*:\s*','',value)
        pos=source.find(value,lo)
        result.append({'text':value,'start':pos,'end':pos+len(value),
                       'role':_role_at(text,segments,pos)})
    return result


def financial_response_events(text, segments=()):
    """Aceptación de una recapitulación; no exige el signo '?' de Whisper.

    Se exige una propuesta futura explícita con monto o fecha. El turno
    inmediatamente siguiente debe aceptar esa propuesta, sin cambio de objeto.
    """
    rows=frames(text,segments);events=[]
    for previous,reply in zip(rows,rows[1:]):
        offer=previous['text'];answer=reply['text'];fold=offer.lstrip('¿ ')
        if previous['role']in{'TITULAR','TERCERO','INTERLOCUTOR'}or reply['role']in{'GESTOR','TERCERO'}:continue
        if QUOTE.search(offer)or PAST.search(offer)or OTHER.search(offer):continue
        if not PAYMENT.search(offer)or not(DATE.search(offer)or AMOUNT.search(offer)):continue
        directed=bool(re.search(r'\b(?:confirm(?:o|amos|aria|ariamos)|quedaria(?:mos)?|'
            r'quedamos|(?:su|el) pago (?:seria|queda)|seria (?:depositar|pagar|abonar)|'
            r'(?:puede|podria|tiene que|tendria que|debera) (?:realizar|hacer|pagar|depositar|abonar)|'
            r'(?:el banco|el minimo que nos) (?:le |nos )?(?:requiere|solicita)|'
            r'(?:ponemos|genero|generamos|confirmamos) (?:su |el |un )?convenio)\b',fold))
        if not directed or re.search(r'\b(?:no|nunca)\s*$',fold[:next((m.start()for m in PAYMENT.finditer(fold)),0)]):continue
        accepted=FIRM.match(answer)
        if not accepted or answer.startswith('¿')or'?'in answer:continue
        if CONDITION.search(answer)or re.search(r'\b(?:pero no|no puedo|no podria|no tengo|no acepto|no me comprometo)\b',answer):continue
        if re.match(r'(?:(?:ah|bueno|ok|aja)[, ]+){0,2}si[ ,]+(?:no|lo realiza|lo puede|puede|paga|gusta|quiere|consigue)\b',answer):continue
        if re.search(r'\b(?:otro pago|segundo pago|remanente|restante|o realizar|o bien|en dos|dos pagos|dos exhibiciones)\b',offer):continue
        if re.search(r'\b(?:clave inter ?bancaria|concepto|banco destino|referencia|digitos)\b',offer):continue
        if OTHER.search(answer)and not re.search(r'\b(?:pago|pagar|depositar|abonar)\b',answer):continue
        dated=offer
        candidates=list(re.finditer(r'\b(?:este pago (?:lo )?(?:puede|podria|debe) realizar|(?:su|el) pago (?:seria|queda)|confirm(?:o|amos|aria|ariamos)(?: su| el)? pago|(?:puede|podria|tiene que|tendria que|debera) (?:realizar|hacer|pagar|depositar|abonar))\b',offer))
        if candidates:
            dated=offer[candidates[-1].start():]
            dated=re.split(r'\b(?:yo le sugiero|para que se comunique|para que pueda (?:cancelar|llamar|comunicarse))\b',dated)[0]
        events.append({'position':reply['start'],'end':reply['end'],'accepted':True,'declined':False,
            'conditional':False,'evidence':offer+' '+answer,'date_evidence':dated+' '+answer,
            'reply':answer,'method':'ACEPTACION_DE_RECAPITULACION_FINANCIERA_INMEDIATA',
            'speaker_role':reply['role'],'human_verified':False,'acoustic_voice_identified':False})
    return events


POSITIVE_DECISION = re.compile('\\b(?:me comprometo a (?:pagar|depositar|abonar|cubrir)|(?:yo )?voy a (?:ir a )?(?:pagar|depositar|abonar|cubrir)|lo voy a realizar|pagare|depositare|abonare|realizare (?:un |el |mi )?pago|hare (?:un |el |mi )pago|(?:hoy|manana) (?:mismo )?(?:deposito|abono|lo hago|lo realizo|hago el deposito|hago (?:el|mi) pago|realizo (?:el|mi) pago)|(?:manana|(?:el )?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)) (?:(?:le )?(?:pago|deposito)|mando a pagar(?:lo)?))\\b')
NEGATIVE_DECISION = re.compile('\\b(?:no (?:(?:le|les|lo) )?(?:voy a|puedo|pienso|quiero) (?:pagar|depositar|abonar|cubrir)|no he podido realizarlo|no he podido ir (?:porque|hasta)|no les voy a completar|no voy a poder[.!]?$|no he podido pagar|no me alcanza(?: para pagar)?|no puedo (?:comprometerme|confirmar|dar una fecha)|no me comprometo|no tengo (?:esa|la) cantidad|no dispongo de (?:esa|la) cantidad|no (?:tengo|cuento con) (?:(?:todo |una? |la |esa )?(?:cierta )?cantidad de )?dinero|no tengo todo el dinero|no (?:tengo|cuento con) (?:la cantidad|esa cantidad)|no tengo (?:ni )?(?:para |pal )?(?:abonar|pagar)|no (?:lo )?(?:puedo|voy a poder) (?:pagar|hacer)|no lo confirmo|(?:manana|hoy) no (?:podria|puedo)|no (?:tendria|tendre)\\s+(?:\\d+|dos|mil)|(?:ahorita|por el momento) (?:todavia )?no puedo|no puedo (?:ahorita|hacer (?:ese |el |un )?pago))\\b')
CONDITIONAL_DECISION = re.compile('\\b(?:si me da tiempo|si consigo (?:el )?dinero|si tengo dinero|si puedo juntar|lo podria(?: hacer)?|(?:yo )?pagaria|hare lo posible|a lo mejor|yo creo|no sabria decir(?:le|te)? (?:si|cuanto|cuando)|no se cuanto (?:voy a|vaya a|pueda) (?:pagar|depositar)|no se cuando (?:pueda|voy a) pagar)\\b')


def payment_decision_events(text, segments=()):
    """Todos los cambios de decisión, no solo el primer verbo de cada ventana.

    La fuente es el texto, con ámbito de negación/cita y objeto financiero.
    Los tiempos de una ventana ASR no se usan para ordenar decisiones.
    """
    from app.services.declarative_evidence import declarative_units
    source=normalize(text);events=[];cursor=0
    verbatim=unicodedata.normalize('NFC',re.sub(r'\s+',' ',str(text or '')).strip().lower())
    for unit in declarative_units(text,segments):
        value=normalize(unit['text']);at=source.find(value,cursor)
        if at<0:continue
        cursor=at+len(value)
        if unit['speaker_role']in{'GESTOR','TERCERO'}:continue
        # Las preguntas requieren el marco de respuesta, no autodeterminación.
        if '?'in value or '¿'in value:
            value=value.split('¿',1)[0].strip()if'¿'in value else''
            if not value or'?'in value:continue
        negatives=list(NEGATIVE_DECISION.finditer(value))
        negatives+=list(re.finditer(r'\bno (?:le |les )?voy a (?:seguir |estar )pagando(?: nada)?\b',value))
        positives=list(POSITIVE_DECISION.finditer(value))
        positives+=list(re.finditer(r'\b(?:(?:yo )?lo (?:hago|hare|realizo|realizare|aplico)|'
            r'(?:el |mi )?(?:pago|deposito) lo (?:hago|hare|realizo)|lo estaria (?:realizando|haciendo|depositando)) '
            r'(?:(?:el dia de|el dia|para|el) )?(?:hoy|manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo|\d{1,2})\b',value))
        positives+=list(re.finditer(r'\b(?:yo )?voy a hacer (?:el |mi |un )?pago\b',value))
        negatives+=list(re.finditer(r'\b(?:no me voy a comprometer|no (?:quisiera|quiero) comprometerme|'
            r'no (?:se lo |te lo |lo )?(?:prometo|aseguro))\b',value))
        conditions=list(CONDITIONAL_DECISION.finditer(value))
        conditions+=list(re.finditer(r'\b(?:cuando (?:yo )?pueda (?:pagar(?:la|lo)?|apagar(?:la|lo)|depositar|abonar)|'
            r'(?:pago|pagare|pagaria|pagando) (?:cuando (?:yo )?pueda|en cuanto (?:tenga|junte|consiga))|'
            r'me comprometo a (?:ir )?(?:estar )?pagando\b[^.!?]{0,110}\b(?:quincenalmente|semanalmente))\b',value))
        for accepted,found in [(True,positives),(False,negatives),(None,conditions)]:
            for match in found:
                from app.services.speech_scope import nonassertive_prefix
                if nonassertive_prefix(value,match.start()):continue
                pos=at+match.start();before=value[max(0,match.start()-100):match.start()]
                if _role_at(text,segments,pos)in{'GESTOR','TERCERO'}:continue
                if re.search(r'\b(?:usted dice|usted dijo|tu dices|usted menciona|usted comento|diga que|repita que|por ejemplo|supongamos que)\b[^.!?;]{0,65}$',before):continue
                if accepted is False and re.match(r'(?:manana|hoy|ahorita) no (?:puedo|podria)',match.group()):
                    if re.match(r'\s+(?:hablar|atender|escuchar|anotar|apuntar|enviar|mandar|contestar)\b',value[match.end():]):continue
                if accepted is True:
                    if re.search(r'\b(?:realizó|aplicó)\b',verbatim[pos:pos+len(match.group())]):continue
                    if any(n.start()<=match.start()<n.end()for n in negatives):continue
                    if re.search(r'\b(?:no|nunca|jamas)(?: (?:lo|la|le|les|se))?\s*$',before):continue
                    if match.group()=='pagare'and re.search(r'\b(?:el|un|su|del|al|ese|este)\s*$',before):continue
                    if re.search(r'\bsi (?:yo )?(?:tuviera|tuviese|pudiera|pudiese)\b[^.!?]{0,90}$',before):continue
                nearby=source[max(0,pos-160):pos]+match.group()
                topics=list(re.finditer(r'\b(?:pagos?|pagar|depositar|deposito|abonar|abono|dinero|pesos|cantidad|convenio|comprobante|ticket|whatsapp|telefono|numero|folio|cita|consulta medica)\b',nearby))
                if accepted is None and(not topics or OTHER.fullmatch(topics[-1].group())):
                    if not re.match(r'cuando (?:yo )?pueda (?:pagar|apagar|depositar|abonar)',match.group()):continue
                if accepted is None and re.search(r'\b(?:no se (?:ha )?reflejado|no (?:habia|tenia|tienen) sistema)\b',value[match.end():]):
                    if not re.search(r'\b(?:voy a (?:pagar|depositar|abonar)|pagare|depositare|no puedo pagar)\b',value[match.end():]):continue
                if accepted is None and match.group()=='pagaria'and re.search(r'\b(?:restante|resto|diferencia)\b',before)and re.search(r'\bno (?:lo |la )?$',before):continue
                if accepted is True and re.match(r'(?:yo )?(?:lo|el pago|mi pago|el deposito|mi deposito)\b',match.group()):
                    if topics and OTHER.fullmatch(topics[-1].group()):continue
                    if not topics:
                        prior=source[max(0,pos-650):pos]
                        payment=list(PAYMENT.finditer(prior))
                        if not payment or OTHER.search(prior[payment[-1].end():]):continue
                if re.search(r'\b(?:comprometer|prometo|aseguro)\b',match.group()):
                    after=value[match.end():match.end()+110]
                    objects=list(re.finditer(r'\b(?:pago|pagar|depositar|abonar|comprobante|ticket|whatsapp|telefono|numero)\b',after))
                    if objects and OTHER.fullmatch(objects[0].group()):continue
                    if not topics or OTHER.fullmatch(topics[-1].group()):continue
                if match.group()=='lo voy a realizar'and(not topics or OTHER.fullmatch(topics[-1].group())):continue
                if accepted is False and re.match(r'no puedo confirmar (?:su|el) pago\b',value[match.start():])and OTHER.search(value[match.end():]):continue
                result=accepted
                if accepted is True and re.search(r'\b(?:esperando (?:que|tener)|poder (?:decir(?:te|le|les)?|confirmar(?:te|le|les)?)|para ver (?:si|como))\b[^.!?]{0,100}$',before):result=None
                if accepted is True:
                    preceding=[c for c in conditions if c.start()<match.start()]
                    if preceding:
                        scope=value[preceding[-1].end():match.start()]
                        if not re.search(r'\b(?:pero|sin falta|me comprometo)\b',scope):result=None
                tail=value[match.start():]
                stop=re.search(r'[.!?;]|\b(?:comprobante|ticket|whatsapp|telefono|cita|cancelacion|contactar|llamar)\b',tail)
                dated=tail[:stop.start()]if stop else tail
                events.append({'position':pos,'end':at+match.end(),'accepted':result is True,
                    'declined':result is False,'conditional':result is None,'evidence':unit['text'],
                    'date_evidence':dated,'decision_phrase':match.group(),'method':'SECUENCIA_COMPLETA_DE_DECISIONES_DE_PAGO',
                    'speaker_role':_role_at(text,segments,pos),'human_verified':False})
    # Respuesta personal negativa al pago solicitado: estado pendiente,
    # sin convertir una falta de reporte/comprobante del gestor en negativa.
    from app.services.contact_evidence_graph import own_payment_responses
    for response in own_payment_responses(text,segments):
        answer=response['answer']
        if re.match(r'(?:no[, ]+)?(?:(?:aun|todavia)[, ]+)?no (?:lo |le )?he podido|no[, ]+(?:aun|todavia) no he podido',answer):
            events.append({'position':response['position'],'end':response['position']+len(answer),
                'accepted':False,'declined':True,'conditional':False,
                'evidence':response['text'],'date_evidence':'','decision_phrase':answer,
                'method':'RESPUESTA_PERSONAL_NEGATIVA_A_PREGUNTA_DE_PAGO',
                'speaker_role':response['speaker_role'],'human_verified':False})
    return events


def active_paid_followup(payment_events, completed_payment_evidence):
    """Un rechazo vigente posterior al pago histórico no es seguimiento puro."""
    reports=completed_payment_evidence.get('evidence')or[]
    if not completed_payment_evidence.get('confirmed')or not reports:return False
    last_report=max(e.get('text_end',0)for e in reports)
    current=[e for e in payment_events if e['position']>=last_report]
    return not(current and max(current,key=lambda e:e['position']).get('declined'))
