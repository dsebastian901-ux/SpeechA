"""Respuestas locales con objeto de pago, separadas de ofertas y trámites.

Los eventos son hechos textuales con posición. No asignan voces acústicas ni
aportan fechas/importes desde el Excel.
"""
import re
from app.services.conversation_evidence import normalize,_role_at

DATE=r'(?:hoy|manana|(?:el |este |proximo )?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)|(?:el )?dia \d{1,2})'
OTHER_TOPIC=re.compile(r'\b(?:comprobante|ticket|recibo|whatsapp|telefono|numero|folio|anotar|apuntar|correo)\b')
FINANCIAL=re.compile(r'\b(?:pago|pagar|depositar|deposito|abonar|abono|monto|cantidad|pesos|convenio)\b')
QUOTED=re.compile(r'\b(?:dice que|dijo que|diga que|usted dijo|usted dice|repita|por ejemplo|supongamos)\b[^.!?]{0,90}$')
CONDITION=re.compile(r'\b(?:(?:yo )?creo|a lo mejor|tal vez|posiblemente|si consigo|si puedo|si arreglo|si resuelvo|si me (?:dan|prestan|depositan|liberan)|hare lo posible|voy a (?:ver|tratar)|no (?:puedo|podria|podre|sabria) (?:confirmar|prometer|decir|pagar|depositar|abonar)|no se (?:si|cuanto|cuando))\b')


def payment_replies(text,segments=()):
    source=normalize(text);found=[];previous=0
    for end in re.finditer(r'\?',source):
        opening=source.rfind('¿',previous,end.start())
        if opening<0:
            breaks=list(re.finditer(r'\.(?=\s)|[!?]',source[previous:end.start()]))
            opening=previous+(breaks[-1].end()if breaks else 0)
        question=source[opening:end.start()+1].lstrip('¿ ')
        q_start=end.start()+1-len(question)
        previous=end.end()
        if len(question)>260:continue
        if not re.search(r'\b(?:podemos|puedo|puede|puedes|podria|podrias|podriamos|confirm|contari|contamos|tendra|tendras|aplicaria|realizaria|pagaria|seria|lo realizara)\w*\b',question):continue
        context=source[max(0,q_start-220):q_start]
        explicit=bool(FINANCIAL.search(question))
        temporal=bool(re.search(DATE,question))
        if not explicit and not temporal:continue
        if OTHER_TOPIC.search(question):continue
        if not explicit:
            topics=list(re.finditer(r'\b(?:pago|pagar|deposito|cantidad|monto|pesos|comprobante|ticket|recibo|whatsapp|telefono|numero|folio)\b',context))
            if not topics or OTHER_TOPIC.fullmatch(topics[-1].group()):continue
        if re.search(r'\b(?:ayer|realizado|efectuado|recibido|reportado|hizo|pudo realizar|ya realizo|ya pago)\b',question):continue
        if re.match(r'no\b',question)or QUOTED.search(context[-100:]):continue
        tail=source[end.end():end.end()+200]
        label=re.match(r'\s*(?:(?:titular|cliente|interlocutor|gestor|tercero|familiar)\s*:\s*)?',tail)
        start=end.end()+label.end();tail=source[start:start+180]
        boundary=re.search(r'\.(?=\s|$)|[!?]|\b(?:gestor|titular|tercero|cliente|interlocutor)\s*:',tail)
        reply=tail[:boundary.start()if boundary else len(tail)].strip()
        if not reply or tail.startswith('¿')or(boundary and boundary.group()=='?'):continue
        if _role_at(text,segments,start)in{'GESTOR','TERCERO'}:continue
        if re.search(r'\b(?:ya (?:lo |les )?pague|pague ayer|ya (?:hice|realice|mande)|me lo habia dicho|ya les habia pagado)\b',reply):continue
        if re.match(r'(?:me presento|mi nombre|hablamos|le (?:hablo|ofrezco|solicito|requiero|voy a)|se le|el banco)\b',reply):continue
        conditional=bool(CONDITION.search(reply))
        declined=bool(re.match(r'(?:no\b|(?:hoy|ahorita)[, ]+no\b)',reply))
        accepted=not(conditional or declined)and bool(re.match(
            r'(?:(?:ah|bueno|ok|aja)[, ]+){0,2}(?:si\b|asi es\b|de acuerdo\b|esta bien\b|claro\b|'
            r'(?:seria|lo (?:realizo|aplico)|(?:el pago )?queda(?:ria)?) (?:el dia de |el dia |para )?'+DATE+r'\b)',reply))
        # La respuesta «mañana a las diez» a una alternativa explícita de
        # fecha se refiere al pago, sin exigir «sí, pagaré» literalmente.
        date_prefix=r'(?:(?:seria|para) )?(?:el dia de |el dia )?'
        if re.match(date_prefix+DATE+r'[, ]+no\b',reply):declined=True
        if temporal and not(conditional or declined)and re.match(date_prefix+DATE+r'\b',reply):accepted=True
        if not(accepted or declined or conditional):continue
        evidence=source[q_start:start+len(reply)]
        own=bool(re.search(r'\b(?:yo|mi|mis|no (?:puedo|tengo|cuento)|estoy|me (?:pagan|quede)|voy a)\b',reply))
        found.append({'position':start,'end':start+len(reply),'accepted':accepted,'declined':declined,
            'conditional':conditional,'evidence':evidence,'reply':reply,'own_financial_response':own,
            'date_evidence':('Pago '+reply if temporal and re.search(DATE,reply) else evidence),'method':'RESPUESTA_LOCAL_A_PREGUNTA_DE_PAGO','speaker_role':_role_at(text,segments,start),
            'human_verified':False,'acoustic_voice_identified':False})
    # Aceptación después de aclarar el día actual. Su ámbito es la última
    # propuesta con importe y día límite, sin otro objeto financiero intermedio.
    correction=re.compile(r'\bhoy es (?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)[^.!?]{0,55}[.!]\s*(?P<reply>ok[, ]+esta bien|de acuerdo|si[, ]+esta bien)\b')
    for match in correction.finditer(source):
        before=source[max(0,match.start()-500):match.start()]
        offers=list(re.finditer(r'\b(?:propuesta|pago|pagar|haga|realice)\b[^.!?]{0,170}',before))
        if not offers:continue
        offer=offers[-1]
        if not re.search(r'\b(?:\d{2,}|mil|quinientos|cientos)\b',offer.group())or not re.search(DATE,offer.group()):continue
        if OTHER_TOPIC.search(before[offer.start():]):continue
        pos=match.start('reply')
        if _role_at(text,segments,pos)in{'GESTOR','TERCERO'}:continue
        tail=source[match.end():match.end()+60]
        if CONDITION.search(tail.split('.')[0])or re.match(r'[, ]*pero no\b',tail):continue
        evidence=before[offer.start():]+' '+match.group()
        found.append({'position':pos,'end':match.end(),'accepted':True,'declined':False,'conditional':False,
            'evidence':evidence,'date_evidence':offer.group(),'reply':match['reply'],
            'own_financial_response':False,'method':'ACEPTACION_TRAS_ACLARAR_DIA_ACTUAL',
            'speaker_role':_role_at(text,segments,pos),'human_verified':False,'acoustic_voice_identified':False})
    # Una limitación personal explícita sigue siendo respuesta sobre pago
    # cuando ASR perdió el signo de la pregunta previa. No la extender a
    # dictado de teléfonos, documentos, citas o trámites.
    from app.services.declarative_evidence import declarative_units
    cursor=0
    for unit in declarative_units(text,segments):
        value=normalize(unit['text']);at=source.find(value,cursor)
        if at<0:continue
        cursor=at+len(value)
        if unit['speaker_role']in{'GESTOR','TERCERO'}or OTHER_TOPIC.search(value):continue
        limitation=re.search(r'\bno (?:puedo|podria)\b[^.!?]{0,55}\bhasta '
            r'(?:el (?:dia )?\d{1,2}|el fin de semana|la quincena)\b',value)
        if not limitation:continue
        prefix=value[:limitation.start()]
        if QUOTED.search(prefix)or re.search(r'\b(?:si|cuando|supongamos que)\s*$',prefix):continue
        context=source[max(0,at-220):at]+value[:limitation.end()]
        topics=list(re.finditer(r'\b(?:pago|pagar|cantidad|monto|pesos|convenio|whatsapp|'
            r'telefono|numero|folio|comprobante|cita|consulta medica)\b',context))
        if not topics or not FINANCIAL.fullmatch(topics[-1].group()):continue
        position=at+limitation.start()
        if any(e['position']==position for e in found):continue
        found.append({'position':position,'end':at+limitation.end(),'accepted':False,
            'declined':True,'conditional':False,'evidence':unit['text'],'reply':limitation.group(),
            'own_financial_response':True,'date_evidence':'',
            'method':'LIMITACION_PERSONAL_DE_PAGO_CON_PLAZO_EXPLICITO',
            'speaker_role':unit['speaker_role'],'human_verified':False,'acoustic_voice_identified':False})
    return found
