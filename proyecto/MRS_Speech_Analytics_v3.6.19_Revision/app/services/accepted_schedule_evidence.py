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
    candidates=_recapped_schedules(text,segments,call_date)
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


def _recapped_schedules(text, segments, call_date):
    """Dos importes y sus días recapitulados y aceptados en el mismo marco.

    No se completa el remanente desde Excel ni se acepta una alternativa
    hipotética. Las reglas de mora y plazos se aplican después al plan.
    """
    source=normalize(text)
    pattern=re.compile(
        r"\b(?:confirmo|confirmamos|confirmaria|confirmariamos)"
        r"(?: asi)?(?: como (?:te|le) menciono)?[, :]*"
        r"(?:el (?:primer )?pago (?:de |por )?)?(?P<first>"+NUMBER+r")"
        r"(?: pesos)? (?:es |seria |para )?(?:el (?:dia )?)(?P<d1>\d{1,2})"
        r"[, ]+y (?:el (?:segundo )?pago (?:de |por )?)?(?P<second>"+NUMBER+r")"
        r"(?: pesos)? (?:es |seria |para )?(?:el (?:dia )?)(?P<d2>\d{1,2})"
        r"[.?]\s*(?:(?:titular|cliente|interlocutor)\s*:\s*)?"
        r"(?P<yes>si|aja|correcto|de acuerdo|esta bien)(?=[,.! ]|$)")
    result=[]
    for m in pattern.finditer(source):
        if _role_at(text,segments,m.start('yes'))in{'GESTOR','TERCERO'}:continue
        before=source[max(0,m.start()-120):m.start()]
        if re.search(r"\b(?:por ejemplo|supongamos|si pudiera|si tuviera|diga que|dijo que|repita)\b[^.!?]{0,100}$",before):continue
        reply=source[m.start('yes'):m.end()+100].split('.')[0].split('?')[0]
        if re.search(r"\b(?:pero|no puedo|no tengo|a lo mejor|yo creo|si (?:puedo|consigo))\b",reply):continue
        amounts=[money_value(m[k])for k in['first','second']]
        if any(v is None or v<10 for v in amounts):continue
        try:days=[date(call_date.year,call_date.month,int(m[k]))for k in['d1','d2']]
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
