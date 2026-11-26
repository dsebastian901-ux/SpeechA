"""Importes expresamente confirmados o explicados; no se completan con Excel."""
import re
from app.services.conversation_evidence import normalize,_role_at
from app.services.dialogue_confirmation_evidence import future_confirmation_events
from app.services.reported_payment_amounts import NUMBER,money_value

def explicit_current_amounts(text,segments=()):
    source=normalize(text)
    events=[dict(e,method='IMPORTE_Y_FECHA_CONFIRMADOS') for e in future_confirmation_events(text,segments) if e.get('amount')]
    from app.services.payment_intent_frames import payment_frames
    for frame in payment_frames(text,segments):
        if not frame['accepted']or frame['history']:continue
        if frame['kind']=='AMOUNT':
            value=frame['reply'];offset=frame['position']
            matches=list(re.finditer(r'^(?:(?:si|ah|bueno)[, ]+)?(?:(?:lo que (?:traigo|tengo) (?:son|es)|cuento con|tengo|traigo|seria (?:el )?monto(?: es)?|(?:el )?monto es) )?(?:de |por )?(?:\$\s*)?(?P<amount>'+NUMBER+r')(?!\w)',value))
        else:
            value=frame['question'];offset=frame['question_position']
            matches=list(re.finditer(r'\b(?:pago (?:de|por)(?: los)?|por la cantidad de|por(?: los)?)\s+(?:\$\s*)?(?P<amount>'+NUMBER+r')(?!\w)',value))
        amounts={money_value(m['amount'])for m in matches}
        if len(amounts)!=1:continue
        amount=amounts.pop()
        if not amount or amount<10:continue
        match=matches[-1]
        if re.match(r'\s*(?:dias?|horas?|meses?|de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre))\b',value[match.end():]):continue
        events.append({'amount':amount,'amount_position':offset+match.start('amount'),
            'amount_end':offset+match.end('amount'),'amount_text':match['amount'],
            'position':frame['position'],'evidence':frame['evidence'],'method':'IMPORTE_EN_PREGUNTA_ACTUAL_ACEPTADA'})
    # La aceptación propia inmediata puede remitir al único importe
    # ofrecido. Nunca completar desde Excel ni de un saldo, teléfono o fecha.
    from app.services.payment_lifecycle import financial_response_events
    for response in financial_response_events(text,segments):
        if response.get('method')=='RESPUESTA_ACTUAL_DE_IMPORTE_Y_FECHA':
            events.append({k:response[k]for k in ['amount','amount_position','amount_end','amount_text','position','evidence']}
                |{'method':'IMPORTE_Y_FECHA_CONFIRMADOS','human_verified':False})
            continue
        offer=response['offer'];offset=response['offer_position']
        matches=list(re.finditer(r'\b(?:pagar|depositar|abonar|pago(?: (?:es|seria))?)(?: de| por)?\s+(?:\$\s*)?(?P<amount>'+NUMBER+r')(?!\w)',offer))
        usable=[]
        for match in matches:
            if re.match(r'\s*(?:dias?|horas?|meses?|de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre))\b',offer[match.end():]):continue
            value=money_value(match['amount'])
            if value and value>=10:usable.append((match,value))
        if len({value for _,value in usable})!=1:continue
        match,value=usable[-1]
        events.append({'amount':value,'amount_position':offset+match.start('amount'),
            'amount_end':offset+match.end('amount'),'amount_text':match['amount'],
            'position':response['position'],'evidence':response['evidence'],
            'method':'IMPORTE_DE_OFERTA_INMEDIATA_ACEPTADA','human_verified':False})
    # Indicar el monto a ingresar en una operación es una propuesta actual,
    # no un número de teléfono ni el saldo meramente informado. No acredita
    # por sí solo aceptación, fecha o realización del pago.
    for match in re.finditer(r'\b(?:elige|elija|seleccione|ingrese) (?:el |un )?monto (?:de )?(?:\$\s*)?(?P<amount>'+NUMBER+r')(?!\w)',source):
        before=source[max(0,match.start()-350):match.start()]
        if not re.search(r'\b(?:aplicacion|banco|transferencia|pago)\b',before):continue
        if _role_at(text,segments,match.start())in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        if re.search(r'\b(?:no|dice que|dijo que|me dijeron que|supongamos que|por ejemplo)\b[^.!?]{0,65}$',before):continue
        amount=money_value(match['amount'])
        if amount and amount>=10:
            events.append({'amount':amount,'amount_position':match.start('amount'),'amount_end':match.end('amount'),
                'amount_text':match['amount'],'position':match.start(),'evidence':match.group(),'method':'MONTO_EXPLICITO_DE_OPERACION_DE_PAGO'})
    pattern=re.compile(r'\bcuanto seria (?:del|el) (?P<percent>\d{1,2})\?\s*(?:si[, ]+)?(?:en este caso seria |serian? )?(?P<amount>'+NUMBER+r')(?!\w)')
    for match in pattern.finditer(source):
        before=source[max(0,match.start()-250):match.start()]
        percent=match['percent']
        if not re.search(r'\bahorita\b[^.!?]{0,100}\bpago\b',before):continue
        if not re.search(r'(?<!\d)'+re.escape(percent)+r'\s*%',before):continue
        amount=money_value(match['amount'])
        if not amount or amount<10:continue
        events.append({'amount':amount,'amount_position':match.start('amount'),'amount_end':match.end('amount'),
                       'amount_text':match['amount'],'position':match.start(),'evidence':match.group(),
                       'method':'IMPORTE_EXPLICITO_DEL_PORCENTAJE_PROPUESTO_AHORITA'})
    return events


def instruction_amount_conflicts(events):
    """Cambio de importe en la operación después de términos aceptados."""
    accepted=[e for e in events if e.get('amount')and e.get('method')in{
        'IMPORTE_Y_FECHA_CONFIRMADOS','IMPORTE_EN_PREGUNTA_ACTUAL_ACEPTADA'}]
    if not accepted:return []
    last=max(accepted,key=lambda e:e['position'])
    return [{'accepted_amount':last['amount'],'instruction_amount':e['amount'],
             'accepted_evidence':last['evidence'],'text':e['evidence'],
             'position':e['position'],'method':'INSTRUCCION_POSTERIOR_CON_IMPORTE_DISTINTO',
             'human_verified':False}
            for e in events if e.get('method')=='MONTO_EXPLICITO_DE_OPERACION_DE_PAGO'
            and e['position']>last['position']and abs(e['amount']-last['amount'])>.009]
