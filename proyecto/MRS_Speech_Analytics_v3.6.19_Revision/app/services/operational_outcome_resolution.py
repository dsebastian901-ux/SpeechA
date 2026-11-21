"""Resolución conservadora de estatus con evidencia del diálogo, no de Excel.

Reglas acordadas 21/nov/2026. Nunca certifica pago bancario, voces acústicas,
aprobaciones de calidad ni cifras no reconocidas por el titular.
"""
import re

from app.services.conversation_evidence import normalize, recipient_statement
from app.services.current_payment_amounts import explicit_current_amounts
from app.services.reported_payment_amounts import NUMBER, money_value


def amount_confirmed_for_agreement(text, segments, commitment, accepted_schedule=None):
    """No basta una fecha o un saldo informado para declarar CONVENIO.

    Requiere importe en una aceptación de pago o en la declaración final propia
    del titular. Se excluyen días, plazos, teléfonos y menciones históricas.
    """
    if not commitment.get('accepted'):
        return False
    if (accepted_schedule or {}).get('confirmed') and (accepted_schedule or {}).get('amounts'):
        return True
    accepted_methods={'IMPORTE_Y_FECHA_CONFIRMADOS','IMPORTE_EN_PREGUNTA_ACTUAL_ACEPTADA'}
    if any(e.get('amount') and e.get('method') in accepted_methods
           for e in explicit_current_amounts(text,segments)):
        return True
    evidence=normalize(commitment.get('evidence')or'')
    if re.search(r'\b(?:ayer|antier|ya pague|ya hice el pago|pago anterior|pago pasado)\b',evidence):
        return False
    # «Me comprometo a pagar mil pesos el 25» es una respuesta del titular.
    # «Pagar el día 25» no contiene importe.
    pattern=re.compile(r'\b(?:pagar|pagare|depositar|depositare|abonar|abonare|cubrir|'
        r'realizar (?:el |un |mi )?pago|hacer (?:el |un |mi )?pago)'
        r'\b[^.!?]{0,70}?(?<!\w)(?P<amount>'+NUMBER+r')(?!\w)')
    for match in pattern.finditer(evidence):
        if re.search(r'\b(?:dia|fecha|hasta el|para el|a las|el)\s*$',evidence[max(0,match.start('amount')-24):match.start('amount')]):
            continue
        after=evidence[match.end('amount'):match.end('amount')+30]
        if re.match(r'\s*(?:dias?|horas?|meses?|anos?|de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre))\b',after):
            continue
        value=money_value(match['amount'])
        if value is not None and value>=10:
            return True
    return False


def prior_agreement_breached(text,segments=()):
    """Declaración del titular de un convenio *anterior* incumplido."""
    pattern=(r'\b(?:no (?:pude|he podido|logre|cumpli|pague|realice|hice)\b'
        r'[^.!?]{0,85}\b(?:convenio|acuerdo|pago acordado|pago pendiente)|'
        r'incumpli (?:el |mi |ese )?(?:convenio|acuerdo)|'
        r'(?:se me|me) vencio (?:el |mi |ese )?(?:convenio|acuerdo)|'
        r'no cumpli (?:el |mi |ese )?(?:convenio|acuerdo))\b')
    return recipient_statement(text,segments,pattern)


def recipient_has_contact(text,segments=()):
    """El tercero afirma poseer el contacto vigente, sin inventar diez dígitos."""
    from app.services.message_dialogue_evidence import existing_callback_confirmation
    return bool(existing_callback_confirmation(text,segments))
