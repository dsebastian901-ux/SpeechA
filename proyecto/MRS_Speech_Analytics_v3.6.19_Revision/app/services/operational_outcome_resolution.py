"""Resolución conservadora de estatus con evidencia del diálogo, no de Excel.

Reglas acordadas 21/nov/2026. Nunca certifica pago bancario, voces acústicas,
aprobaciones de calidad ni cifras no reconocidas por el titular.
"""
import re

from app.services.conversation_evidence import normalize, recipient_statement, sentence_evidence
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


def offered_payment_alternatives(text,segments=(),before_hangup=False):
    """Ofertas del gestor realmente expresadas, no la palabra «convenio».

    No cuenta el saldo, el simple relato de un convenio incumplido o una
    pregunta del titular. Ante cuelgue solo cuentan ofertas anteriores.
    """
    source=normalize(text)
    marker=re.search(r'\b(?:voy a colgar|ya le voy a colgar|te voy a colgar|yo le cuelgo)\b',source)
    limit=marker.start() if before_hangup and marker else len(source)
    patterns=(
        r'\b(?:le (?:ofrezco|ofrecemos|propongo|proponemos)\b[^.!?]{0,80}\b(?:pago|abono|convenio|alternativa)|'
        r'(?:otra|una|dos|tres|varias) (?:alternativas?|opciones?) (?:de )?pago|'
        r'(?:podemos|podriamos) (?:hacer|generar|ofrecer|formalizar) (?:un |el |su )?(?:convenio|acuerdo|pago)|'
        r'(?:puede|podria|podriamos|podemos) (?:realizar|hacer|depositar|pagar|abonar|cubrir)\b[^.!?]{0,85}\b(?:pago|abono|pesos|manana|hoy|dia)|'
        # Preguntar cuánto o cuándo NO constituye una alternativa ofrecida.
        # Mencionar el pago mínimo sí es una opción de cobranza.
        r'(?:puede|podria|debe) (?:realizar|cubrir|pagar) (?:su |el |un )?pago minimo|'
        r'(?:el |su )?pago minimo (?:es|seria|se puede realizar)|'
        r'(?:podemos contar con|contariamos con) (?:su |el )?pago)'
    )
    cursor=0
    for unit in sentence_evidence(text,segments):
        fragment=normalize(unit.get('text')or'')
        position=source.find(fragment,cursor)
        if position<0:continue
        cursor=position+len(fragment)
        if position>=limit or unit.get('speaker_role') in {'TITULAR','TERCERO','INTERLOCUTOR'}:
            continue
        for match in re.finditer(patterns,fragment):
            if position+match.start()>=limit:continue
            before=fragment[max(0,match.start()-75):match.start()]
            if re.search(r'\b(?:no|nunca|dijo que|dice que|por ejemplo|supongamos que)\s*$',before):
                continue
            return {'confirmed':True,'evidence':unit['text'],'position':position+match.start()}
    return {'confirmed':False,'evidence':'','position':None}
