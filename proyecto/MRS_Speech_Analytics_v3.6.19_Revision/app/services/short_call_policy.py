"""Excepción de duración con evidencia positiva de gestión completa."""


def management_completeness(metadata, label=None):
    m=metadata or {};status=m.get('status_validation')or{};n=m.get('negotiation_validation')or{}
    result={'complete':False,'workflow':status.get('detected_status')or'',
            'reasons':[],'evidence':status.get('evidence')or'', 'human_verified':False}
    if (m.get('death_followup_validation')or{}).get('valid'):
        result['complete']=True;result['workflow']='SEGUIMIENTO_DOCUMENTAL_DEFUNCION'
        return result
    from app.services.status_output_label import confirmed_status_without_label
    known=status.get('valid')is True or (label or{}).get('valid')is True or confirmed_status_without_label(m, label).get('eligible')is True
    if not known or not status.get('evidence'):
        result['reasons'].append('No se confirmó con evidencia el estatus de la gestión breve.')
        return result
    workflow=status.get('detected_status')or status.get('excel_status')or''
    if workflow=='NO CONOCEN A DEUDOR':
        result['complete']=bool((m.get('arco_validation')or{}).get('valid'))
    elif workflow.startswith('MENSAJE ') or workflow in {'RECADO REF1','RECADO REF2'}:
        result['complete']=bool(str(status.get('evidence_method')or'').startswith('RECADO_ACEPTADO')
            and not(m.get('message_delivery_validation')or{}).get('review_required'))
    elif workflow == 'SE NIEGAN A TOMAR RECADO':
        result['complete'] = bool((m.get('explicit_message_refusal') or {}).get('confirmed'))
    elif n.get('payment_followup_case'):
        result['complete']=bool(n.get('prior_payment_covers_minimum') and (m.get('convenio_payment_validation')or{}).get('requests_payment_receipt'))
        # El extractor conserva las solicitudes y los reportes enviados en
        # quality_checks y en la evidencia del comprobante según el flujo.
        if not result['complete']:
            receipt=m.get('receipt_assessment')or{}
            result['complete']=bool(n.get('prior_payment_covers_minimum') and(receipt.get('requested')or receipt.get('reported_sent')))
    elif workflow=='CONVENIO':
        result['complete']=bool(n.get('commitment_evidence',{}).get('accepted')
            and n.get('promise_date_confirmed_from_call') and n.get('amount_confirmed'))
    elif workflow in {'NO DEFINE FECHA DE PAGO','NEGATIVA DE PAGO'}:
        result['complete']=bool(n.get('negotiation_attempt_detected'))
    elif workflow=='ACLARACION':
        result['complete']=bool(status.get('detection_confidence')=='ALTA' and status.get('evidence_method'))
    if not result['complete']:
        result['reasons'].append('Falta confirmar un elemento obligatorio del flujo breve; la duración por sí sola no autoriza aprobar.')
    end=m.get('call_end_validation')or{}
    if end.get('review_required'):
        result['complete']=False;result['reasons'].append('El cierre de la llamada requiere aclaración.')
    return result
