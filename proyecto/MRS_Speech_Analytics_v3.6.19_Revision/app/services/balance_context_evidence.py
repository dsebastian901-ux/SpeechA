"""Correcciones explícitas de saldo y separación de historia/ofertas, sin completar desde Excel."""
import re
from app.services.conversation_evidence import normalize, _role_at
from app.services.reported_payment_amounts import NUMBER, money_value


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
    if role in {'TITULAR','TERCERO','INTERLOCUTOR'}:
        return 'IMPORTE_DICHO_POR_INTERLOCUTOR'
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
