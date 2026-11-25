"""Correcciones explícitas de saldo y separación de historia/ofertas, sin completar desde Excel."""
import re
from app.services.conversation_evidence import normalize, _role_at
from app.services.reported_payment_amounts import NUMBER, money_value


def callback_dictation_spans(text):
    """Excluir cifras dictadas como contacto sin completar ni validar el teléfono."""
    from app.services.payment_reference_validation import callback_numbers, TOKEN
    from app.services.message_contact_evidence import callback_dictation_fragments
    source=normalize(text);spans=[]
    for record in callback_numbers(source)+callback_dictation_fragments(source):
        if 'text_start' in record:
            spans.append((record['text_start'],record['text_end']))
        elif record.get('text'):
            for match in re.finditer(re.escape(record['text']),source):
                spans.append((match.start(),match.end()))
    # Un contacto incompleto sigue siendo un identificador, aunque no alcance
    # para certificar recepción o validar sus diez dígitos. No exigir aquí las
    # condiciones positivas de un recado para excluirlo del dinero.
    gap=re.compile(r'[\W_]*(?:(?:es|seria|el|aja|si|ok|correcto|perdon|a ver)[\W_]*)*')
    for cue in re.finditer(r'\b(?:numero(?: telefonico| de contacto| de telefono)?|telefono|whatsapp)\b',source):
        before=source[max(0,cue.start()-250):cue.start()]
        if cue.group()=='numero' and not re.search(r'\b(?:anotar|anotarte|anotarlo|apuntar|llamada|contacto|whatsapp|telefono)\b',before):
            continue
        tail=source[cue.end():cue.end()+220]
        tokens=list(TOKEN.finditer(tail))
        if not tokens or tokens[0].start()>65 or not gap.fullmatch(tail[:tokens[0].start()]):
            continue
        group=[tokens[0]]
        for token in tokens[1:]:
            if not gap.fullmatch(tail[group[-1].end():token.start()]):break
            group.append(token)
        if re.match(r'\s*(?:pesos?|por ciento|dias?|meses?|parcialidades)\b',tail[group[-1].end():]):
            continue
        spans.append((cue.end()+group[0].start(),cue.end()+group[-1].end()))
    return sorted(set(spans))


def balance_corrections(text):
    source = normalize(text)
    anchor = r'\bsaldo(?: total| pendiente| vencido)?\s+(?:(?:es|de|por|la|cantidad)\s+){0,4}'
    patterns = [
        re.compile(anchor + rf'(?P<old>{NUMBER})\s*[,;]\s*(?P<new>{NUMBER})\s*[,;]?\s*(?:perdon|corrijo|disculpe)\b'),
        re.compile(anchor + rf'(?P<old>{NUMBER})\s*[,;]\s*(?:perdon|corrijo|disculpe)[, ]+(?P<new>{NUMBER})(?!\w)'),
    ]
    result=[]
    for pattern in patterns:
        for m in pattern.finditer(source):
            value=money_value(m['new'])
            if value is None or value <= 0:continue
            result.append({'old_start':m.start('old'),'old_end':m.end('old'),
                           'start':m.start('new'),'end':m.end('new'),'amount':value,
                           'phrase':m['new'],'evidence':m.group(),'method':'CORRECCION_EXPLICITA_SALDO'})
    return result


def balance_scope(text, segments, start, end):
    source=normalize(text);before=source[max(0,start-200):start];after=source[end:end+110]
    role=_role_at(text,segments,start)
    if (re.search(r'\bsaldo\s*$',before)and re.fullmatch(r'\d{1,2}',source[start:end])
            and not re.match(r'\s*pesos?\b',after)):
        return 'CIFRA_SIN_DETERMINANTE_MONETARIO'
    if source.rfind('¿',0,start)>source.rfind('?',0,start):
        return 'IMPORTE_EN_PREGUNTA_NO_DECLARACION_DE_SALDO'
    if re.search(r'\b(?:me habian comentado|me habian dicho|me comentaron|me dijeron|me decian)\b[^.!?]{0,95}$',before):
        return 'PROPUESTA_ANTERIOR_REPORTADA'
    if role in {'TITULAR','TERCERO','INTERLOCUTOR'}:
        return 'IMPORTE_DICHO_POR_INTERLOCUTOR'
    if re.match(r'\s*[,;]?\s*(?:que )?es (?:el |un |su )?(?:pago )?minimo(?: requerido)?\b',after):
        return 'MINIMO_REQUERIDO_NO_SALDO_TOTAL'
    if re.search(r'\byo (?:ahorita |acabo de )?consulte (?:mi |el )?saldo\b[^.!?]{0,80}$',before):
        return 'CONSULTA_PERSONAL_REPORTADA_NO_SALDO_DEL_GESTOR'
    if re.search(r'\b(?:tenia|tenian|tuve|tenia registrado|habia) (?:un |el |mi )?saldo[^.!?]{0,45}$',before):
        return 'SALDO_HISTORICO'
    # «Le estamos dando el saldo de X» al presentar el descuento no declara
    # que X sea el saldo total contable; no exime un saldo total explícito.
    if (re.search(r'\b(?:se le esta dando|le estamos dando|le estaria dando|propuesta de|oferta de|saldo con descuento)\b[^.!?]{0,55}$',before)
            and not re.search(r'\bsaldo total\b[^.!?]{0,30}$',before)
            and re.search(r'\b(?:liquidando|liquidaria|liquidar|liquidada|liquida)\b',after)):
        return 'OFERTA_DE_LIQUIDACION'
    return 'SALDO_ACTUAL_DECLARADO'


def fragmented_balance_amounts(text):
    """Un millar con resto de cuatro cifras no acredita un saldo de 11 pesos."""
    source=normalize(text)
    pattern=re.compile(r'\bsaldo(?: total| pendiente| vencido)?[^.!?]{0,65}?'
                       r'(?P<number>\d{1,3}\s+mil\s+\d{4,})(?!\w)')
    return [{'start':m.start('number'),'end':m.end('number'),'text':m['number'],
             'method':'SALDO_ASR_FRAGMENTADO_REQUIERE_AUDIO'} for m in pattern.finditer(source)]


def attached_balance_amount(text,start):
    """«Saldo ..., tarjeta ..., una cantidad de X» conserva el sujeto saldo.

    «Cantidad» no es por sí sola una nueva propuesta de pago. Un verbo de
    pago, descuento o propuesta entre ambos sí cambia el objeto financiero.
    """
    source=normalize(text);prefix=source[max(0,start-160):start]
    if not re.search(r'\b(?:una |la )?cantidad de\s*$',prefix):return False
    anchors=list(re.finditer(r'\bsaldo(?: total| pendiente| vencido)?\b',prefix))
    if not anchors:return False
    bridge=prefix[anchors[-1].end():]
    return not re.search(r'\b(?:pagar|pago|depositar|abonar|minimo|descuento|'
                         r'liquidar|propuesta|convenio)\b',bridge)
