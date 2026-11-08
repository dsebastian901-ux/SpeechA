"""Dictaminación común con evaluación explícita de los trece grupos de reglas.

Un descuento, una duda y una falta crítica no son intercambiables. Esta puerta
se usa tanto al procesar audio como al reanalizar y exportar resultados.
"""
from app.services.approval_resolution import ordinary_score_rejection

RULES = (
    (1, 'Dictaminación'), (2, 'RECADO REF1 / REF2'), (3, 'Privacidad PEN003'),
    (4, 'Interlocutor y aceptación'), (5, 'Tarjeta y referencia'), (6, 'Derechos ARCO'),
    (7, 'Lugares de pago'), (8, 'Amenazas y visitas'), (9, 'Lenguaje ofensivo'),
    (10, 'Hostilidad y profesionalismo'), (11, 'Quejas de atención previa'),
    (12, 'Negociación, montos y fechas'), (13, 'Clasificación final'),
)


def evaluate_quality(metadata, score, minimum_score=80, duration_seconds=None, base_classification=None):
    m = metadata if isinstance(metadata, dict) else {}
    score = round(float(score or 0), 2)
    checks = m.get('quality_checks') or {}
    penalties = m.get('penalties') or []
    failures = m.get('critical_failures') or []
    status = m.get('status_validation') or {}
    negotiation = m.get('negotiation_validation') or {}
    treatment = m.get('treatment_validation') or {}
    findings = []

    def add(domain, code, reasons, source, severity='REVIEW'):
        if isinstance(reasons, str):
            reasons = [reasons]
        details = list(dict.fromkeys(str(r) for r in reasons if r))
        if details:
            findings.append({'rule_group':domain, 'code':code, 'severity':severity,
                             'source_field':source, 'reasons':details})

    def pending(domain, field, code, fallback):
        value = m.get(field) or {}
        if value.get('review_required'):
            add(domain, code, value.get('reason') or value.get('reasons') or fallback, field)

    arco = m.get('arco_validation') or {}
    if arco.get('applies') and not arco.get('valid'):
        add(6, 'ARCO_INCOMPLETE', arco.get('reasons') or ['Procedimiento ARCO incompleto; requiere revisión.'], 'arco_validation')
    for domain, field, code, message in [
        (2,'family_contact_validation','FAMILY_CONFIRMATION','Confirmación de parentesco pendiente de revisión.'),
        (4,'recado_acceptance_validation','RECADO_CONFIRMATION','Confirmación de aceptación del recado pendiente.'),
        (4,'contact_conflict_validation','CONTACT_CONTRADICTION','Respuestas contradictorias sobre el interlocutor.'),
        (4,'message_delivery_validation','CALLBACK_NOT_DELIVERED','Contacto ofrecido sin entrega detectada.'),
        (3,'privacy_disclosure_validation','DISCLOSURE_CONFIRMATION','Confirmación de divulgación pendiente de revisión.'),
        (8,'home_warning_validation','WARNING_CONFIRMATION','Confirmación de advertencia pendiente.'),
        (5,'account_source_validation','ACCOUNT_SOURCE','Datos de cuenta inconsistentes; revisar nombre de salida'),
        (12,'financial_review_validation','FINANCIAL_CONFIRMATION','Confirmación financiera pendiente de revisión'),
        (13,'call_end_validation','CALL_END','Silencio o finalización sin responsable confirmado; revisar audio'),
    ]:
        pending(domain, field, code, message)
    additional = m.get('audio_block_evidence_validation') or {}
    if additional.get('review_required'):
        only_profanity = additional.get('valid') and additional.get('risks') and all(
            r.get('type') == 'EXPRESION_OFENSIVA_SIN_HABLANTE_CONFIRMADO' for r in additional['risks'])
        add(9 if only_profanity else 13, 'ADDITIONAL_AUDIO_EVIDENCE',
            'Lenguaje ofensivo requiere revisión' if only_profanity else
            additional.get('reason') or 'Lectura adicional pendiente de revisión.', 'audio_block_evidence_validation')
    payment = m.get('convenio_payment_validation') or {}
    if payment.get('receipt_request_review_required'):
        add(12,'RECEIPT_UNCERTAIN','Posible solicitud de comprobante deformada por ASR; confirmar frase, sin atribuir omisión.', 'convenio_payment_validation')
    if negotiation.get('liquidation_offer_review_required'):
        add(12,'LIQUIDATION_UNATTRIBUTED','Posible liquidación total sin atribución u oferta confirmada; revisar audio','negotiation_validation')
    if (m.get('home_recovery_warning') or {}).get('review_required'):
        add(8,'HOME_WARNING_UNATTRIBUTED','Posible advertencia de recuperación en domicilio en 1–2 PV; confirmar voz y frase en audio.','home_recovery_warning')
    if (m.get('amount_recovery_validation') or {}).get('review_required'):
        add(12,'RECOVERED_AMOUNT_UNVERIFIED','Importe recuperado por lecturas adicionales de audio; conserva revisión de evidencia','amount_recovery_validation')
    if m.get('quality_contact_type') == 'CONTACTO NO DETERMINADO':
        add(4,'UNIDENTIFIED_CONTACT','Interlocutor sin identificar; requiere revisión','quality_contact_type')
    if any(isinstance(f,dict) and f.get('invalidates') is True for f in failures):
        add(13,'CONFIRMED_CRITICAL_FAILURE','Incumplimiento crítico confirmado','critical_failures','CRITICAL')
    critical_domains={'PEN003':3,'PEN004':12,'PEN005':12,'PEN012':8}
    for failure in failures:
        if isinstance(failure,dict) and failure.get('invalidates') is True and failure.get('id') in critical_domains:
            add(critical_domains[failure['id']],'CRITICAL_'+failure['id'],failure.get('reason') or failure['id'], 'critical_failures','CRITICAL')
    privacy = m.get('privacy_validation') or {}
    if privacy.get('confirmed_disclosure'):
        add(3,'CONFIRMED_DISCLOSURE',privacy.get('reason') or 'Divulgación confirmada a un tercero','privacy_validation','CRITICAL')
    elif privacy.get('review_required'):
        add(3,'UNCERTAIN_DISCLOSURE',privacy.get('reason') or 'Posible divulgación pendiente de atribución','privacy_validation')
    card = m.get('card_validation') or {}
    if card.get('result') == 'TARJETA INCORRECTA' or str(card.get('result') or '').startswith('REVISAR -'):
        add(5,'CARD_REFERENCE',card.get('reason') or 'Referencia de tarjeta pendiente de validación','card_validation')
    ids = {p.get('id') for p in penalties if isinstance(p,dict)}
    if 'PEN_SIN_INTENTO_NEGOCIACION' in ids:
        add(12,'NO_COLLECTION_ATTEMPT','No se confirmó intento de negociación con el titular','penalties')
    if status.get('excel_status') and status.get('matches') is None:
        add(1,'STATUS_NOT_CONFIRMED','Estatus de Excel sin coincidencia confirmada; requiere revisión','status_validation')
    if status.get('valid') is False:
        add(1,'STATUS_INVALID',status.get('reasons') or ['Estatus pendiente de validación'],'status_validation')
    if ids & {'PEN_CONV_FRAUDE','PEN_CONV_TRANSFER_REV'}:
        add(12,'PAYMENT_DESTINATION','Método o datos de pago requieren revisión de seguridad','convenio_payment_validation')
    if checks.get('queja_maltrato_detectada') or treatment.get('mistreatment_report_evidence') or 'PEN_QUEJA_MALTRATO' in ids:
        add(11,'MISTREATMENT_REPORT','Queja de atención o maltrato requiere revisión, aunque supere el puntaje mínimo','treatment_validation')
    if negotiation.get('valid') is False or negotiation.get('review_required'):
        add(12,'NEGOTIATION_INVALID_OR_UNCERTAIN',negotiation.get('reasons') or ['Negociación pendiente de validación'],'negotiation_validation')
    if checks.get('groseria_bloquea_aprobacion') or 'PEN_GROSERIA_SIN_ATRIBUCION' in ids:
        add(9,'OFFENSIVE_LANGUAGE','Lenguaje ofensivo requiere revisión','treatment_validation')
    waiting = m.get('wait_validation') or {}
    if waiting.get('review_required') or checks.get('espera_prolongada_detectada') or 'PEN_ESPERA_PROLONGADA' in ids:
        add(11,'WAIT_WITHOUT_RESUMPTION',waiting.get('reason') or 'Espera de 65 segundos o más sin retoma confirmada; revisar audio.','wait_validation')
    for field, code, reason in [
        ('dismissive_review_required','DISMISSIVE_CONDUCT','Expresión despectiva o confrontativa; revisar emisor y contexto'),
        ('confrontation_review_required','UNCERTAIN_CONFRONTATION','Confrontación sin hablante confirmado; requiere revisión'),
        ('hostile_interlocutor_review_required','HOSTILE_RECIPIENT','Hostilidad del interlocutor requiere validación'),
    ]:
        if treatment.get(field):
            add(10,code,reason,'treatment_validation')
    if duration_seconds is not None and float(duration_seconds) < 60:
        add(13,'SHORT_DURATION','Duración inferior a 60 segundos','duration_seconds')
    duration = m.get('duration_validation') or {}
    if duration.get('valid') is False:
        add(13,'INVALID_DURATION',duration.get('reason') or 'Duración fuera del rango permitido','duration_validation')

    from app.services.status_output_label import corrected_status_label
    output_label = corrected_status_label(m)
    if output_label['valid']:
        # La discrepancia permanece documentada; solo se resuelve el motivo
        # de etiqueta. Las demás dudas conservan toda su prioridad.
        for finding in findings:
            if finding['code']=='STATUS_INVALID':
                finding['severity']='CORRECTED_STATUS'

    exception = m.get('hostile_interlocutor_exception') or {}
    verified_exception = all(exception.get(k) is True for k in
        ('audio_verified','interlocutor_hostile_or_lascivious','prevented_script','agent_professional'))
    exception_codes = {'OFFENSIVE_LANGUAGE','HOSTILE_RECIPIENT'}
    # Una lectura adicional de grosería solo es dispensable si esa es la única
    # duda de la lectura; jamás exime privacidad, referencias ni quejas previas.
    if verified_exception:
        for finding in findings:
            if finding['code'] in exception_codes or (finding['code']=='ADDITIONAL_AUDIO_EVIDENCE' and finding['rule_group']==9):
                finding['severity'] = 'VALIDATED_EXCEPTION'
    blocking = [f for f in findings if f['severity'] in {'REVIEW','CRITICAL'}]
    critical = any(f['severity']=='CRITICAL' for f in blocking)
    score_ok = score >= float(minimum_score)
    base = base_classification or {}
    if critical:
        category = 'FALLA_GRAVE'
    elif verified_exception and score_ok and not blocking:
        category = 'APROBADO_ETIQUETA_CORREGIDA' if output_label['valid'] else 'APROBADO_CON_EXCEPCION'
    elif not score_ok and ordinary_score_rejection(m,score,minimum_score,duration_seconds):
        category = 'NO_APROBADO_MENOR_80'
    elif blocking:
        category = 'REVISAR'
    elif not score_ok:
        category = 'NO_APROBADO_MENOR_80'
    elif output_label['valid']:
        category = 'APROBADO_ETIQUETA_CORREGIDA'
    elif base.get('estatus_autorizado') is False:
        category = 'APROBADO_SIN_ETIQUETAR'
    elif base.get('estatus_autorizado') is True and base.get('tiene_nombre_final') is False:
        add(13,'OUTPUT_NAME_MISSING','Falta nombre final para reetiquetar','base_classification')
        blocking = [f for f in findings if f['severity'] in {'REVIEW','CRITICAL'}]
        category = 'REVISAR'
    else:
        category = 'APROBADO'
    reasons = list(dict.fromkeys(r for f in blocking for r in f['reasons']))
    if category == 'NO_APROBADO_MENOR_80' and reasons:
        reasons.insert(0,'Puntaje inferior al mínimo por incumplimientos ordinarios; rechazo automático. Las observaciones pendientes se conservan.')
    # Los descuentos se conservan como evidencia, sin convertirlos de nuevo
    # en bloqueos. Es esencial para omisión de dos lugares con 80 puntos.
    for penalty in penalties:
        if not isinstance(penalty,dict):
            continue
        domain = 7 if penalty.get('id')=='PEN_CONV_LUGARES' else 12 if penalty.get('category')=='Negociación' else 13
        add(domain,'DEDUCTION_'+str(penalty.get('id')),penalty.get('reason') or penalty.get('id'), 'penalties','DEDUCTION')
    applicability = {2:bool(status.get('recado_evidence')),6:bool(arco.get('applies')),
                     7:bool(payment.get('applies')),10:bool(verified_exception or any(f['rule_group']==10 for f in findings))}
    evaluations = []
    for number, label in RULES:
        relevant = [f for f in findings if f['rule_group']==number]
        state = ('INCUMPLIMIENTO_CRITICO' if any(f['severity']=='CRITICAL' for f in relevant) else
                 'REQUIERE_REVISION' if any(f['severity']=='REVIEW' for f in relevant) else
                 'EXCEPCION_VALIDADA' if any(f['severity']=='VALIDATED_EXCEPTION' for f in relevant) else
                 'ETIQUETA_CORREGIDA' if any(f['severity']=='CORRECTED_STATUS' for f in relevant) else
                 'DESCUENTO_APLICADO' if relevant else
                 'NO_APLICA' if applicability.get(number) is False else
                 'SIN_HALLAZGOS' if m else 'NO_EVALUADO')
        evaluations.append({'id':number,'rule':label,'state':state,'finding_codes':[f['code'] for f in relevant]})
    return {'clasificacion':category, 'aprobado':category in {'APROBADO','APROBADO_ETIQUETA_CORREGIDA'},
            'calidad_aprobada':category.startswith('APROBADO'), 'score':score,'puntaje_minimo':minimum_score,
            'cumple_puntaje':score_ok,'rechazo_automatico_por_puntaje':category=='NO_APROBADO_MENOR_80',
            'observaciones_conservadas':reasons,
            'motivo':('Excepción por hostilidad validada en audio; gestor profesional' if category=='APROBADO_CON_EXCEPCION' else
                      ' | '.join(reasons) if reasons else 'Cumple calidad y seguridad; etiqueta corregida en copia separada' if category=='APROBADO_ETIQUETA_CORREGIDA' else 'Cumple reglas de aprobación' if score_ok else 'Puntaje inferior al mínimo'),
            'decision_findings':findings,'rule_evaluation':evaluations,
            'output_label_correction':output_label,'decision_policy':'THIRTEEN_RULE_GROUPS_V1'}
