"""Dependencias de corroboración: evidencia inválida nunca es respaldo favorable."""


def unresolved_dependencies(metadata):
    context = metadata.get('context_audio_validation') or {}
    if not context.get('present') or context.get('valid'):
        return []
    required = set(context.get('required_findings') or [])
    required.update(metadata.get('context_recovery_requirements') or [])
    contact = metadata.get('contact_validation') or {}
    negotiation = metadata.get('negotiation_validation') or {}
    source = str(contact.get('source') or '')
    if source == 'LOCAL_AUDIO_CONTEXT':
        required.add('UNIDENTIFIED_CONTACT')
    if (negotiation.get('source') or '') == 'LOCAL_AUDIO_CONTEXT':
        required.add('NEGOTIATION_INVALID_OR_UNCERTAIN')
    unresolved = []
    for code in sorted(required):
        independent = False
        if code == 'UNIDENTIFIED_CONTACT':
            independent = bool(contact.get('confirmed') and source != 'LOCAL_AUDIO_CONTEXT')
        elif code in {'RECEIPT_UNCERTAIN'}:
            receipt = metadata.get('convenio_payment_validation') or {}
            independent = bool(receipt.get('receipt_request_evidence') and
                               not receipt.get('receipt_request_review_required') and
                               receipt.get('receipt_evidence_source') != 'LOCAL_AUDIO_CONTEXT')
        elif code in {'NEGOTIATION_INVALID_OR_UNCERTAIN', 'FINANCIAL_CONFIRMATION',
                      'PAYMENT_OUTCOME_NOT_CONFIRMED'}:
            independent = bool(negotiation.get('valid') and not negotiation.get('review_required')
                               and negotiation.get('amount_confirmed') and
                               negotiation.get('commitment_confirmed') and
                               negotiation.get('promise_date_confirmed_from_call') and
                               negotiation.get('source') != 'LOCAL_AUDIO_CONTEXT')
        elif code == 'UNCERTAIN_DISCLOSURE':
            privacy = metadata.get('privacy_validation') or {}
            independent = bool(not privacy.get('review_required') and
                               ((contact.get('confirmed') and source != 'LOCAL_AUDIO_CONTEXT')
                                or privacy.get('confirmed_disclosure')))
        elif code in {'STATUS_INVALID', 'STATUS_NOT_CONFIRMED'}:
            # La etiqueta puede resolverse independientemente. Nunca exime
            # las obligaciones financieras/de seguridad de la misma lista.
            status = metadata.get('status_validation') or {}
            independent = bool(status.get('detection_confidence') == 'ALTA' and
                               status.get('evidence') and not status.get('review_required'))
        elif code=='ARCO_INCOMPLETE':
            arco=metadata.get('arco_validation')or{}
            independent=bool(arco.get('valid')and arco.get('complete_procedure')and
                             arco.get('source')!='LOCAL_AUDIO_CONTEXT')
        elif code=='RECOVERED_AMOUNT_UNVERIFIED':
            review=metadata.get('amount_recovery_validation')or{}
            independent=bool(review.get('human_review_record')and review.get('valid')and
                             not review.get('review_required'))
        if not independent:
            unresolved.append(code)
    return unresolved


def confirmed_fact(context, rule):
    """Solo el validador vigente y una vinculación válida habilitan consumo."""
    from app.services.context_fact_consensus import VALIDATOR_REVISION
    if not context.get('valid') or context.get('validator_revision') != VALIDATOR_REVISION:
        return None
    candidates=[]
    for group in context.get('fact_validations') or []:
        for result in group.get('rules') or []:
            if result['rule'] != rule:continue
            if result['state']in{'CONTRADICTORIO','DESCARTADO_CON_EVIDENCIA'}:
                return None
            if result['state']=='CONFIRMADO':candidates.append(result)
    if not candidates:return None
    from app.services.context_audio_recovery import digest
    values={digest(e['value'])for r in candidates for e in r['matching_evidence']}
    return candidates[0]if len(values)==1 else None


def annotate_decision(metadata, decision):
    """Explicar qué regla se resolvió, con qué hecho y qué bloqueos continúan."""
    context=metadata.get('context_audio_validation')or{}
    if not context.get('present'):return
    context['classification_after']=decision['clasificacion']
    context['decision_justification']=decision['motivo']
    remaining={f['code']for f in decision.get('decision_findings',[])if
               f['severity']in{'REVIEW','CRITICAL','PENDING_ALERT'}}
    consumed=[]
    receipt=metadata.get('convenio_payment_validation')or{}
    if receipt.get('receipt_evidence_source')=='LOCAL_AUDIO_CONTEXT':consumed.append(('RECEIPT_REQUEST','RECEIPT_UNCERTAIN'))
    if (metadata.get('arco_validation')or{}).get('source')=='LOCAL_AUDIO_CONTEXT':consumed.append(('ARCO','ARCO_INCOMPLETE'))
    if (metadata.get('contact_validation')or{}).get('source')=='LOCAL_AUDIO_CONTEXT':consumed.append(('IDENTITY','UNIDENTIFIED_CONTACT'))
    for group in context.get('fact_validations')or[]:
        for fact in group.get('rules')or[]:
            fact['resolves_codes']=[code for rule,code in consumed if rule==fact['rule']and code not in remaining]
            fact['blocking_effect']=('RESUELTO_POR_REGLA_ESPECIFICA'if fact['resolves_codes']else
                'CONSERVADO'if remaining else 'SIN_BLOQUEO_INDEPENDIENTE')
    context['remaining_blocking_codes']=sorted(remaining)
