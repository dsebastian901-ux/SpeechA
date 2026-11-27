"""Reaplicar controles MRS al contexto que aporta un plan recuperado.

Un fragmento no contiene necesariamente la apertura ni todo el guion. Sus
omisiones no generan descuentos nuevos; sus instrucciones y riesgos explícitos
sí impiden consumir solamente la parte favorable de la lectura.
"""


def financial_context_risks(text,relation):
    from app.services.analytics_service import AnalyticsService as A
    from app.services.operational_script_evidence import receipt_request_evidence
    # Se hereda únicamente el contacto ya acreditado en la llamada original.
    # No es una voz nueva, una lectura ni una confirmación humana inventada.
    context=dict(relation or{},_context_audio_validation={
        'valid':True,'holder':True,'evidence':[]})
    r=A.calculate_basic_compliance(text,context)
    n=r.get('negotiation_validation')or{}
    codes=[]
    for p in r.get('penalties')or[]:
        if ((p.get('invalidates')and p.get('id')!='PEN005')or p.get('id')in{
            'PEN006','PEN_CONV_TRANSFER_REV','PEN_QUEJA_MALTRATO','PEN_GROSERIA_SIN_ATRIBUCION'}):
            codes.append(p['id'])
    card=r.get('card_validation')or{}
    if str(card.get('result')or'').startswith('REVISAR')or card.get('result')=='TARJETA INCORRECTA':
        codes.append('REFERENCIA_NO_VALIDADA')
    if n.get('liquidation_offer_review_required')or(n.get('liquidation_detected')and not n.get('liquidation_allowed')):
        codes.append('LIQUIDACION_NO_CORROBORADA_O_NO_AUTORIZADA')
    if n.get('multipago_detectado')or(n.get('installment_validation')or{}).get('review_required'):
        codes.append('PLAN_COMPLEJO_REQUIERE_VALIDACION_COMPLETA')
    if any(t in str(n.get('validacion_saldo_informado')or'')for t in ['REVISAR','INCORRECTO','DIFERENTE']):
        codes.append('SALDO_NO_VALIDADO')
    treatment=r.get('treatment_validation')or{}
    if any(treatment.get(k)for k in ['asset_pressure_review','mistreatment_report_evidence',
            'confrontation_review_required','dismissive_review_required','hostile_interlocutor_review_required']):
        codes.append('TRATO_REQUIERE_VALIDACION')
    receipt=receipt_request_evidence(text)
    if receipt.get('withdrawal_evidence')and not(receipt.get('requested')or receipt.get('reported_sent')):
        codes.append('COMPROBANTE_RETIRADO_EN_RELECTURA')
    return sorted(set(codes))
