"""Corroboración del cierre a partir de los mismos eventos del motor.

No vuelve a interpretar una frase unilateral del validador ni modifica estatus,
puntuación o seguridad. La aceptación entra por payment_commitment antes de
las validaciones financieras y la decisión final.
"""
import re
from app.services.conversation_evidence import normalize, payment_commitment
from app.services.payment_lifecycle import financial_response_events
from app.services.reported_payment_amounts import money_value, NUMBER

_VALIDATION=re.compile(r'\b(?:area de validacion|pasar a validacion|validaciones)\b')
_AMOUNT=re.compile(r'\b(?:por la cantidad de|cantidad de|el monto es|seria el monto|por los?)\s+(?P<amount>'+NUMBER+r')(?:\s+pesos?)?\b')
_DATE=re.compile(r'\b(?:(?:el|para|al)\s+dia\s+(?:de\s+manana\s+)?\d{1,2}|dia\s+\d{1,2}|(?:el|para)\s+\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)|manana|hoy)\b')


def confirmed_validation_plan(text,segments=(),*,commitment=None):
    """API compatible; solo una respuesta inmediata acreditada del titular.

    Emplea los guardas comunes de citas, condiciones, interlocutor, cambio de
    objeto y revocación. Una etiqueta SPEAKER_00 no acredita el rol TITULAR.
    """
    none={'confirmed':False,'amount':None,'evidence':''}
    source=normalize(text);markers=list(_VALIDATION.finditer(source))
    if not markers:return none
    commitment=payment_commitment(text,segments)if commitment is None else commitment
    if not commitment.get('accepted'):return none
    for event in reversed(financial_response_events(text,segments)):
        if event['offer_position']<markers[-1].start()or event['speaker_role']!='TITULAR':continue
        # Si otra decisión sustituyó el acuerdo, no reciclar una confirmación vieja.
        if normalize(commitment.get('evidence'))!=normalize(event['evidence']):continue
        offer=event['offer'];amount=_AMOUNT.search(offer)
        if not amount:continue
        value=money_value(amount['amount']);day=_DATE.search(offer,amount.end())
        if value is None or value<=0 or not day:continue
        digits=re.search(r'\d+',day.group())
        if digits and not 1<=int(digits.group())<=31:continue
        return {'confirmed':True,'amount':float(value),'evidence':event['evidence'],
                'speaker_role':event['speaker_role'],'position':event['position'],
                'method':event['method'],'human_verified':False}
    return none
