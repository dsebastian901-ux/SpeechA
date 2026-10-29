"""Importes ligados a un pago reportado, separados de fechas y propuestas."""
import re

from app.services.conversation_evidence import normalize


UNITS = dict(zip(('cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince '
                 'dieciseis diecisiete dieciocho diecinueve veinte veintiuno veintidos veintitres veinticuatro '
                 'veinticinco veintiseis veintisiete veintiocho veintinueve').split(), range(30)))
UNITS['un'] = UNITS['una'] = 1
UNITS.update(dict(zip('treinta cuarenta cincuenta sesenta setenta ochenta noventa'.split(), range(30,100,10))))
UNITS.update(dict(zip('cien ciento doscientos trescientos cuatrocientos quinientos seiscientos setecientos ochocientos novecientos'.split(),
                     (100,100,200,300,400,500,600,700,800,900))))
WORDS = '|'.join(sorted([*UNITS,'mil'],key=len,reverse=True))
NUMBER = rf'(?:(?:(?:un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)\s+)?mil\s+\d{{1,3}}|\d{{1,3}}(?:[.,]\d{{3}})+(?:[.,]\d{{1,2}})?|\d{{1,7}}(?:[.,]\d{{1,2}})?|(?:{WORDS})(?:\s+(?:y\s+)?(?:{WORDS})){{0,7}})'
MONEY = re.compile(rf'(?<!\w)(?:\$\s*)?(?P<number>{NUMBER})(?:\s*pesos?)?(?!\w)')


def money_value(token):
    value=normalize(token).strip()
    hybrid=re.fullmatch(r'(?:(un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)\s+)?mil\s+(\d{1,3})',value)
    if hybrid:
        return float(UNITS.get(hybrid[1],1)*1000+int(hybrid[2]))
    if re.fullmatch(r'[\d.,]+',value):
        if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+',value):
            value=re.sub(r'[.,]','',value)
        elif ',' in value and '.' in value:
            value=value.replace(',','')
        else:
            value=value.replace(',','.')
        return float(value)
    total=current=0
    for word in value.split():
        if word=='y': continue
        if word=='mil': total+=(current or 1)*1000; current=0
        elif word in UNITS: current+=UNITS[word]
        else: return None
    return float(total+current)


def reported_amounts(text, completion):
    """No atribuir al pago el saldo que anuncia el gestor ni horas/fechas.

    Acepta importe inmediato de «pagué» o respuesta a una pregunta de monto
    realizado. Mantiene evidencia y conflictos; no escoge el número más cómodo.
    """
    source=normalize(text)
    anchors=completion.get('evidence') or []
    candidates=[]
    def add(start,end,method,anchor):
        fragment=source[start:end]
        for match in MONEY.finditer(fragment):
            before=fragment[max(0,match.start()-75):match.start()]
            after=source[start+match.end():start+match.end()+32]
            if method!='RESPUESTA_IMPORTE_PAGADO' and before.strip():
                if not re.fullmatch(r'\s*(?:(?:de|por|fueron|fue|disculpe|el|mi|un|pago|minimo|pesos)\s*[, ]*)*',before):
                    continue
            if re.search(r'[.!?]\s+',before):
                continue
            if (re.search(r'\b(?:dia|fecha|corte|telefono|whatsapp|referencia|terminacion|digitos|folio|clabe)\s*(?:es|de|el|:)?\s*$',before)
                    or re.match(r'\s*(?:horas?|dias?|meses?|anos?|semana|ocasion|de octubre|de noviembre|de diciembre|de enero)\b',after)):
                continue
            value=money_value(match['number'])
            if value is None or value<1: continue
            # No tomar un monto futuro/cancelación como pago anterior.
            if re.search(r'\b(?:tiene que|tendria que|debe|voy a|va a|tengo que|debo|solicita|solicitando|restante|saldo (?:total|vencido))\b[^.!?]{0,65}$',before):
                continue
            absolute_start=start+match.start()
            if any(c['start']==absolute_start for c in candidates): continue
            candidates.append({'amount':value,'start':absolute_start,'end':start+match.end(),
                'text':fragment,'method':method,'anchor':anchor})
            return

    for unit in anchors:
        a,b=unit['text_start'],unit['text_end']
        tail=source[b:min(len(source),b+180)]
        # Importe ligado al verbo, antes de cambiar de oración/pregunta.
        # Se permiten introducciones naturales y el día antes de «por la cantidad».
        direct=re.match(r'\s*[, ]*(?:(?:ya|senorita|senor|joven)\s*[, ]+){0,3}(?:(?:mi|el|un)\s+pago\s*)?(?:minimo(?: que me pidieron)? de |de |por |por la cantidad (?:que era el pago total )?de )?(?P<amount>'+NUMBER+r')(?:\s*pesos?)?\b',tail)
        if direct:
            add(b+direct.start('amount'),b+direct.end(),'IMPORTE_TRAS_PAGO_REPORTADO',a)
        for match in re.finditer(r'\b(?:por la cantidad (?:que era el pago total )?de|pague|lo pague|pago (?:de|por))\s+',tail):
            bridge=tail[:match.start()]
            if re.search(r'\b(?:manana|tendria|debe|voy a|tengo que|tiene que|'
                         r'(?:puede|podria|necesita) (?:usted )?(?:realizar|aplicar|hacer|cubrir|depositar|abonar))\b',bridge): continue
            add(b+match.end(),min(len(source),b+match.end()+95),'IMPORTE_DE_PAGO_REPORTADO',a)

    # Una pregunta puede quedar lejos de «ya pagué» cuando se comprueba antes
    # la fecha o el comprobante. La pregunta debe referirse al pago realizado.
    question=re.compile(
        r'\b(?:que cantidad (?:pago|pagaron|cubrio|deposito|aplico(?: pago)?|realizo(?: (?:su|el) pago)?)|'
        r'(?:de|por) que cantidad(?: (?:fue|lo (?:hizo|realizo)|realizo(?: (?:su|el) pago)?))?|'
        r'cual fue la cantidad|sobre que cantidad se realizo)\b[^?!]{0,45}[?!.]\s*')
    for match in question.finditer(source):
        previous=[u for u in anchors if 0<=match.start()-u['text_start']<=650]
        if not previous: continue
        anchor=previous[-1]['text_start']
        answer_end=min(len(source),match.end()+110)
        add(match.end(),answer_end,'RESPUESTA_IMPORTE_PAGADO',anchor)
    # ASR sin signos: «el día de ayer de qué cantidad fue disculpe de dos mil...».
    for match in re.finditer(r'\b(?:de que cantidad fue|que cantidad (?:pago|deposito))\s+(?:disculpe\s+)?(?:de\s+)?',source):
        previous=[u for u in anchors if 0<=match.start()-u['text_start']<=350]
        if previous:
            add(match.end(),min(len(source),match.end()+100),'RESPUESTA_IMPORTE_PAGADO',previous[-1]['text_start'])
    for match in re.finditer(r'\b(?:el dia de hoy |hoy |ayer )?(?:realizo|hizo) el pago por\s+',source):
        previous=[u for u in anchors if 0<=match.start()-u['text_start']<=650]
        if previous:
            add(match.end(),min(len(source),match.end()+85),'RECAPITULACION_PAGO_REPORTADO',previous[-1]['text_start'])

    candidates.sort(key=lambda x:x['start'])
    days=r'lunes|martes|miercoles|jueves|viernes|sabado|domingo|ayer|hoy'
    pairs=re.compile(rf'\b(?:el )?(?P<day1>{days}) (?:fue |de |pague )?(?P<a>{NUMBER})'
        rf'\s+y (?:el )?(?:dia )?(?P<day2>{days}) (?:fue |de |pague )?(?P<b>{NUMBER})\b')
    for pair in pairs.finditer(source):
        if pair['day1']==pair['day2']: continue
        if not any(0<=pair.start()-u['text_start']<=650 for u in anchors): continue
        amounts=[money_value(pair['a']),money_value(pair['b'])]
        if any(v is None or v<=0 for v in amounts): continue
        if candidates and not {c['amount'] for c in candidates}.issubset(set(amounts)): continue
        return {'amounts':amounts,'total':sum(amounts),
                'evidence':candidates+[{'text':pair.group(),'amounts':amounts,
                    'dates':[pair['day1'],pair['day2']],'method':'PAGOS_POR_DIAS_DISTINTOS'}],
                'review_required':False,'reason':''}
    # Las menciones de una misma cantidad son reiteraciones, no pagos nuevos.
    amounts=[]
    for item in candidates:
        if item['amount'] not in amounts: amounts.append(item['amount'])
    uncertain=any(re.search(r'\b(?:no recuerdo|no me acuerdo|creo que fueron|creo que eran)\b',c['text'])
                  for c in candidates)
    conflicting=len(amounts)>1
    return {'amounts':amounts if not conflicting else [],
            'total':amounts[0] if len(amounts)==1 and not uncertain else None,
            'evidence':candidates,'review_required':conflicting or uncertain,
            'reason':('Importe de pago reportado expresamente incierto; verificar el comprobante.' if uncertain else
                      'Importes de pagos reportados distintos; verificar eventos antes de sumarlos.' if conflicting else '')}
