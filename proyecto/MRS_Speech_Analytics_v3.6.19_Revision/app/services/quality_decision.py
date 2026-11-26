"""Dictaminación común con evaluación explícita de los trece grupos de reglas.

Un descuento, una duda y una falta crítica no son intercambiables. Esta puerta
se usa tanto al procesar audio como al reanalizar y exportar resultados.
"""
import math
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
    if not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError('Puntaje de calidad inválido; debe ser finito y estar entre 0 y 100.')
    minimum_score=float(minimum_score)
    if not math.isfinite(minimum_score)or minimum_score<=0:
        raise ValueError('Puntaje mínimo inválido.')
    minimum_score=max(80.,minimum_score)
    no_voice=m.get('no_voice_validation') or {}
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

    if not m:
        add(13,'QUALITY_EVIDENCE_MISSING','No existe evaluación de las reglas; un puntaje aislado no acredita calidad.','metadata')
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
    context_audio=m.get('context_audio_validation')or{}
    from app.services.context_evidence_policy import unresolved_dependencies
    dependencies=unresolved_dependencies(m)
    if dependencies:
        add(13,'CONTEXT_AUDIO_REQUIRED_INVALID',
            'La corroboración acústica requerida no es válida; siguen pendientes: '+', '.join(dependencies),
            'context_audio_validation')
    if context_audio.get('review_required'):
        risks=context_audio.get('risks')or[]
        if any(r.get('type')=='INFORMACION_PROTEGIDA_SIN_VOZ_CONFIRMADA'for r in risks):
            add(3,'CONTEXT_AUDIO_PRIVACY_RISK','Información protegida en relectura local sin voz confirmada; verificar el fragmento.','context_audio_validation')
        if any(r.get('type')=='EXPRESION_OFENSIVA_SIN_VOZ_CONFIRMADA' for r in risks):
            add(9,'CONTEXT_AUDIO_RISK',context_audio.get('reason')or'Expresión ofensiva en relectura local pendiente de atribución.','context_audio_validation')
        if any(r.get('type')=='ADVERTENCIA_DOMICILIARIA_PENDIENTE' for r in risks):
            add(8,'CONTEXT_AUDIO_HOME_WARNING','Advertencia domiciliaria en relectura; confirmar emisor y política de mora.','context_audio_validation')
        if any(r.get('type')=='CONFRONTACION_PENDIENTE'for r in risks):
            add(10,'CONTEXT_AUDIO_CONFRONTATION','Expresión confrontativa en relectura; confirmar emisor y contexto.','context_audio_validation')
        if not risks:
            add(13,'CONTEXT_AUDIO_UNVERIFIED',context_audio.get('reason')or'Relectura focal pendiente de validación; no confirma por sí sola cumplimiento.','context_audio_validation')
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
        add(8,'HOME_WARNING_UNATTRIBUTED','Posible advertencia de recuperación en domicilio o bienes; confirmar voz y frase en audio.','home_recovery_warning')
    if (m.get('amount_recovery_validation') or {}).get('review_required'):
        add(12,'RECOVERED_AMOUNT_UNVERIFIED','Importe recuperado por lecturas adicionales de audio; conserva revisión de evidencia','amount_recovery_validation')
    if m.get('quality_contact_type') == 'CONTACTO NO DETERMINADO':
        add(4,'UNIDENTIFIED_CONTACT',(m.get('contact_validation')or{}).get('reason')or
            'Interlocutor sin identificar; requiere revisión','contact_validation')
    if any(isinstance(f,dict) and f.get('invalidates') is True for f in failures):
        add(13,'CONFIRMED_CRITICAL_FAILURE','Incumplimiento crítico confirmado','critical_failures','CRITICAL')
    if any(isinstance(p,dict) and p.get('invalidates') is True for p in penalties):
        add(13,'CONFIRMED_INVALIDATING_PENALTY','Penalización invalidante expresamente acreditada','penalties','CRITICAL')
    critical_domains={'PEN003':3,'PEN004':12,'PEN005':12,'PEN012':8}
    for failure in failures:
        if isinstance(failure,dict) and failure.get('invalidates') is True and failure.get('id') in critical_domains:
            add(critical_domains[failure['id']],'CRITICAL_'+failure['id'],failure.get('reason') or failure['id'], 'critical_failures','CRITICAL')
    privacy = m.get('privacy_validation') or {}
    guidance=(m.get('convenio_payment_validation')or{}).get('third_party_guidance')or{}
    if guidance.get('confirmed')or guidance.get('review_required'):
        add(3,'THIRD_PARTY_PAYMENT_GUIDANCE',guidance.get('reason'),'convenio_payment_validation')
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
    # Explicar el hecho pendiente. Una discrepancia de etiqueta por sí sola
    # no describe qué falta confirmar en un recado ni en una negociación.
    workflow=m.get('message_workflow_validation')or{}
    if (status.get('evidence_method')=='TERCERO_SIN_RECADO_CONFIRMADO'
            and not(m.get('explicit_message_refusal')or{}).get('confirmed')):
        if not workflow.get('recipient_accepted'):
            add(4,'MESSAGE_RECEIPT_NOT_CONFIRMED','El ASR no acredita una respuesta de recepción del recado; no basta el agradecimiento del gestor.','message_workflow_validation')
        if not workflow.get('directed_body'):
            add(4,'MESSAGE_BODY_NOT_CONFIRMED','No quedó acreditado el mensaje dirigido al titular ausente.','message_workflow_validation')
        if not workflow.get('callback_available')and not(m.get('message_delivery_validation')or{}).get('review_required'):
            add(4,'CALLBACK_NOT_CONFIRMED','El contacto no quedó completo en ASR ni fue confirmado expresamente como disponible; no completar dígitos por ecos.','message_workflow_validation')
    if (m.get('quality_contact_type')=='TITULAR' and status.get('evidence_method')=='SIN_EVIDENCIA'
            and status.get('matches')is None and negotiation.get('negotiation_attempt_detected')):
        add(12,'PAYMENT_OUTCOME_NOT_CONFIRMED','Se identifica al titular y una gestión de pago, pero no se acredita su resultado final: aceptación firme, negativa o decisión pendiente.','negotiation_validation')
    # No confirmar una reetiqueta NO DEFINE con fecha e importe presentes
    # si el Excel registra CONVENIO. La evidencia requiere reconciliación,
    # no aprobación automática con etiqueta corregida.
    if (status.get('excel_status') == 'CONVENIO'
            and status.get('detected_status') == 'NO DEFINE FECHA DE PAGO'
            and negotiation.get('amount_confirmed')
            and negotiation.get('payment_date_confirmed')
            and negotiation.get('promise_date')
            and negotiation.get('negotiation_attempt_detected')):
        add(1, 'CONVENIO_OUTCOME_CONFLICT',
            'La gestión contiene monto y fecha de pago, pero fue reetiquetada NO DEFINE: '
            'confirmar aceptación final y si corresponde CONVENIO antes de aprobar.',
            'status_validation')
    if treatment.get('asset_pressure_review'):
        add(10, 'ASSET_COERCION_REVIEW',
            treatment.get('asset_pressure_evidence') or
            'Posible presión para vender o empeñar bienes o penalidad adicional no corroborada; '
            'confirmar contexto y hablante.', 'treatment_validation')
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
    short_call=bool(duration_seconds is not None and 0<float(duration_seconds)<60)
    if duration_seconds is not None and (not math.isfinite(float(duration_seconds)) or float(duration_seconds)<=0):
        add(13,'INVALID_DURATION','La duración no es finita y positiva; comprobar el archivo de audio.','duration_seconds')
    duration = m.get('duration_validation') or {}
    if duration.get('valid') is False and not(short_call and duration.get('maximum_met',True)):
        add(13,'INVALID_DURATION',duration.get('reason') or 'Duración fuera del rango permitido','duration_validation')

    from app.services.status_output_label import corrected_status_label, confirmed_status_without_label
    output_label = corrected_status_label(m)
    pending_output_label = confirmed_status_without_label(m, output_label)
    from app.services.short_call_policy import management_completeness
    completeness=management_completeness(m,output_label)if short_call else{}
    if short_call and not completeness.get('complete'):
        add(13,'SHORT_MANAGEMENT_INCOMPLETE',completeness['reasons'],'management_completeness')
    if output_label['valid']:
        # La discrepancia permanece documentada; solo se resuelve el motivo
        # de etiqueta. Las demás dudas conservan toda su prioridad.
        for finding in findings:
            if finding['code']=='STATUS_INVALID':
                finding['severity']='CORRECTED_STATUS'
    elif pending_output_label['eligible']:
        for finding in findings:
            if finding['code'] == 'STATUS_INVALID':
                finding['severity'] = 'OUTPUT_LABEL_PENDING'

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
    # Criterio 78: tras dos ventanas ASR usables y con riesgo EXCLUSIVAMENTE
    # ofensivo sin emisor confirmado, no convertir incertidumbre en infracción.
    # El dictamen aprobado lleva ALERTA visible. No exime privacidad, maltrato,
    # amenazas, importe ni otras alertas independientes.
    audio_quality=additional.get('quality')or{}
    risks=additional.get('risks')or[]
    second_listening_offensive_only=bool(
        additional.get('valid') and additional.get('second_listening_complete')
        and not audio_quality.get('degraded') and risks
        and all(r.get('type')=='EXPRESION_OFENSIVA_SIN_HABLANTE_CONFIRMADO' for r in risks)
        and score>=float(minimum_score))
    if second_listening_offensive_only:
        allowed={'OFFENSIVE_LANGUAGE','ADDITIONAL_AUDIO_EVIDENCE'}
        context_risks=(m.get('context_audio_validation')or{}).get('risks')or[]
        if context_risks and all(r.get('type')=='EXPRESION_OFENSIVA_SIN_VOZ_CONFIRMADA' for r in context_risks):
            allowed.add('CONTEXT_AUDIO_RISK')
        for finding in findings:
            if finding['code'] in allowed and finding['severity']=='REVIEW':
                finding['severity']='ALERTA_INFORMATIVA'
    # Criterio 141: la denuncia contra el gestor actual no constituye
    # por sí sola maltrato confirmado. Sólo ese hallazgo pasa a alerta;
    # privacidad, insultos confirmados y demás bloqueos siguen intactos.
    current_unverified_complaint=bool(
        treatment.get('current_agent_mistreatment_unverified')
        and not any(isinstance(f,dict) and f.get('invalidates')
                    for f in failures))
    if current_unverified_complaint:
        for finding in findings:
            if finding['code']=='MISTREATMENT_REPORT' and finding['severity']=='REVIEW':
                finding['severity']='ALERTA_INFORMATIVA'
    blocking = [f for f in findings if f['severity'] in {'REVIEW','CRITICAL'}]
    critical = any(f['severity']=='CRITICAL' for f in blocking)
    if no_voice.get('candidate') and not critical:
        return _no_voice_result(minimum_score)
    score_ok = score >= float(minimum_score)
    base = base_classification or {}
    from app.services.definitive_rejection import definitive_rejection
    rejection = definitive_rejection(m,findings,duration_seconds)
    from app.services.minor_failure_policy import confirmed_minor_failure
    minor_failure = confirmed_minor_failure(m)
    # Una falta mínima por plazo no puede cerrar una duda INDEPENDIENTE
    # de seguridad o presión al interlocutor.
    if minor_failure and any(f['code'] == 'ASSET_COERCION_REVIEW'
                             and f['severity'] == 'REVIEW' for f in findings):
        minor_failure = None
    score_rejection=bool(not score_ok and ordinary_score_rejection(m,score,minimum_score,duration_seconds))
    pending_alerts=[]
    if (rejection or minor_failure or score_rejection) and not critical:
        for finding in blocking:
            resolution = rejection or minor_failure
            if resolution and finding['code']in resolution.get('resolves_codes',[]):
                finding['severity']='CONFIRMED_NONCRITICAL'
                finding['resolved_by']=resolution['code']
            elif finding['code']in{'STATUS_INVALID','STATUS_NOT_CONFIRMED','SHORT_MANAGEMENT_INCOMPLETE'}:
                finding['severity']='OBSERVATION'
            else:
                finding['severity']='PENDING_ALERT';pending_alerts.append(dict(finding))
        if rejection:findings.append(rejection)
        if minor_failure:findings.append(minor_failure)
        blocking=[rejection]if rejection else [minor_failure]if minor_failure else[]
    if minor_failure and minor_failure not in findings:
        findings.append(minor_failure)
    if critical:
        category = 'FALLA_GRAVE'
    elif base.get('missing_excel_relation'):
        category = 'SIN_RELACION_EXCEL'
    elif rejection:
        category = 'NO_APROBADO'
    elif minor_failure:
        category = 'FALLA_MINIMA'
    elif verified_exception and score_ok and not blocking:
        # Una excepción validada permanece separada incluso si la llamada es
        # breve o también existe evidencia para corregir la etiqueta.
        # Su causa (hostilidad/lascivia de un tercero) no debe desaparecer del
        # dictamen ni terminar en APROBADAS_DURACION_MENOR.
        category = 'APROBADO_CON_EXCEPCION'
    elif score_rejection:
        category = 'NO_APROBADO_MENOR_80'
    elif blocking:
        category = 'REVISAR'
    elif not score_ok:
        category = 'NO_APROBADO_MENOR_80'
    elif ((second_listening_offensive_only or current_unverified_complaint)
          and any(f['severity']=='ALERTA_INFORMATIVA' for f in findings)):
        category = 'APROBADO_CON_ALERTA'
    elif output_label['valid']:
        category = 'APROBADO_ETIQUETA_CORREGIDA'
    elif pending_output_label['eligible']:
        category = 'APROBADO_SIN_ETIQUETAR'
    elif base.get('estatus_autorizado') is False:
        category = 'APROBADO_SIN_ETIQUETAR'
    elif base.get('estatus_autorizado') is True and base.get('tiene_nombre_final') is False:
        add(13,'OUTPUT_NAME_MISSING','Falta nombre final para reetiquetar','base_classification')
        blocking = [f for f in findings if f['severity'] in {'REVIEW','CRITICAL'}]
        category = 'REVISAR'
    else:
        category = 'APROBADO'
    approved_with_alert=bool(category=='APROBADO_CON_ALERTA')
    if short_call and category in {'APROBADO','APROBADO_ETIQUETA_CORREGIDA','APROBADO_CON_ALERTA'}:
        category='APROBADO_DURACION_MENOR'
    reasons = list(dict.fromkeys(r for f in blocking for r in f['reasons']))
    if approved_with_alert:
        reasons.extend('[ALERTA SIN EMISOR CONFIRMADO] '+reason
            for finding in findings if finding['severity']=='ALERTA_INFORMATIVA'
            for reason in finding['reasons'] if '[ALERTA SIN EMISOR CONFIRMADO] '+reason not in reasons)
    if category == 'SIN_RELACION_EXCEL':
        reasons.insert(0,'Falta el registro de esta llamada en el Excel de cuentas; corregir la relación de origen. No requiere retranscribir para relacionarla.')
    if category in {'NO_APROBADO','NO_APROBADO_MENOR_80','FALLA_MINIMA'}:
        reasons.extend(r for f in findings if f['severity']=='OBSERVATION'for r in f['reasons']if r not in reasons)
    if pending_alerts:
        reasons.extend('[Pendiente '+f['code']+'] '+r for f in pending_alerts for r in f['reasons'])
        reasons.append('El rechazo conserva '+str(len(pending_alerts))+' alerta(s) pendiente(s) de revisión; consultar ALERTAS_PENDIENTES.')
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
                 'ALERTA_PENDIENTE' if any(f['severity']=='PENDING_ALERT' for f in relevant) else
                 'REQUIERE_REVISION' if any(f['severity']=='REVIEW' for f in relevant) else
                 'INCUMPLIMIENTO_CONFIRMADO' if any(f['severity']=='CONFIRMED_NONCRITICAL' for f in relevant) else
                 'OBSERVACION_CONSERVADA' if any(f['severity']=='OBSERVATION' for f in relevant) else
                 'EXCEPCION_VALIDADA' if any(f['severity']=='VALIDATED_EXCEPTION' for f in relevant) else
                 'ETIQUETA_CORREGIDA' if any(f['severity']=='CORRECTED_STATUS' for f in relevant) else
                 'ETIQUETA_PENDIENTE' if any(f['severity']=='OUTPUT_LABEL_PENDING' for f in relevant) else
                 'ALERTA_INFORMATIVA' if any(f['severity']=='ALERTA_INFORMATIVA' for f in relevant) else
                 'DESCUENTO_APLICADO' if relevant else
                 'NO_APLICA' if applicability.get(number) is False else
                 'SIN_HALLAZGOS' if m else 'NO_EVALUADO')
        evaluations.append({'id':number,'rule':label,'state':state,'finding_codes':[f['code'] for f in relevant]})
    return {'clasificacion':category, 'aprobado':category in {'APROBADO','APROBADO_ETIQUETA_CORREGIDA','APROBADO_DURACION_MENOR','APROBADO_CON_ALERTA'},
            'calidad_aprobada':category.startswith('APROBADO'), 'score':score,'puntaje_minimo':minimum_score,
            'aprobado_con_alerta':approved_with_alert,
            'cumple_puntaje':score_ok,'rechazo_automatico_por_puntaje':category=='NO_APROBADO_MENOR_80',
            'rechazo_automatico_por_reglas':category=='NO_APROBADO',
            'falla_minima':category=='FALLA_MINIMA',
            'observaciones_conservadas':reasons,
            'motivo':('Excepción por hostilidad validada en audio; gestor profesional' if category=='APROBADO_CON_EXCEPCION' else
                      ' | '.join(reasons) if reasons else 'Cumple calidad y seguridad; etiqueta corregida en copia separada' if category=='APROBADO_ETIQUETA_CORREGIDA' else 'Cumple reglas de aprobación' if score_ok else 'Puntaje inferior al mínimo'),
            'decision_findings':findings,'rule_evaluation':evaluations,
            'output_label_correction':output_label,'pending_alerts':pending_alerts,
            'output_label_pending':pending_output_label,
            'requires_alert_review':bool(pending_alerts),'pending_alert_count':len(pending_alerts),
            'short_duration_approval':category=='APROBADO_DURACION_MENOR','management_completeness':completeness,
            'decision_policy':'INTEGRATED_USER_POLICY_20261123'}


def _no_voice_result(minimum_score):
    return {
        'clasificacion':'SIN_VOZ','aprobado':False,'calidad_aprobada':False,
        'score':0,'score_aplicable':False,'puntaje_minimo':minimum_score,
        'cumple_puntaje':False,'rechazo_automatico_por_puntaje':False,
        'rechazo_automatico_por_reglas':False,
        'observaciones_conservadas':['SIN VOZ — audio sin habla reconocida; corroborar señal/segmentos antes de atribuir la causa.'],
        'motivo':'SIN VOZ — no corresponde calificar gestión telefónica sin interlocución.',
        'decision_findings':[{'rule_group':13,'code':'SIN_VOZ_ASR_SIN_CORROBORACION',
           'severity':'ALERTA_INFORMATIVA','source_field':'no_voice_validation',
           'reasons':['La ausencia de texto ASR requiere corroborar audio para descartar error del motor.']}],
        'rule_evaluation':[{'id':13,'rule':'Clasificación final','state':'SIN_VOZ',
           'finding_codes':['SIN_VOZ_ASR_SIN_CORROBORACION']}],
        'output_label_correction':{'valid':False,'eligible':False},
        'pending_alerts':[],'requires_alert_review':True,'pending_alert_count':0,
        'quality_not_applicable':True,'short_duration_approval':False,
        'management_completeness':{},'decision_policy':'SIN_VOZ_USER_POLICY_20261121'
    }
