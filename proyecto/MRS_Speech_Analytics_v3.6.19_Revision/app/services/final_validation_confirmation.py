"""Evidencia explícita de monto y fecha en el cierre de validación.

No acredita el pago bancario ni sustituye la validación de convenio,
plazo, seguridad, privacidad o atribución acústica.
"""
import re
from app.services.conversation_evidence import normalize
from app.services.reported_payment_amounts import money_value, NUMBER

_VALIDATION = re.compile(r'\b(?:area de validacion|del area de validacion|al area de validacion|pasar a validacion|validaciones)\b')
_FIRM = re.compile(r'\b(?:queda confirmado|quedamos entonces|confirmo (?:su |el )?pago|seria el monto|el monto es)\b')
_DATE = re.compile(r'\b(?:(?:el|para|al)\s+dia\s+(?:de\s+manana\s+)?\d{1,2}|dia\s+\d{1,2}|(?:el|para)\s+\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)|manana|hoy)\b')
_AMOUNT = re.compile(r'\b(?:por la cantidad de|cantidad de|el monto es|seria el monto|por los?)\s+(?P<amount>' + NUMBER + r')(?:\s+pesos?)?\b')
_NEGATED = re.compile(r'\b(?:no quedo confirmado|no confirmo el pago|se cancela el compromiso|no voy a pagar|no pagare)\b')


def confirmed_validation_plan(text):
    """Detecta recapitulación FINAL con importe y fecha expresos.

    La evidencia es SOLO para cotejar el estatus operativo: no autoriza
    aprobación, no infiere año, ni elimina dudas financieras o de seguridad.
    """
    source = normalize(text or '')
    markers = list(_VALIDATION.finditer(source))
    if not markers:
        return {'confirmed': False, 'amount': None, 'evidence': ''}
    tail = source[markers[-1].start():]
    # Una pregunta, la lectura unilateral del gestor o la mención de una fecha
    # NO constituyen un compromiso. Exigir respuesta afirmativa atribuida al
    # titular, posterior a los términos y dentro de la misma recapitulación.
    if re.search(r'\b(?:no voy a pagar|no pagare|se cancela el compromiso|no acepto|no confirmo)\b', tail):
        return {'confirmed': False, 'amount': None, 'evidence': ''}
    for anchor in reversed(list(_FIRM.finditer(tail))):
        phrase = tail[anchor.start():anchor.start()+230]
        if _NEGATED.search(phrase):
            continue
        match = _AMOUNT.search(phrase)
        if not match:
            continue
        amount = money_value(match['amount'])
        if amount is None or float(amount) <= 0:
            continue
        date_match = _DATE.search(phrase[match.end():match.end()+95])
        if not date_match:
            continue
        # El 'sí' debe venir DESPUÉS de la fecha y pertenecer al titular.
        # No asumir identidad a partir del mero texto de una pregunta.
        response = phrase[match.end()+date_match.end():]
        if not re.search(r'\b(?:titular|cliente|deudor)\s*:\s*(?:si|correcto|de acuerdo|acepto|confirmo)\b', response):
            continue
        return {'confirmed': True, 'amount': float(amount), 'evidence': phrase[:175]}
    return {'confirmed': False, 'amount': None, 'evidence': ''}
