"""Importes expresamente confirmados o explicados; no se completan con Excel."""
import re
from app.services.conversation_evidence import normalize
from app.services.dialogue_confirmation_evidence import future_confirmation_events
from app.services.reported_payment_amounts import NUMBER,money_value

def explicit_current_amounts(text,segments=()):
    source=normalize(text)
    events=[dict(e,method='IMPORTE_Y_FECHA_CONFIRMADOS') for e in future_confirmation_events(text,segments) if e.get('amount')]
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
