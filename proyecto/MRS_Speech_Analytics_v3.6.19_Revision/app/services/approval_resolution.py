"""Rechazo por puntaje independiente de dudas ordinarias de etiqueta/identidad."""

ORDINARY_PENALTIES={
    'PEN001','PEN_CONV_LUGARES','PEN_CONV_WHATSAPP','PEN007','PEN009','PEN_SIN_INTENTO_NEGOCIACION',
}


def ordinary_score_rejection(metadata, score, minimum_score, duration_seconds):
    """Resolver el rechazo ya determinado por el puntaje sin ocultar seguridad.

    Conserva toda observación pendiente. No confirma identidad, estatus, pago o
    voz. Una duda financiera, de privacidad, referencias, trato, recado o final
    de llamada mantiene REVISAR, incluso si el puntaje ya es insuficiente.
    """
    if float(score or 0)>=float(minimum_score):return False
    penalties=metadata.get('penalties') or []
    if not penalties or any(p.get('id') not in ORDINARY_PENALTIES for p in penalties):return False
    if not any(float(p.get('points') or 0)>0 for p in penalties):return False
    expected=max(0,100-sum(float(p.get('points') or 0) for p in penalties))
    if abs(expected-float(score or 0))>.01:return False
    if metadata.get('critical_failures'):return False
    if duration_seconds is not None and float(duration_seconds)<60:return False
    if (metadata.get('duration_validation') or {}).get('valid') is False:return False
    privacy=metadata.get('privacy_validation') or {}
    if privacy.get('review_required') or privacy.get('confirmed_disclosure'):return False
    card=metadata.get('card_validation') or {}
    if card.get('result')=='TARJETA INCORRECTA' or str(card.get('result') or '').startswith('REVISAR -'):return False
    negotiation=metadata.get('negotiation_validation') or {}
    if negotiation.get('valid') is False or negotiation.get('review_required') or negotiation.get('date_year_rollover_review'):return False
    arco=metadata.get('arco_validation') or {}
    if arco.get('applies') and not arco.get('valid'):return False
    checks=metadata.get('quality_checks') or {}
    if any(checks.get(k) for k in ['queja_maltrato_detectada','groseria_bloquea_aprobacion','espera_prolongada_detectada']):return False
    treatment=metadata.get('treatment_validation') or {}
    if any(treatment.get(k) for k in ['mistreatment_report_evidence','dismissive_review_required',
                                    'confrontation_review_required','hostile_interlocutor_review_required']):return False
    for key in ['audio_block_evidence_validation','family_contact_validation','recado_acceptance_validation',
                'privacy_disclosure_validation','home_warning_validation','home_recovery_warning',
                'account_source_validation','financial_review_validation','amount_recovery_validation',
                'call_end_validation','wait_validation']:
        value=metadata.get(key) or {}
        if value.get('review_required') or (value.get('quality') or {}).get('degraded'):return False
    return True
