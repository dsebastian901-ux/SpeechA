"""Financial objects and handoffs, anchored to positions in this conversation.

Terms are never filled from Excel. A transport choice does not rescind a
payment; a later refusal of that payment does. Transfers start a new scope.
"""
import re
from app.services.conversation_evidence import normalize

HANDOFF = re.compile(r'\b(?:le voy a pasar|lo voy a pasar|la voy a pasar|lo paso|la paso|'
                     r'le transfiero|voy a transferir|enviarla directamente|enviarlo directamente)\b'
                     r'[^.!?]{0,110}\b(?:departamento|area|convenios|supervisor|validacion)\b')
METHOD = re.compile(r'\b(?:transferencia|banca movil|aplicacion|en tienda|en sucursal)\b')


def handoffs(text):
    return [{'position':m.start(),'end':m.end(),'text':m.group(),
             'method':'TRANSFERENCIA_EXPLICITA_DE_AREA'} for m in HANDOFF.finditer(normalize(text))]


def scope_start(text, position):
    return max([h['end'] for h in handoffs(text) if h['end'] <= position] or [0])


def route_uncertainty(value):
    return bool(METHOD.search(value) and re.search(
        r'\b(?:creo que|no se si|tal vez|a lo mejor)\b',value)
        and not re.search(r'\b(?:si consigo|si puedo|si tengo|no puedo pagar|no voy a pagar)\b',value))


def payment_purpose(value):
    """Explanation of cancellation is not an offer to settle a debt."""
    value=normalize(value)
    if re.search(r'\b(?:cancelacion|cancelar|dar(?:la)? de baja|tramite)\b',value) and re.search(
            r'\b(?:una vez|cuando|si ya|hasta que|ya puede|pueda hacer|para cancelar|para que pueda)\b',value):
        if not re.search(r'\b(?:le ofrezco|le ofrecemos|con este pago liquida|le podemos ofrecer)\b',value):
            return 'EXPLICACION_TRAMITE_CANCELACION'
    if re.search(r'\b(?:liquidar|liquida|liquidacion|saldar el total|saldo total)\b',value):return 'LIQUIDACION'
    if re.search(r'\b(?:mensualidad|mensualidades)\b',value):return 'MENSUALIDAD'
    if re.search(r'\b(?:regulariz|al corriente|lo vencido)\w*',value):return 'REGULARIZACION'
    return 'PAGO'


def validation_terms(text, segments=()):
    """Adjacent date/amount answers in a validation exchange, either order.

    Allows a recap of the same date between answers, never a new proposal,
    a contact/document question, a transfer or a historical report.
    """
    from app.services.payment_lifecycle import frames, CONDITION, QUOTE, PAST, OTHER, DATE
    from app.services.reported_payment_amounts import NUMBER,money_value
    source=normalize(text)
    if not re.search(r'\b(?:fecha|cuando|para que dia)\b',source)or not re.search(r'\b(?:cantidad|monto)\b',source):return []
    rows=frames(text,segments);events=[]
    for i,question in enumerate(rows[:-1]):
        q=question['text']
        if question['role'] in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        if OTHER.search(q)or PAST.search(q)or QUOTE.search(q):continue
        date_query=bool(re.search(r'\b(?:fecha|cuando|para que dia)\b',q)
                        and re.search(r'\b(?:pago|pagar|aplic|confirm|movimiento)\w*',q))
        if not date_query or re.search(r'\b(?:vencimiento|corte|limite)\b',q):continue
        answer=rows[i+1];day=answer['text']
        if answer['role'] in {'GESTOR','TERCERO'}or not DATE.search(day):continue
        if CONDITION.search(day)or QUOTE.search(day)or PAST.search(day)or re.search(r'\b(?:o|no|creo|si consigo|si puedo)\b',day):continue
        for j in range(i+2,min(i+5,len(rows)-1)):
            query=rows[j];reply=rows[j+1]
            middle=' '.join(r['text']for r in rows[i+2:j])
            if middle and (HANDOFF.search(middle)or OTHER.search(middle)or CONDITION.search(middle)
                           or '?'in middle or '¿'in middle
                           or re.search(r'\b(?:no|pero|otro|cantidad|pesos|pagar|vencimiento|corte)\b',middle)):break
            if not re.search(r'\b(?:cantidad|monto)\b',query['text']):continue
            if query['role']in{'TITULAR','TERCERO','INTERLOCUTOR'}or reply['role']in{'GESTOR','TERCERO'}:break
            if OTHER.search(query['text'])or PAST.search(query['text'])or QUOTE.search(query['text']):break
            value=re.sub(r'^(?:serian?|de|por)\s+','',reply['text'])
            match=re.fullmatch(r'(?P<amount>'+NUMBER+r')(?: pesos)?[.! ]*',value)
            if not match:break
            amount=money_value(match['amount'])
            if amount is None or amount<10:break
            evidence=' '.join(r['text']for r in rows[i:j+2])
            events.append({'position':reply['start'],'end':reply['end'],'accepted':True,
                'declined':False,'conditional':False,'amount':float(amount),'date_evidence':day,
                'amount_position':reply['start']+reply['text'].find(match['amount']),
                'amount_end':reply['start']+reply['text'].find(match['amount'])+len(match['amount']),
                'amount_text':match['amount'],
                'offer_position':question['start'],'evidence':evidence,'reply':reply['text'],
                'offer':q,'speaker_role':reply['role'],'method':'RESPUESTA_ACTUAL_DE_IMPORTE_Y_FECHA',
                'human_verified':False,'acoustic_voice_identified':False})
            break
    return events
