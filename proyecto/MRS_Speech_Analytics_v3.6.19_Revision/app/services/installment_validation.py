"""Relaciona importes con parcialidades explícitas; conserva contradicciones."""
import re

from app.services.reported_payment_amounts import NUMBER, money_value
from app.services.conversation_evidence import normalize


def unresolved_accepted_plan(text, plan, dates, segments=()):
    """No ocultar un plan aceptado no extraído detrás de una intención posterior.

    Detecta la obligación de validar el calendario; no fabrica sus importes,
    no acredita aceptación por una pregunta ni atribuye falta grave.
    """
    from app.services.conversation_evidence import sentence_evidence
    cues=[]
    for unit in sentence_evidence(text,segments):
        value=normalize(unit['text'])
        if re.search(r'\b(?:me dijeron|dijo que|el mes pasado|anteriormente|por ejemplo|supongamos)\b',value):
            continue
        match=re.search(r'\b(?:usted (?:acepta|confirma)|confirma|confirmamos|acordamos|quedamos en)'
                        r'\s+(?:los |el acuerdo de )?(dos|tres|2|3) pagos\b',value)
        if match and not re.search(r'\b(?:no|nunca|si)\s*$',value[:match.start()]) and '?' not in unit['text']:
            cues.append({'count':{'dos':2,'tres':3,'2':2,'3':3}[match[1]],
                         'text':unit['text'],'speaker_role':unit['speaker_role']})
    # Una recapitulación aceptada puede enumerar ambos pagos sin decir
    # «dos pagos». No comparar solo el primero contra el mínimo mientras
    # falta extraer el calendario completo. Esto no confirma ni suma el plan.
    from app.services.payment_lifecycle import financial_response_events
    day=r'(?:hoy|manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo|dia \d{1,2})'
    coordinated=re.compile(r'\bpago (?:de|por) '+NUMBER+r'(?: pesos)? '
        r'[^?!]{0,65}?\b'+day+r'\b\s+y\s+(?:otro pago de |un pago de )?'+NUMBER+
        r'(?: pesos)? [^?!]{0,80}?\b'+day+r'\b')
    for event in financial_response_events(text,segments):
        if coordinated.search(normalize(event['offer'])):
            cues.append({'count':2,'text':event['evidence'],'speaker_role':event['speaker_role'],
                'method':'RECAPITULACION_DE_DOS_IMPORTES_CON_FECHAS'})
    if not cues:return {'review_required':False,'evidence':[]}
    count=cues[-1]['count']
    unresolved=(len(plan.get('amounts')or[])!=count or len(dates)<count or plan.get('review_required'))
    return {'review_required':bool(unresolved),'expected_count':count,'evidence':cues,
            'reason':'Se describe un plan aceptado de varias parcialidades, pero no quedaron validados todos sus importes y fechas.' if unresolved else ''}


def installment_dates(source, parse_date, expected_count=None):
    """Última fecha propuesta para cada parcialidad, separada de recordatorios."""
    matches = list(re.finditer(r"\b(primer(?: pago)?|segundo(?: pago)?|tercer(?: pago)?|pago mas)\b", source))
    dates = {}
    for index, match in enumerate(matches):
        ordinal = 1 if match[1].startswith("primer") else 3 if match[1].startswith("tercer") else 2
        left = match.start()
        if ordinal == 1 and re.search(r"\bcomo\s*$", source[max(0,left-8):left]):
            breaks = list(re.finditer(r"[.!?](?:\s|$)", source[:left]))
            left = breaks[-1].end() if breaks else 0
        right = min(len(source), match.end()+180, matches[index+1].start() if index+1 < len(matches) else len(source))
        stop = re.search(r"[.!?](?:\s|$)", source[match.end():right])
        if stop:
            right = match.end()+stop.start()
        evidence = source[left:right]
        parsed = parse_date(evidence)
        if parsed.get("date"):
            dates[ordinal] = {"installment": ordinal, "date": parsed["date"].isoformat(),
                              "text": parsed["text"], "evidence": evidence}
    ordered = [dates[k] for k in sorted(dates)]
    if expected_count not in {2,3} or len(ordered)>=expected_count:
        return ordered
    # Cierre repetido de un calendario: «día 6, día 13, día 20». Solo
    # emplear fechas completas del mismo plan, en orden, sin tomar teléfonos.
    calendar = []
    for match in re.finditer(r'\bdia\s+(?P<day>\d{1,2})(?!\d|\s*[/:-])',source):
        parsed=parse_date('Pago el día '+match['day'])
        if parsed.get('date'):
            value={'date':parsed['date'].isoformat(),'text':match.group(),
                   'evidence':source[max(0,match.start()-65):match.end()+65],
                   'position':match.start()}
            if calendar and calendar[-1]['date']==value['date']:
                calendar[-1]=value
            else:
                calendar.append(value)
    for start in range(len(calendar)-expected_count,-1,-1):
        window=calendar[start:start+expected_count]
        values=[row['date'] for row in window]
        if values==sorted(set(values)) and window[-1]['position']-window[0]['position']<=350:
            return [dict({k:v for k,v in row.items() if k!='position'},installment=n)
                    for n,row in enumerate(window,1)]
    return ordered


def installment_plan(source, mentions):
    source = normalize(source)
    schedules = []
    for match in re.finditer(r'\bdia\s+(?P<days>\d{1,2}(?:\s*(?:[,./]|y)\s*\d{1,2}){1,2})'
            r'(?!\d|\s*(?:[,./]|y)\s*\d)[^?!]{0,140}?\bpor\s+(?P<amount>'+NUMBER+r')\s+cada pago\b',source):
        days = [int(day) for day in re.findall(r'\d+',match['days'])]
        amount = money_value(match['amount'])
        if amount and amount>=10 and all(1<=day<=31 for day in days) and days==sorted(set(days)):
            schedules.append((match.start(),[amount]*len(days),match.group()))
    # Un plan desigual debe conservar todos sus pagos; «dos de X y el
    # último de Y» no es un monto único X ni un plan de dos pagos iguales.
    unequal = []
    for match in re.finditer(r'\b(?:dos|2) (?:pagos )?de\s+(?P<first>'+NUMBER+r')'
            r'\s+y\s+(?:el )?(?:ultimo|tercer pago)\b[^.!?]{0,110}?\b(?:por|de)\s+'
            r'(?P<last>'+NUMBER+r')(?!\w)', source):
        first, last = money_value(match['first']), money_value(match['last'])
        if first and last and re.search(r'\b(?:pagos?|regularizar|cuenta)\b', source[max(0,match.start()-120):match.end()]):
            unequal.append((match.start(), [first, first, last], match.group()))
    counts = []
    for match in re.finditer(r"\b(dos|tres|2|3) pagos (?:por|de)\s+", source):
        amount = next((m for m in mentions if match.end() <= m[0] <= match.end()+8), None)
        if amount is None:
            spoken = re.match(rf'(?P<amount>{NUMBER})(?!\w)',source[match.end():])
            value = money_value(spoken['amount']) if spoken else None
            if value and value > 0:
                amount = (match.end(),match.end()+spoken.end(),value,spoken.group())
        if amount:
            count = {"dos": 2, "tres": 3, "2": 2, "3": 3}[match[1]]
            counts.append((match.start(), [float(amount[2])]*count, source[match.start():amount[1]]))
    bindings = {}
    evidence = []
    pattern = r"\b(primer(?: pago)?|segundo(?: pago)?|tercer(?: pago)?|pago mas)\b"
    for match in re.finditer(pattern, source):
        ordinal = 1 if match[1].startswith("primer") else 3 if match[1].startswith("tercer") else 2
        amount = None
        for m in mentions:
            if not match.end() <= m[0] <= match.end()+100:
                continue
            bridge = source[match.end():m[0]]
            if re.search(pattern, bridge) or re.search(r"[.!?]", bridge):
                break
            if re.search(r"\b(?:por|cantidad de|de)\s*$", bridge):
                amount = m
            break
        if amount is None and re.search(r"\bcomo\s*$", source[max(0,match.start()-8):match.start()]):
            previous = [m for m in mentions if 0 <= match.start()-m[1] <= 85]
            if previous:
                amount = previous[-1]
        if amount:
            bindings.setdefault(ordinal, []).append(float(amount[2]))
            evidence.append({"installment": ordinal, "amount": float(amount[2]),
                             "text": source[min(match.start(),amount[0]):max(match.end(),amount[1])]})
    conflicts = [{"installment": ordinal, "amounts": sorted(set(values))}
                 for ordinal, values in bindings.items() if len(set(values)) > 1]
    if len(bindings) >= 2 and sorted(bindings) == list(range(1, max(bindings)+1)):
        amounts = [bindings[k][-1] for k in sorted(bindings)]
        method = "PARCIALIDADES_IDENTIFICADAS"
    elif (unequal or schedules) and (not counts or max(unequal+schedules)[0] > counts[-1][0]):
        _, amounts, phrase = max(unequal+schedules,key=lambda p:p[0])
        evidence.append({'text': phrase})
        method = 'PAGOS_CON_CALENDARIO_EXPLICITO' if schedules and phrase==schedules[-1][2] else 'DOS_PAGOS_Y_ULTIMO_DISTINTO'
    elif counts:
        _, amounts, phrase = counts[-1]
        evidence.append({"text": phrase})
        method = "PAGOS_IGUALES_EXPLICITOS"
    else:
        amounts, method = [], "SIN_PLAN_EXPLICITO"
    return {"amounts": amounts, "total": sum(amounts) if amounts else None,
            "method": method, "evidence": evidence, "conflicts": conflicts,
            "review_required": bool(conflicts)}
