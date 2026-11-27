"""Planes de dos pagos aceptados antes de explorar una alternativa opcional."""
import re
from datetime import date,timedelta
from app.services.conversation_evidence import normalize,_role_at
from app.services.reported_payment_amounts import NUMBER,money_value


def unresolved_remainder_dates(text,segments=()):
    """Fechas alternativas declaradas para el remanente, no un plazo elegido.

    No se completa el monto restante ni se elige el día desde el Excel.
    Una posibilidad anterior a una recapitulación no activa esta alerta.
    """
    source=normalize(text)
    pattern=re.compile(r'\b(?:no[, ]+pues[, ]+)?los? \d+(?: pesos)? y (?:ya )?'
        r'(?:los? )?(?:otros?|restantes?)\s*[, ]+el (?:dia )?\d{1,2} o (?:el )?(?:dia )?\d{1,2}\b')
    result=[]
    for m in pattern.finditer(source):
        if m.start()<len(source)-650:continue
        if _role_at(text,segments,m.start())in{'GESTOR','TERCERO'}:continue
        before=source[max(0,m.start()-80):m.start()]
        if re.search(r'\b(?:dice que|dijo que|diga que|por ejemplo|supongamos que)\b[^.!?]{0,65}$',before):continue
        if re.match(r'\s*\?',source[m.end():]):continue
        result.append({'text':m.group(),'start':None,'end':None,'speaker_role':_role_at(text,segments,m.start()),
                       'method':'REMANENTE_CON_DOS_FECHAS_ALTERNATIVAS','human_verified':False})
    return result


def accepted_two_part_schedule(text,segments,call_date):
    none={'confirmed':False,'amounts':[],'dates':[],'evidence':'','human_verified':False}
    if not isinstance(call_date,date):return none
    source=normalize(text)
    pattern=re.compile(r'\b(?:entonces[, ]+)?seria (?:el |un )?(?:pago (?:de |por ))?'
        r'(?P<first>'+NUMBER+r')(?: pesos)? (?:el dia(?: de)? )?'
        r'(?P<day>hoy|manana)\?\s*(?P<yes>si)\b'
        r'(?P<reply>[^?]{0,200}?)\b(?:y )?seria (?:un|uno) mas (?:por|de) '
        r'(?P<second>'+NUMBER+r')(?: pesos)?[.]\s*(?P<yes2>si|correcto|de acuerdo)\b')
    candidates=(_recapped_schedules(text,segments,call_date)+_own_dated_schedule(text,segments,call_date)
                +_equal_recapped_schedule(text,segments,call_date))
    for match in pattern.finditer(source):
        if any(_role_at(text,segments,match.start(k)) in {'GESTOR','TERCERO'} for k in ['yes','yes2']):continue
        if re.search(r'\b(?:no puedo|no tengo|a lo mejor|yo creo|si consigo|si puedo|si me da)\b',match['reply']):continue
        before=source[max(0,match.start()-90):match.start()]
        if re.search(r'\b(?:por ejemplo|si tuviera|si pudiera|usted dijo que|repita)\b',before):continue
        first,second=money_value(match['first']),money_value(match['second'])
        if not first or not second or min(first,second)<10:continue
        earlier=source[max(0,match.start()-1200):match.start()]
        dates=[]
        for amount in re.finditer(NUMBER,earlier):
            if money_value(amount.group())!=second:continue
            lead=earlier[max(0,amount.start()-230):amount.start()]
            if re.search(r'\b(?:whatsapp|telefono|folio|ayer|pasado)\b',lead[-100:]):continue
            for day in re.finditer(r'\bdia (?:que (?:menciona|mencionas) del )?(?P<day>\d{1,2})\b',lead):
                try:second_date=date(call_date.year,call_date.month,int(day['day']))
                except ValueError:continue
                dates.append((amount.start(),second_date,lead[day.start():]+amount.group()))
        # Puede anunciarse «un monto más para el día 16» antes de corregir
        # oralmente su importe. La recapitulación posterior sí debe confirmar
        # ambas cifras; esta rama solo vincula la fecha al segundo pago.
        for day in re.finditer(r'\b(?:monto|pago) mas\b[^.!?]{0,70}\bdia (?:que (?:menciona|mencionas) del )?(?P<day>\d{1,2})\b',earlier):
            try:second_date=date(call_date.year,call_date.month,int(day['day']))
            except ValueError:continue
            dates.append((day.end(),second_date,day.group()))
        if not dates:continue
        _,second_date,date_evidence=max(dates,key=lambda row:row[0])
        first_date=call_date+timedelta(days=match['day']=='manana')
        if second_date<=first_date:continue
        later=source[match.end():]
        rejected=False
        for clause in re.split(r'[.!?]',later):
            if '¿' in clause:continue
            if re.search(r'\b(?:mejor no|cancela(?:r)? (?:el |ese )?convenio|no voy a poder|no puedo pagar(?! con)|no acepto|no lo voy a hacer)\b',clause):
                rejected=True;break
        if rejected:continue
        dates=[{'installment':1,'date':first_date.isoformat(),'text':match['day'],'evidence':match.group()},
               {'installment':2,'date':second_date.isoformat(),'text':str(second_date.day),'evidence':date_evidence}]
        candidates.append({'confirmed':True,'amounts':[first,second],'total':first+second,'dates':dates,
            'evidence':match.group(),'position':match.start('yes2'),'end':match.end(),
            'method':'DOS_PAGOS_ACEPTADOS_CON_FECHAS','human_verified':False})
    return max(candidates,key=lambda row:row['position']) if candidates else none


def _equal_recapped_schedule(text,segments,call_date):
    """Count × unit price plus an explicit calendar and an immediate acceptance.

    No interpolation of missing dates, rounding to the bank minimum or joining
    terms across a handoff. Subsequent revocation still invalidates the plan.
    """
    from decimal import Decimal
    from app.services.payment_lifecycle import frames,FIRM,CONDITION,QUOTE,PAST,NEGATIVE_DECISION
    from app.services.installment_validation import accepted_calendar
    from app.services.negotiation_chronology import HANDOFF
    rows=frames(text,segments);result=[]
    pattern=re.compile(r'\b(?P<count>dos|tres|2|3) pagos (?:de|por) (?P<amount>'+NUMBER+r')(?!\w)')
    for i,offer in enumerate(rows[:-1]):
        match=pattern.search(offer['text'])
        if not match or offer['role']in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        if QUOTE.search(offer['text'])or PAST.search(offer['text'])or CONDITION.search(offer['text']):continue
        count={'dos':2,'tres':3,'2':2,'3':3}[match['count']]
        amount=money_value(match['amount'])
        if amount is None or amount<10:continue
        reply=rows[i+1]
        if reply['role']in{'GESTOR','TERCERO'}or not FIRM.match(reply['text']):continue
        if '?'in reply['text']or CONDITION.search(reply['text'])or NEGATIVE_DECISION.search(reply['text']):continue
        dates=accepted_calendar(offer['text'],call_date,count)
        if len(dates)!=count or HANDOFF.search(offer['text']):continue
        later=[r for r in rows[i+2:]if r['role']!='GESTOR']
        if any(NEGATIVE_DECISION.search(r['text'])for r in later):continue
        evidence=offer['text']+' '+reply['text']
        result.append({'confirmed':True,'amounts':[float(amount)]*count,
            'total':float(Decimal(str(amount))*count),'dates':dates,'evidence':evidence,
            'position':reply['start'],'end':reply['end'],'method':'PARCIALIDADES_IGUALES_ACEPTADAS_CON_CALENDARIO',
            'human_verified':False})
    return result


def _own_dated_schedule(text,segments,call_date):
    """Dos pagos formulados por el propio cliente en una misma declaración.

    No requiere un «sí» adicional al compromiso personal explícito, ni une
    importes de propuestas distintas. Conserva fecha, rol, cita y revocación.
    """
    from app.services.speech_scope import nonassertive_prefix
    source=normalize(text);result=[]
    pattern=re.compile(r'\b(?P<day>hoy|manana) (?:yo )?(?:voy a )?'
        r'(?:hago|hare|realizo|realizare|hacer|realizar) (?:el |mi |un )?pago (?:de |por )?'
        r'(?P<first>'+NUMBER+r')(?: pesos)? (?:para que|y) (?:el )?dia (?P<d2>\d{1,2}) '
        r'(?:yo )?(?:hago|hare|realizo|realizare) (?:el )?otro pago (?:de |por )?'
        r'(?P<second>'+NUMBER+r')(?!\w)')
    for m in pattern.finditer(source):
        if _role_at(text,segments,m.start())in{'GESTOR','TERCERO'}:continue
        if nonassertive_prefix(source,m.start())or re.search(r'\b(?:si|cuando)\s*$',source[max(0,m.start()-30):m.start()]):continue
        a,b=money_value(m['first']),money_value(m['second'])
        if a is None or b is None or min(a,b)<10:continue
        first=call_date+timedelta(days=m['day']=='manana')
        try:second=date(call_date.year,call_date.month,int(m['d2']))
        except ValueError:continue
        if second<=first:continue
        if re.search(r'\b(?:no acepto|no me comprometo|no voy a poder|no puedo pagar(?! con)|no voy a pagar)\b',source[m.end():]):continue
        result.append({'confirmed':True,'amounts':[a,b],'total':a+b,
            'dates':[{'installment':i+1,'date':d.isoformat(),'text':str(d.day),'evidence':m.group()}for i,d in enumerate([first,second])],
            'evidence':m.group(),'position':m.start(),'end':m.end(),
            'method':'DOS_PAGOS_PROPIOS_CON_FECHAS','human_verified':False})
    return result


def _recapped_schedules(text, segments, call_date):
    """Dos importes y sus días recapitulados y aceptados en el mismo marco.

    No se completa el remanente desde Excel ni se acepta una alternativa
    hipotética. Las reglas de mora y plazos se aplican después al plan.
    """
    source=normalize(text)
    patterns=[re.compile(
        r"\b(?:confirmo|confirmamos|confirmaria|confirmariamos)"
        r"(?: asi)?(?: como (?:te|le) menciono)?[, :]*"
        r"(?:el (?:primer )?pago (?:de |por )?)?(?P<first>"+NUMBER+r")"
        r"(?: pesos)? (?:es |seria |para )?(?:el (?:dia )?)(?P<d1>\d{1,2})"
        r"[, ]+y (?:el (?:segundo )?pago (?:de |por )?)?(?P<second>"+NUMBER+r")"
        r"(?: pesos)? (?:es |seria |para )?(?:el (?:dia )?)(?P<d2>\d{1,2})"
        r"[.?]\s*(?:(?:titular|cliente|interlocutor)\s*:\s*)?"
        r"(?P<yes>si|aja|correcto|de acuerdo|esta bien)(?=[,.! ]|$)"),re.compile(
        r"\b(?:el primero )?seria (?:de |un pago de |el pago de )(?P<first>"+NUMBER+r")"
        r"(?: pesos)? el dia (?:de )?(?P<d1>hoy|manana|\d{1,2})"
        r"\s+y (?:el )?segundo pago (?:seria )?(?:de |por )(?P<second>"+NUMBER+r")"
        r"(?: pesos)? el dia (?P<d2>\d{1,2})[, ]*¿?correcto\?\s*"
        r"(?:(?:titular|cliente|interlocutor)\s*:\s*)?(?P<yes>si|aja|correcto|de acuerdo|esta bien)(?=[,.! ]|$)")]
    result=[]
    for m in (match for pattern in patterns for match in pattern.finditer(source)):
        if _role_at(text,segments,m.start('yes'))in{'GESTOR','TERCERO'}:continue
        before=source[max(0,m.start()-120):m.start()]
        if re.search(r"\b(?:por ejemplo|supongamos|si pudiera|si tuviera|diga que|dijo que|repita)\b[^.!?]{0,100}$",before):continue
        reply=source[m.start('yes'):m.end()+100].split('.')[0].split('?')[0]
        if re.search(r"\b(?:pero|no puedo|no tengo|a lo mejor|yo creo|si (?:puedo|consigo))\b",reply):continue
        amounts=[money_value(m[k])for k in['first','second']]
        if any(v is None or v<10 for v in amounts):continue
        try:days=[call_date+timedelta(days=m[k]=='manana') if m[k]in {'hoy','manana'} else date(call_date.year,call_date.month,int(m[k]))for k in['d1','d2']]
        except ValueError:continue
        if not(call_date<=days[0]<days[1]):continue
        # Una revocación posterior no desaparece por haber dicho sí antes.
        later=source[m.end():]
        if re.search(r"\b(?:mejor no|no acepto|no voy a poder|no puedo pagar(?! con)|no lo voy a hacer|no me comprometo|cancela(?:r)? (?:el |ese )?convenio)\b",later):continue
        dates=[{'installment':i+1,'date':d.isoformat(),'text':str(d.day),'evidence':m.group()}for i,d in enumerate(days)]
        result.append({'confirmed':True,'amounts':amounts,'total':sum(amounts),'dates':dates,
            'evidence':m.group(),'position':m.start('yes'),'end':m.end(),
            'method':'DOS_PAGOS_ACEPTADOS_CON_FECHAS','human_verified':False})
    return result
