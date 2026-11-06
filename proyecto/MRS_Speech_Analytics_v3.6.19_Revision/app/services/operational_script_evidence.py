"""Variantes ASR de la presentación del despacho y del comprobante de pago."""
import re

from app.services.conversation_evidence import normalize, sentence_evidence, _role_at


def company_alias_evidence(text, segments=()):
    """Una variante no acredita MRS si no pertenece a la presentación."""
    source = normalize(text)
    sep = r'[.\s_-]*'
    aliases = re.compile(
        rf'\b(?:d{sep}m{sep}r{sep}s|m{sep}i{sep}r{sep}s|'
        rf'm{sep}a{sep}r{sep}s|m{sep}r{sep}c|m{sep}r)\b')
    found = []
    for match in aliases.finditer(source):
        if _role_at(text, segments, match.start()) in {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}:
            continue
        before = source[max(0, match.start()-140):match.start()]
        after = source[match.end():match.end()+140]
        nearby = before + match.group() + after
        if re.search(r'\b(?:no (?:somos|hablo|hablamos|llamo|trabajo|es)|me dijeron|me dijo|usted dijo)\b[^.!?]{0,100}$', before):
            continue
        company = re.search(r'\b(?:juridico|curidico|corporativo|cooperativo|despacho|consultores?|consultoria|firma de abogados)\b', nearby)
        presentation = re.search(r'\b(?:mi nombre es|me presento|su servidor[ae]?|le saluda|'
                                 r'le hablo|le hablamos|hablamos|hablo|le llamo|le llamamos|'
                                 r'me comunico|nos comunicamos|le marcamos|por parte de)\b', before)
        representation = re.search(r'\ben representacion\b', after)
        direct = re.search(r'\b(?:juridico|curidico|corporativo|cooperativo|despacho|firma de abogados)(?: de)?\s*[,.:]?\s*$', before)
        if not ((presentation and (company or representation)) or direct):
            continue
        found.append({'text': source[max(0, match.start()-100):match.end()+100],
                      'phrase': match.group(), 'method': 'VARIANTE_ASR_EN_PRESENTACION',
                      'speaker_role': _role_at(text, segments, match.start()),
                      'start': None, 'end': None})
    return found


RECEIPT = r'(?:comprobantes?(?!\s+de\s+(?:(?:la|su|el)\s+)?(?:domicilio|linea|telefono))|tickets?|tickers?|tiquet[ea]?s?|tiques?|capturas?|fichas? de pago|recibos? de (?:su )?pago)'


def receipt_request_evidence(text, segments=()):
    """Solicitud/expectativa de comprobante y canal se acreditan por separado."""
    source = normalize(text)
    requests, received, channels, pending = [], [], [], []
    explicit_refusal = False
    verbs = (r'(?:mandar|mand(?:e|a)(?:me|nos)?|mandando|enviar|envi(?:e|a)(?:me|nos)?|enviarme|enviarnos|enviando|'
             r'compartir|comparta(?:me|nos)?|comparte|compartirnos|compartiendo|haga llegar|hacer llegar|reportar|reporte|reportarnos|regala|'
             r'proporcione|proporcionar|remitir|remita)')
    request = re.compile(rf'\b{verbs}\b[^.!?]{{0,100}}?\b{RECEIPT}\b')
    reporting = re.compile(r'\b(?:reporte|reportar|reportarnos|reportando|reporteme)\b[^.!?]{0,65}'
                           r'\b(?:pagos?|depositos?|abonos?)\b[^.!?]{0,100}\b(?:whatsapp|whats app|guasap|wasap)\b')
    expectation = re.compile(
        rf'\b(?:esper(?:o|amos|aremos|aria|aremos)|(?:estamos|estaremos) esperando|'
        rf'(?:quedamos|quedo|quedaremos|que damos|se quedo) (?:(?:al|el) pendiente[s]? de|a la espera de|en espera de|en espera del|a la espera del|la espera del reporte de)|en espera de)'
        rf'\s+(?:(?:de |la fotografia de |la foto de )?(?:su|sus|el|los|la|las|un|una)\s+)?{RECEIPT}\b')
    for unit in sentence_evidence(text, segments):
        value = normalize(unit['text'])
        role = unit['speaker_role']
        if role not in {'TITULAR','TERCERO','INTERLOCUTOR'}:
            for match in re.finditer(r'\b(?:whatsapp|whats app|whatsaba|guasap|wasap|guatsap|watsap)\b', value):
                if not re.search(r'\bno (?:tengo|uso|cuento con)\s*$', value[:match.start()]):
                    channels.append(dict(unit, phrase=match.group()))
            if re.search(rf'\b(?:no es necesario|no se requiere|no hace falta|no (?:mande|envie))\b[^.!?]{{0,90}}\b{RECEIPT}\b',value):
                explicit_refusal = True
            for pattern in (request, expectation, reporting, re.compile(rf'\b(?:le (?:voy a )?pedir|le pido|le encargo|necesito|le solicito)\b[^.!?]{{0,110}}\b{RECEIPT}\b')):
                for match in pattern.finditer(value):
                    before = value[max(0,match.start()-80):match.start()]
                    if re.search(r'\b(?:no|nunca)(?: (?:nos|me|lo|la|se|le))?\s*$',before):
                        explicit_refusal = True
                        continue
                    if re.search(r'\bno (?:le )?(?:voy a )?(?:pedir|pido|pedimos|pedire)(?: que)?\b[^.!?]{0,35}$',before):
                        explicit_refusal = True
                        continue
                    if re.search(r'\b(?:no|nunca|no (?:le |lo )?(?:pido|pedimos|pedire que)|'
                                 r'yo|ya|dice que|dijo que|diga que|repita que|si hubiera|si hubiese)\s*$',before):
                        continue
                    if re.search(r'\b(?:no es necesario|no se requiere|no hace falta)\b[^.!?]{0,45}$',before):
                        continue
                    if re.search(r'\bno (?:me |nos |lo )?(?:mande|envie|comparta|haga)\b',match.group()):
                        explicit_refusal = True
                        continue
                    requests.append(dict(unit,phrase=match.group(),method='SOLICITA_O_ESPERA_COMPROBANTE'))
            backwards = re.search(rf'\b{RECEIPT}\b[^.!?]{{0,100}}\b(?:me |nos |lo |la )?(?:envia|manda|comparte|va a compartir)\b',value)
            if backwards and not re.search(r'\b(?:no|nunca|dice que|dijo que|diga que)\s*$',value[:backwards.start()]):
                requests.append(dict(unit,phrase=backwards.group(),method='INDICA_ENVIO_DEL_DOCUMENTO_MENCIONADO'))
            # Una fotografía puede ser del ticket: no confundirla con INE/ARCO.
            photo=re.search(r'\b(?:mande|envie|comparta|enviar|mandar|enviarnos)\b[^.!?]{0,65}\b(?:foto|fotografia)\b',value)
            if photo and re.search(r'\b(?:pago|deposito|ticket|tiquete|comprobante)\b',value) and not re.search(r'\b(?:ine|identificacion|linea telefonica)\b',value):
                prefix=value[max(0,photo.start()-60):photo.start()]
                if not re.search(r'\b(?:no|nunca|yo|ya|dice que|dijo que|diga que)\s*$',prefix):
                    requests.append(dict(unit,phrase=photo.group(),method='SOLICITA_FOTOGRAFIA_DE_PAGO'))
        if role not in {'TITULAR','TERCERO','INTERLOCUTOR'}:
            uncertain = re.search(rf'\b(?:a este|al) whatsapp\b[^.!?]{{0,45}}\b(?:mas a llegar|hace llegar)\b[^.!?]{{0,40}}\b{RECEIPT}\b',value)
            if uncertain:
                pending.append(dict(unit,phrase=uncertain.group(),method='POSIBLE_SOLICITUD_ASR_REQUIERE_AUDIO'))
        # Acredita que se reportó el envío; no certifica recepción ni pago bancario.
        for match in re.finditer(rf'\bya (?:nos |lo |se lo )?(?:mande|envie|mando|envio|comparti|compartio)\b[^.!?]{{0,55}}\b(?:{RECEIPT}|fotografia)\b',value):
            if re.search(r'\b(?:no|nunca|diga que|repita que)\s*$',value[:match.start()]):continue
            if re.search(r'\bhace (?:dos|tres|cuatro|cinco|\d+) anos\b',value):continue
            received.append(dict(unit,phrase=match.group(),method='ENVIO_REPORTADO_EN_CONVERSACION'))
    # El lector anterior reconocía un comprobante próximo a WhatsApp. Si ASR
    # conserva ambos pero perdió la petición, no convertir esa duda en omisión.
    # Tampoco certificar cumplimiento: queda pendiente de cotejo del audio.
    if not requests and not received and not pending and channels and not explicit_refusal:
        for unit in sentence_evidence(text, segments):
            if re.search(rf'\b{RECEIPT}\b',normalize(unit['text'])):
                pending.append(dict(unit,method='COMPROBANTE_Y_CANAL_SIN_PETICION_CLARA'))
                break
    return {'requested':bool(requests),'reported_sent':bool(received),
            'channel':'WHATSAPP' if channels else 'NO CONFIRMADO',
            'request_evidence':requests,'reported_sent_evidence':received,'channel_evidence':channels,
            'review_required':bool(pending) and not requests,'uncertain_request_evidence':pending}


def remaining_payment_proposals(text, segments=()):
    """No eximir una propuesta vigente del restante por un pago ya reportado."""
    source=normalize(text);cursor=0;found=[]
    for unit in sentence_evidence(text,segments):
        value=normalize(unit['text']);position=source.find(value,cursor)
        if position<0:continue
        cursor=position+len(value)
        if unit['speaker_role'] in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        match=re.search(r'\b(?:puede|podria|podemos) confirmar (?:ese|este|el|su) pago\b'
                        r'[^.!?]{0,60}\b(?:el dia|para el|hoy|manana)\b',value)
        if not match:continue
        before=source[max(0,position-200):position]
        after=source[cursor:cursor+180]
        if re.search(r'\b(?:no|dice que|dijo que|repita que)\s*$',value[:match.start()]):continue
        if not re.search(r'\b(?:otra propuesta|otro pago|pago restante|pagar (?:el )?restante|restante que)\b',before+value+after):continue
        found.append(dict(unit,phrase=match.group(),method='PROPUESTA_DE_RESTANTE_REQUIERE_ACEPTACION'))
    return found
