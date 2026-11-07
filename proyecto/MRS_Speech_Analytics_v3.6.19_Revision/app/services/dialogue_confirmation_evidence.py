"""Confirmaciones de pago con objeto y fecha; nunca asigna voces humanas."""
import re
import unicodedata
from app.services.conversation_evidence import normalize,_role_at
from app.services.reported_payment_amounts import NUMBER,money_value

DATE=r'(?:hoy|manana|(?:el )?dia \d{1,2}|(?:el )?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo))'
BAD=r'\b(?:si pudiera|si tuviera|si consigo|si me da tiempo|a lo mejor|yo creo|no puedo|no tengo|no sabria|supongamos|por ejemplo|diga que|usted dijo)\b'

def future_confirmation_events(text,segments=()):
    source=normalize(text);found=[];unbound_amounts=[]
    patterns=[('IMPORTE_FINAL_CON_ACEPTACION',re.compile(
        r'\bseria (?:por|de) (?P<amount>'+NUMBER+r')[.!?]\s*'
        r'(?P<answer>(?:aja[, ]+)?esta bien|si[, ]+esta bien|de acuerdo)\b')),
      ('RESPUESTA_IMPORTE_Y_FECHA_FUTURA',re.compile(
        r'\b(?:me )?(?:podria|puede|puedes) confirmar (?:nada mas )?(?:el )?monto '
        r'que va a (?:realizar|pagar|depositar)[^?!]{0,30}que dia\?\s*'
        r'(?P<answer>(?:si[, ]+)?(?P<amount>'+NUMBER+r')[^.!?]{0,20}'+DATE+r')[.!?]')),
      ('CONFIRMACION_FECHA_PROPUESTA',re.compile(
        r'\b(?P<offer>vamos a (?:ponerlo|estar)|ponemos|contariamos con (?:su|el) pago)'
        r'[^?!]{0,55}'+DATE+r'[^?!]{0,30}(?:le parece bien)\?\s*'
        r'(?P<answer>(?:bueno[, ]+)?(?:si|esta bien|de acuerdo|correcto|perfecto|ok[, ]+muy bien))\b')),
      ('CONFIRMACION_FECHA_SIN_PUNTUACION_ASR',re.compile(
        r'\b(?:contariamos con|confirmamos) (?:su|el) pago para (?:el dia de |el dia )?'
        r'(?:hoy|manana)\s+(?P<answer>si[, ]+(?:perfecto|esta bien|de acuerdo))\b')),
      ('DECLARACION_FECHA_ACTUAL',re.compile(
        r'\b(?P<answer>(?:lo hago|lo realizo) el dia de hoy|'
        r'(?:hoy|manana) mismo lo (?:hago|realizo)|hoy mismo[^.!?]{0,90}termino de comer lo hago|pero manana queda(?: perfecto)?(?: claro que si)?)\b')),
    ]
    for method,pattern in patterns:
        for match in pattern.finditer(source):
            if method == 'DECLARACION_FECHA_ACTUAL':
                verbatim=re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(text)).lower()).strip()
                if re.search(r'\brealizó\b',verbatim[match.start():match.end()]):continue
            before=source[max(0,match.start()-240):match.start()]
            if method == 'DECLARACION_FECHA_ACTUAL' and re.search(
                    r'\b(?:no|nunca|jamas|si|cuando|para que|dijo que|usted dice que)\s*$', before):
                continue
            if method == 'DECLARACION_FECHA_ACTUAL' and (
                    source.rfind('¿',0,match.start()) > source.rfind('?',0,match.start())
                    or re.match(r'\s*\?',source[match.end():])):
                continue
            answer=match['answer'];after=source[match.end():match.end()+75].split('.')[0]
            if method == 'IMPORTE_FINAL_CON_ACEPTACION' and re.search(
                    r'\b(?:whatsapp|telefono|numero de convenio|clave|clabe|folio|referencia|comprobante)\b',before[-100:]):
                continue
            if (_role_at(text,segments,match.start('answer')) in {'GESTOR','TERCERO'}
                    or re.search(BAD,answer+' '+after)
                    or re.search(r'\b(?:dijo que|diga|por ejemplo|si pudiera|supongamos que)\b[^.!?]{0,55}$',before)
                    or re.search(r'\b(?:ayer|hizo|efectuado|realizado|recibido|reportado|comprobante|whatsapp|cita|consulta medica)\b',match.group())):
                continue
            financial_context=bool(re.search(r'\b(?:pago|pagar|deposito|convenio|cantidad|monto|pesos)\b',before+' '+match.group()))
            if not financial_context and method!='IMPORTE_FINAL_CON_ACEPTACION':continue
            record={'position':match.start('answer'),'evidence':match.group(),'method':method}
            if 'amount' in match.re.groupindex:
                record.update(amount=money_value(match['amount']),amount_position=match.start('amount'),
                              amount_end=match.end('amount'),amount_text=match['amount'])
            if financial_context:
                found.append(record)
            else:
                unbound_amounts.append(record)
    for record in unbound_amounts:
        parents=[e for e in found if e['method'].startswith('CONFIRMACION_FECHA')
                 and 0<record['position']-e['position']<=200]
        if parents:
            parent=max(parents,key=lambda e:e['position'])
            between=source[parent['position']:record['position']]
            if not re.search(r'\b(?:whatsapp|telefono|comprobante|cita|consulta|folio|referencia)\b',between):
                record['context_event_position']=parent['position']
                found.append(record)
    return found
