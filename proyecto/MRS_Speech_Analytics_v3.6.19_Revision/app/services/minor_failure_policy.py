"""Faltas mínimas confirmadas el 23/11; nunca equivalen a aprobación.

La evidencia de origen y los descuentos permanecen en sus campos originales.
La incertidumbre sobre un importe/fecha no prueba incumplimiento de política.
"""
from datetime import date
import re


def reported_payment_is_prior_period(completed):
    """Un antecedente de otro periodo no sustituye la negociación actual."""
    from app.services.conversation_evidence import normalize
    reports = completed.get('evidence') or []
    pattern = r'\b(?:(?:el |la )?(?:mes|ano|anio|mensualidad) (?:pasad[oa]|anterior)|hace (?:dos|tres|\d+) (?:meses|anos))\b'
    return bool(reports and all(re.search(pattern, normalize(e.get('text') or '')) for e in reports))


def reported_payment_management(text, segments, *, applies, amount, minimum,
                                amount_review, receipt, proposals):
    # El lote contiene muchos recados y negociaciones nuevas. No recorrer
    # sus turnos otra vez para una regla de pago reportado que no les aplica.
    if not applies:
        return {'applies': False, 'amount_confirmed': bool(amount is not None and not amount_review),
                'reported_amount': amount, 'minimum': minimum, 'insufficient': False,
                'receipt_requested': bool(receipt.get('requested') or receipt.get('reported_sent')),
                'has_collection_action': False, 'collection_evidence': [], 'amount_question_evidence': [],
                'receipt_evidence': [], 'source': 'USER_DECISIONS_20261123', 'bank_payment_verified': False,
                'confirmed_receipt_only_shortfall': False, 'confirmed_receipt_only_without_amount': False,
                'confirmed_missing_receipt_request': False}
    from app.services.conversation_evidence import sentence_evidence, normalize
    def agent_evidence(pattern):
        evidence = []
        for unit in sentence_evidence(text, segments):
            if unit['speaker_role'] in {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}:
                continue
            value = normalize(unit['text'])
            for match in re.finditer(pattern, value):
                prefix = value[max(0, match.start()-90):match.start()]
                if re.search(r'\b(?:no|nunca|dice que|dijo que|diga que|repita que|por ejemplo|supongamos)\b[^.!?]{0,50}$', prefix):
                    continue
                evidence.append(dict(unit, phrase=match.group(), human_verified=False))
        return evidence
    actions = agent_evidence(
        r'\b(?:cuanto puede pagar|que cantidad puede|que dia puede pagar|cuando puede pagar|'
        r'puede (?:cubrir|completar|pagar|depositar)|podria (?:cubrir|completar|pagar|depositar)|'
        r'(?:tiene|tendria|tendriamos|necesita|necesitaria) que (?:realizar|aplicar|hacer|cubrir) (?:un |el |su )?(?:pago|deposito|abono)|'
        r'(?:le )?(?:ofrezco|propongo|ofrecemos|proponemos))\b[^.!?]*|'
        r'\b(?:diferencia|restante|resto|faltante)\b[^.!?]{0,65}\b(?:pagar|cubrir|completar|depositar)\b')
    amount_queries = agent_evidence(
        r'\b(?:cuanto (?:pago|deposito|abono)|(?:por )?que cantidad (?:pago|pagaron|realizo|deposito)|'
        r'de (?:que|cuanto) (?:cantidad|importe|monto)|por que cantidad)\b')
    known = bool(amount is not None and not amount_review)
    shortfall = bool(known and minimum is not None and minimum > 0 and amount + .009 < minimum)
    requested = bool(receipt.get('requested') or receipt.get('reported_sent'))
    attempted = bool(actions or proposals)
    result = {'applies': bool(applies), 'amount_confirmed': known,
              'reported_amount': amount, 'minimum': minimum,
              'insufficient': shortfall, 'receipt_requested': requested,
              'has_collection_action': attempted, 'collection_evidence': actions,
              'amount_question_evidence': amount_queries,
              'receipt_evidence': receipt.get('request_evidence', []) + receipt.get('reported_sent_evidence', []),
              'source': 'USER_DECISIONS_20261123', 'bank_payment_verified': False,
              'confirmed_receipt_only_shortfall': False,
              'confirmed_receipt_only_without_amount': False,
              'confirmed_missing_receipt_request': False}
    if applies and not amount_review and not receipt.get('review_required'):
        result['confirmed_receipt_only_shortfall'] = bool(shortfall and requested and not attempted)
        result['confirmed_receipt_only_without_amount'] = bool(not known and requested and not attempted and not amount_queries)
        result['confirmed_missing_receipt_request'] = bool(known and not requested)
    return result


def confirmed_minor_failure(metadata):
    if metadata.get('quality_contact_type') != 'TITULAR':
        return None
    n = metadata.get('negotiation_validation') or {}
    plan=n.get('installment_validation')or{}
    dates=n.get('installment_dates')or[]
    complete_accepted_calendar=bool(n.get('multipago_detectado')and len(dates)==len(plan.get('amounts')or[])>=2
        and not plan.get('review_required')and all(d.get('method')=='CALENDARIO_ACEPTADO_CON_MES_FINAL_EXPLICITO'for d in dates))
    payment = n.get('reported_payment_management') or {}
    reasons = []
    codes = []
    if payment.get('confirmed_receipt_only_shortfall'):
        codes.append('REPORTED_PAYMENT_SHORTFALL_NOT_MANAGED')
        reasons.append('El pago reportado no cubre el mínimo; solo se solicitó comprobante sin gestionar la diferencia.')
    if payment.get('confirmed_receipt_only_without_amount'):
        codes.append('REPORTED_PAYMENT_AMOUNT_NOT_CONFIRMED')
        reasons.append('Se solicitó únicamente comprobante sin confirmar cuánto pagó el titular.')
    if payment.get('confirmed_missing_receipt_request'):
        codes.append('REPORTED_PAYMENT_RECEIPT_NOT_REQUESTED')
        reasons.append('Se confirmó el importe reportado, pero no se solicitó el comprobante del pago.')
    # No convertir una segunda exhibición, una fecha ambigua ni un monto
    # dudoso en una falta confirmada. PEN005 por vencimiento sigue intacta.
    if (n.get('financial_validation_applicable') and not n.get('review_required')
            and n.get('payment_date_confirmed') and n.get('commitment_confirmed')
            and n.get('amount_confirmed') and not n.get('date_year_rollover_review')
            and not n.get('payment_confirmation_case') and (not n.get('multipago_detectado')or complete_accepted_calendar)
            and not (n.get('accepted_schedule') or {}).get('confirmed')
            and not (n.get('installment_window') or {}).get('applies')
            and (n.get('commitment_evidence') or {}).get('accepted')
            and not n.get('datos_saldo_inconsistentes') and not n.get('monto_normalizado_asr')):
        try:
            promised = date.fromisoformat(str(n['promise_date'])[:10])
            maximum = date.fromisoformat(str(n['mora_payment_policy']['window_end'])[:10])
            if promised > maximum:
                codes.append('CONFIRMED_PAYMENT_DATE_OUTSIDE_POLICY')
                reasons.append(f'La fecha aceptada ({promised}) excede el plazo operativo autorizado ({maximum}); no es negativa del titular.')
        except (ValueError, KeyError, TypeError):
            pass
    if not codes:
        return None
    return {'rule_group': 12, 'code': 'CONFIRMED_MINOR_FAILURE',
            'detail_codes': codes, 'severity': 'CONFIRMED_NONCRITICAL',
            'source_field': 'negotiation_validation', 'reasons': reasons,
            'resolves_codes': ['NEGOTIATION_INVALID_OR_UNCERTAIN', 'NO_COLLECTION_ATTEMPT'],
            'source': 'USER_DECISIONS_20261123', 'human_verified': False}
