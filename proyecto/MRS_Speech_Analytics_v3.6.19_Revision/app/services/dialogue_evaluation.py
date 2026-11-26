"""Hechos de conversación con procedencia y ámbito; no asigna voces por intuición.

Las propuestas, decisiones y aclaraciones son hechos distintos. El Excel se
emplea después para cotejarlos; nunca aporta palabras, importes ni respuestas.
"""
import hashlib
import re

from app.services.conversation_evidence import normalize, sentence_evidence

FINANCIAL = re.compile(r'\b(?:pagos?|pagar|deposito|depositar|abonar|tarjeta|cuenta|convenio|cantidad|pesos|deuda|saldo)\b')
QUOTED = re.compile(r'\b(?:diga que|digale que|repita|usted dice que|usted dijo que|el cliente dice|me dijeron que|supongamos que|por ejemplo)\b')
OWN = re.compile(
    r'\b(?:mi (?:tarjeta|cuenta|pago|saldo|aplicacion)|mis pagos|'
    r'yo (?:cobro|recibo|pague|pago|abonaba)|es el dia que me pagan|yo creo que (?:hasta )?manana|'
    r'(?:la tarjeta )?la (?:extr[aavie]+|di de baja)|'
    r'ya tengo el (?:codigo|folio)(?=[^.!?]{0,80}cancelad)|la quiero (?:cancelar|dar de baja)|ya realice (?:mi |el )?pago|por eso lo deje de pagar|no (?:(?:les|le|lo|te) )?(?:voy a|pienso|quiero) pagar|yo no debo nada|'
    r'no (?:he llegado a ningun acuerdo|tengo (?:esa|la) cantidad|me niego a pagar)|'
    r'no me alcanza|'
    r'(?:me )?(?:hicieron|habian hecho) una propuesta|'
    r'(?:yo )?queria ver si podia hacer (?:algun |un )?acuerdo de pago|'
    r'(?:mi finalidad|lo que quiero hacer) (?:si )?es (?:pagar|un convenio))\b')
PENDING = re.compile(
    r'\b(?:no (?:le |lo )?he podido realizar|no (?:he podido|puedo) ir a pagar|'
    r'no tendr[eia]+ posibilidad|no seria posible|'
    r'no (?:sabria|habria) (?:que )?decirle|'
    r'(?:no tengo|no dispongo de) (?:esa|la) cantidad|'
    r'no (?:puedo|sabria) (?:prometer|confirmar|asegurar)(?:le)? (?:cuanto|una cantidad|la cantidad|una fecha)|'
    r'(?:no[, ]+)?(?:pues[, ]+)?no (?:la |lo )?tengo(?=[.!?]|$)|'
    r'(?:voy a|tengo que|necesito) (?:ver|checar|revisar) (?:si|cuanto|con cuanto)\b|'
    r'tengo que volver a (?:marcar|llamar)|no voy a cumplir|'
    r'(?:hago|hacer|sacar|revisar) mis cuentas|'
    r'si (?:arreglo|resuelvo|consigo) (?:todo|el dinero|esto)|'
    r'no puedo (?:hacer|generar|formalizar) (?:un |algun )?convenio|no me alcanza|(?:estoy|estaba) esperando (?:a que )?[^.!?]{0,65}\b(?:dinero|deposito|quincena)\b|'
    r'(?:(?:el dia de )?hoy|ahorita)[, ]+no|'
    r'no me niego a pagar[^.!?]{0,110}(?:plazos|seman[aa]|pagos)|'
    r'(?:primero|antes de pagar)[^.!?]{0,90}(?:consultar|revisar|aclarar)|'
    r'como me mandarian algo por escrito antes de pagarlo|'
    r'me podria comunicar con ustedes mas tarde|'
    r'(?:puedo|podria|le puedo|les puedo) regresar la llamada (?:en|dentro de)[^.!?]{0,40}minutos|'
    r'(?:por si|para ver si) (?:mi )?(?:mama|papa|familia|herman[oa]) me (?:puede )?prestar[^.!?]{0,25}dinero|'
    r'me puede volver a llamar[^.!?]{0,40}(?:manana|tarde)|'
    r'lo voy a (?:analizar|pensar|consultar|revisar)|'
    r'(?:no|pero) (?:te |le )?estoy diciendo que no[^.!?]{0,80}(?:quiero|convenio))\b')
DISPUTE = re.compile(
    r'\b(?:(?:yo )?no (?:debo nada|tengo (?:ningun )?adeudo|reconozco (?:ese|el) adeudo)|'
    r'no entiendo por ?que\b[^.!?]{0,80}\b(?:seguro|comision|cargos|saldo)|yo no he usado (?:esa|mi|la) tarjeta|'
    r'no (?:he utilizado|he usado) (?:esa|mi|la) tarjeta|'
    r'no (?:hice|reconozco) (?:las |esas |ninguna )?compras|'
    r'no reconozco (?:esos |los )?cargos|'
    r'no se (?:ni )?que (?:tengo que )?pagar|'
    r'no he llegado a ningun acuerdo[^.!?]{0,70}tarjeta|'
    r'eso no me explicaron|no me dieron ningun contrato)\b')


def scan_dialogue(text, segments=()):
    source = normalize(text)
    units, cursor = [], 0
    events = []
    for unit in sentence_evidence(text, segments):
        value = normalize(unit['text'])
        start = source.find(value, cursor)
        if start < 0:
            continue
        end = start + len(value)
        cursor = end
        record = dict(unit, normalized_start=start, normalized_end=end)
        units.append(record)
        if unit['speaker_role'] in {'GESTOR', 'TERCERO'}:
            continue
        # Descartar las preguntas, conservando declaraciones posteriores.
        spans = list(re.finditer(r'¿[^?]*\?', value))
        def statement(match):
            return (not any(a.start() <= match.start() < a.end() for a in spans)
                    and not QUOTED.search(value[:match.end()])
                    and not re.search(r'\b(?:si tuviera|si pudiera|si yo tuviera|si alguien)\b', value[:match.end()]))
        context = source[max(0, start-220):end]
        if not FINANCIAL.search(context):
            continue
        for kind, pattern in [('OWN_FINANCES', OWN), ('PENDING_DECISION', PENDING), ('ACCOUNT_DISPUTE', DISPUTE)]:
            for match in pattern.finditer(value):
                # Una solicitud propia de documento antes de pagar puede
                # expresarse como pregunta; no es promesa ni verificación.
                own_document_question = kind == 'PENDING_DECISION' and 'antes de pagarlo' in match.group()
                if not statement(match) and not own_document_question:
                    continue
                if re.search(r'\b(?:no es cierto que|no dije que|diga|si)\s*$', value[:match.start()]):
                    continue
                if (kind=='PENDING_DECISION' and match.group().startswith('lo voy a ')
                        and re.search(r'\bno\s*$',value[:match.start()])):
                    continue  # «No lo voy a revisar» no acredita decidir revisarlo.
                # «Ahorita no se refleja» y «hoy no puede anotar» describen
                # trámites, no una decisión de pago del interlocutor.
                if kind == 'PENDING_DECISION' and re.fullmatch(r'(?:(?:el dia de )?hoy|ahorita)[, ]+no',match.group()):
                    tail=value[match.end():].lstrip(' ,')
                    if tail and not re.match(r'(?:[.!]|(?:tengo (?:el dinero|dinero|para pagar|previsto)|lo tengo previsto|cuento|puedo (?:pagar|depositar|abonar)|voy a (?:pagar|depositar|abonar))\b)',tail):
                        continue
                    local=source[max(0,start-160):start+match.start()]
                    if re.search(r'\b(?:whatsapp|anotar|numero|escucho|hablar|comprobante|reflejado)\b',local[-100:]):
                        continue
                position = start + match.start()
                events.append({'kind':kind, 'position':position, 'end':start+match.end(),
                    'evidence':unit['text'], 'phrase':match.group(), 'speaker_role':unit['speaker_role'],
                    'start':unit['start'], 'finish':unit['end'],
                    'source':'ORIGINAL_TRANSCRIPT', 'human_verified':False,
                    'id':f'{kind}:{position}:{start+match.end()}'})
    from app.services.payment_dialogue_frames import payment_replies
    for reply in payment_replies(text,segments):
        kinds=[]
        if reply['own_financial_response']:kinds.append('OWN_FINANCES')
        if reply['declined']or reply['conditional']:kinds.append('PENDING_DECISION')
        for kind in kinds:
            events.append({'kind':kind,'position':reply['position'],'end':reply['end'],
                'evidence':reply['evidence'],'phrase':reply['reply'],'speaker_role':reply['speaker_role'],
                'start':None,'finish':None,'source':'ORIGINAL_TRANSCRIPT_LOCAL_PAYMENT_REPLY',
                'human_verified':False,'id':f"{kind}:{reply['position']}:{reply['end']}"})
    from app.services.payment_lifecycle import payment_decision_events
    for event in payment_decision_events(text,segments):
        if event['accepted']:continue
        events.append({'kind':'PENDING_DECISION','position':event['position'],'end':event['end'],
            'evidence':event['evidence'],'phrase':event['decision_phrase'],
            'speaker_role':event['speaker_role'],'start':None,'finish':None,
            'source':'ORIGINAL_TRANSCRIPT_PAYMENT_LIFECYCLE','human_verified':False,
            'id':f"PENDING_DECISION:{event['position']}:{event['end']}"})
    from app.services.payment_intent_frames import payment_frames
    for frame in payment_frames(text,segments):
        kinds=[]
        if frame['own_financial_response']:kinds.append('OWN_FINANCES')
        if not frame['history']and(frame['declined']or frame['conditional']):kinds.append('PENDING_DECISION')
        for kind in kinds:
            events.append({'kind':kind,'position':frame['position'],'end':frame['end'],
                'evidence':frame['evidence'],'phrase':frame['reply'],'speaker_role':frame['speaker_role'],
                'start':None,'finish':None,'source':'ORIGINAL_TRANSCRIPT_PAYMENT_OBJECT_FRAME',
                'human_verified':False,'id':f"{kind}:{frame['position']}:{frame['end']}"})
    return {'source_sha256':hashlib.sha256(str(text).encode('utf-8')).hexdigest(),
            'events':events, 'units':units, 'human_verified':False}


def full_payment_refusal(commitment):
    """Rechazar intereses/compras o una oferta no equivale a rechazar toda deuda."""
    if not commitment.get('declined') or commitment.get('accepted'):
        return False
    reply=normalize(commitment.get('evidence') or '')
    match=re.search(r'\bno (?:(?:lo|le|la|les) )?(?:voy a|pienso) pagar\b',reply)
    if not match or QUOTED.search(reply) or '?' in reply:
        return False
    before=reply[:match.start()]
    if re.search(r'\bno (?:me |le |nos )?(?:(?:va|vaya) a |hay )?(?:decir|diga)\b[^.!?]{0,85}$',before):
        return False  # Citar la negativa que otro podría decir no la acredita.
    # No atribuir al presente una negativa citada de conversación anterior.
    # Por ejemplo: 'les decía y no voy a pagar la tarjeta'.
    historical_clause = before.rsplit('.', 1)[-1][-90:]
    if re.search(r'\b(?:les|le|te) decia\b', historical_clause) and historical_clause.strip().endswith(('y', 'que')):
        return False
    if re.search(r'\b(?:no es que|no digo que|no dije que)\s*$',before):
        return False
    conditional=re.search(r'\b(?:si|cuando)\b[^.!?]{0,140}$',before)
    affirmative_bridge=re.search(r'(?:^|[.!])\s*(?:claro[, ]+)?si[, ]+pero\s*$',before)
    if conditional and not affirmative_bridge:
        return False
    scope=reply[match.end():].split('.')[0][:85]
    return not re.search(r'\b(?:eso|esos|esas|(?:esta|esa|la) cantidad|(?:este|ese) monto|intereses|cargos|compras|solo|solamente|menos|menor|sino)\b',scope)


def pending_status(dialogue, commitment, payment_followup=False, *, date_confirmed=None):
    """Una decisión pendiente acreditada no es un convenio incumplido.

    No inferir un estatus por ausencia de sí, por el Excel, por cortarse el
    audio o por una dificultad de registro en una aplicación.
    """
    if payment_followup:
        return None
    if commitment.get('accepted'):
        if date_confirmed is False:
            return {'detected_status':'NO DEFINE FECHA DE PAGO','confidence':'ALTA',
                'method':'COMPROMISO_SIN_FECHA_CONFIRMADA','evidence':commitment.get('evidence')or'',
                'event_id':'ACCEPTED_WITHOUT_DATE'}
        return None
    if full_payment_refusal(commitment):
        return None  # Una negativa final completa prevalece sobre una duda anterior.
    candidates = [e for e in dialogue['events'] if e['kind'] in {'PENDING_DECISION','ACCOUNT_DISPUTE'}]
    if not candidates:
        return None
    event = max(candidates, key=lambda e:e['position'])
    return {'detected_status':'NO DEFINE FECHA DE PAGO', 'confidence':'ALTA',
            'method':event['kind'], 'evidence':event['evidence'], 'event_id':event['id']}
