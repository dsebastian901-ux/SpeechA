"""Incumplimientos comprobables; las alertas independientes se conservan."""
import re
from app.services.conversation_evidence import normalize,sentence_evidence,_role_at

ORDINARY_REVIEW_CODES={'STATUS_INVALID','STATUS_NOT_CONFIRMED','UNIDENTIFIED_CONTACT',
    'FAMILY_CONFIRMATION','RECADO_CONFIRMATION','CALLBACK_NOT_DELIVERED',
    'SHORT_DURATION','INVALID_DURATION','OUTPUT_NAME_MISSING','NO_COLLECTION_ATTEMPT'}


def explicit_message_refusal(text,segments=(),acceptance=()):
    source=normalize(text);events=[];cursor=0
    pattern=re.compile(r'\b(?:no (?:quiero|puedo|voy a) (?:recibir|tomar|pasar|dar|transmitir) (?:el |un |su |ningun |ninguno |ninguna )?(?:recado|mensaje)|'
                       r'no (?:le |se lo )?(?:voy a|puedo|quiero) (?:pasar|dar|transmitir) (?:el |un |su |ningun )?(?:recado|mensaje)|'
                       r'no soy (?:su )?mensajer[oa]|no me interesa recibir (?:el |su )?recado|'
                       r'no tengo (?:donde|con que) (?:anotar(?:lo)?|apuntar(?:lo)?)|no puedo (?:anotar|apuntar|anotarlo|apuntarlo|notarlo)|'
                       r'no traigo (?:aqui )?(?:en que|con que|como) (?:anotar(?:lo)?|apuntar(?:lo)?))\b')
    from app.services.declarative_evidence import declarative_units
    for unit in declarative_units(text,segments):
        value=normalize(unit['text']);at=source.find(value,cursor)
        if at>=0:cursor=at+len(value)
        if unit['speaker_role']in{'GESTOR','TITULAR'}or at<0:continue
        matches=list(pattern.finditer(value))
        context=source[max(0,at-350):at]
        message_objects=list(re.finditer(r'\b(?:recado|mensaje)\b',context))
        if message_objects and not re.search(r'\b(?:transferencia|pago|deposito|comprobante|correo|paquete)\b',context[message_objects[-1].end():]):
            matches.extend(re.finditer(r'\bno (?:(?:se lo|se la|lo|la|le) (?:puedo|voy a|quiero) (?:pasar|dar|transmitir)|puedo recibir)(?=\s*[,.;!]|$)',value))
        for match in matches:
            before=value[max(0,match.start()-90):match.start()]
            if '?'in value or re.search(r'\b(?:dice que|dijo que|diga que|repita que|no es cierto que|'
                                       r'no es verdad que|si|en caso de que|cuando)\b[^.!?]{0,30}$',before):continue
            if re.search(r'\b(?:anotar(?:lo)?|apuntar(?:lo)?)\b',match.group()):
                from app.services.message_dialogue_evidence import phone_present
                tail=source[at+match.end():]
                if phone_present(tail)or re.search(r'\b(?:ya (?:lo )?tengo|pantalla|memorizo|me lo se|mensaje de texto|whatsapp|por mensaje)\b',tail):continue
                if not re.search(r'\b(?:recado|mensaje|numero|telefono)\b',source[max(0,at-700):at+match.start()]):continue
            events.append(dict(unit,phrase=match.group(),position=at+match.start(),
                human_verified=False,method='RECHAZO_EXPLICITO_DEL_RECADO'))
    positive_question=re.compile(r'\b(?:le )?(?:puedo|podria|podre|pudiera) (?:dejar(?:le)?|dar(?:le)?) (?:un |el |algun )?(?:recado|mensaje)\b[^?!.]{0,100}[?]\s*(?P<answer>no(?:[, ]+gracias)?)(?=[.!?,]|$)')
    for match in positive_question.finditer(source):
        if _role_at(text,segments,match.start('answer'))in{'GESTOR','TITULAR'}:continue
        before=source[max(0,match.start()-70):match.start()]
        if re.search(r'\b(?:no|dice que|dijo que|diga que|repita que|si)\s*$',before):continue
        if re.match(r'\s*\?',source[match.end():]):continue
        events.append({'text':match.group(),'phrase':match['answer'],'position':match.start('answer'),
            'speaker_role':_role_at(text,segments,match.start('answer')),'human_verified':False,
            'method':'NEGATIVA_DIRECTA_A_OFERTA_POSITIVA_DE_RECADO'})
    # Rechazo contextual del contacto ofrecido, sin inventar una omisión de
    # un texto incompleto. No se usa el mero silencio ni el agradecimiento.
    terminal=re.compile(r'\b(?P<answer>(?:no[, ]+){1,3}asi dejelo|entonces no me lo deje|mejor no me deje (?:el |un )?(?:recado|mensaje))\b')
    for m in terminal.finditer(source):
        before=source[max(0,m.start()-500):m.start()]
        if not re.search(r'\b(?:recado|mensaje|numero telefonico|le dejo el numero)\b',before):continue
        if _role_at(text,segments,m.start())in{'GESTOR','TITULAR'}:continue
        if re.search(r'\b(?:dice que|dijo que|diga que|repita que|si|por ejemplo)\b[^.!?]{0,45}$',before[-100:]):continue
        if re.match(r'\s*\?',source[m.end():]):continue
        events.append({'text':source[max(0,m.start()-180):m.end()],'phrase':m['answer'],
            'position':m.start(),'method':'RECHAZO_FINAL_DEL_CONTACTO_O_MENSAJE_OFRECIDO','human_verified':False})
    none={'confirmed':False,'evidence':[],'reason':''}
    if not events:
        # Imposibilidad de anotar seguida de cierre para llamar después. Una
        # alternativa propuesta sin entrega no equivale a recado recibido.
        unable=re.search(r'\bno (?:puedo (?:anotar|apuntar|anotarlo|apuntarlo)|tengo[^.!?]{0,35}\b(?:anotar(?:lo)?|apuntar(?:lo)?))\b',source)
        deferred=re.search(r'\b(?:me comunico|nos comunicamos|le marco|me comunicare|me voy a comunicar|nos comunicaremos) (?:nuevamente |entonces )?(?:mas tarde|en otro momento|nuevamente)\b',source[-220:])
        if unable and deferred and not re.search(r'\b(?:problemas?|dificultades?|nada que|impedimentos?)\b',unable.group()):
            before=source[max(0,unable.start()-600):unable.start()]
            from app.services.message_dialogue_evidence import callback_available
            if (not any(source.rfind(normalize(e.get('text','')))>unable.end() for e in acceptance if e.get('text')) and not callback_available(text,segments) and re.search(r'\b(?:recado|numero|telefono)\b',before)
                    and _role_at(text,segments,unable.start())not in{'GESTOR','TITULAR'}
                    and not re.search(r'\b(?:dice que|dijo que|diga que|por ejemplo|si)\s*$',before[-90:])):
                return {'confirmed':True,'evidence':[{'text':source[unable.start():],'method':'NO_PUEDE_ANOTAR_Y_SE_CIERRA_PARA_LLAMAR_DESPUES','human_verified':False}],
                    'reason':'El interlocutor no puede anotar y la llamada se cierra para llamar después, sin recado recibido.'}
        # No conocer el paradero del titular no equivale a rechazar un recado.
        return none
    last=max(e['position']for e in events)
    for evidence in acceptance:
        value=normalize(evidence.get('text',''));at=source.rfind(value)
        if value and at>last:return none
    return {'confirmed':True,'evidence':events,
            'reason':'El interlocutor rechaza expresamente recibir o transmitir el recado y no se detecta aceptación posterior.'}


def definitive_rejection(metadata,findings,duration_seconds):
    blocking=[f for f in findings if f['severity']in{'REVIEW','CRITICAL'}]
    treatment=metadata.get('treatment_validation')or{}
    from app.services.message_contact_evidence import _outside_question
    confirmed_complaint=False
    for evidence in treatment.get('mistreatment_report_evidence')or[]:
        value=normalize(evidence.get('text',''));phrase=normalize(evidence.get('phrase',''));at=value.find(phrase)if phrase else-1
        if (at>=0 and 'speaker_role'in evidence and evidence['speaker_role']!='GESTOR'
                and _outside_question(value,at,at+len(phrase))
                and not re.search(r'\b(?:parece|quizas|tal vez|supongo|podria ser|no se si)\b',value[:at])):
            confirmed_complaint=True;break
    # Decisión expresa de la usuaria: el rechazo comprobado cierra calidad;
    # otra duda no lo convierte de nuevo en REVISAR ni desaparece del reporte.
    if any(f['severity']=='CRITICAL'for f in blocking):return None
    n=metadata.get('negotiation_validation')or{}
    # Importe aceptado y cotejado inválido: rechazo, no una extracción dudosa.
    # Las dudas independientes permanecen como alertas del rechazo.
    if (metadata.get('quality_contact_type')=='TITULAR'
            and n.get('is_negotiation') and n.get('valid')is False
            and n.get('amount_invalid') and n.get('hard_invalid')
            and not n.get('review_required') and not n.get('datos_saldo_inconsistentes') and not n.get('monto_normalizado_asr')
            and n.get('amount_confirmed') and n.get('payment_date_confirmed')
            and n.get('commitment_confirmed') and not n.get('date_year_rollover_review')
            and not n.get('payment_confirmation_case') and not n.get('multipago_detectado')
            and n.get('evidencia_monto') and (n.get('commitment_evidence')or{}).get('accepted')
            and not(n.get('installment_validation')or{}).get('review_required')):
        return {'rule_group':12,'code':'CONFIRMED_INVALID_PAYMENT_AMOUNT',
            'severity':'CONFIRMED_NONCRITICAL','source_field':'negotiation_validation',
            'resolves_codes':['NEGOTIATION_INVALID_OR_UNCERTAIN'],
            'reasons':[n.get('motivo_validacion_monto')or'El importe del compromiso confirmado incumple la política financiera.']}
    # El plazo operativo fuera de política se resuelve como FALLA_MINIMA
    # por la instrucción del 23/11, separado de los rechazos restantes.
    coverage=(metadata.get('negotiation_validation')or{}).get('followup_coverage_validation')or{}
    if coverage.get('confirmed_failure') and not (n.get('reported_payment_management')or{}).get('confirmed_receipt_only_shortfall'):
        return {'rule_group':12,'code':'CONFIRMED_INSUFFICIENT_FOLLOWUP','severity':'CONFIRMED_NONCRITICAL',
            'source_field':'negotiation_validation','reasons':[coverage['reason']]}
    # La acusación al gestor actual que NO se corroboró es alerta (141);
    # no aplicar automáticamente rechazo por queja de maltrato previa.
    if confirmed_complaint and not treatment.get('current_agent_mistreatment_unverified'):
        return {'rule_group':11,'code':'CONFIRMED_SERVICE_COMPLAINT','severity':'CONFIRMED_NONCRITICAL',
            'resolves_codes':['MISTREATMENT_REPORT'],
            'source_field':'treatment_validation','reasons':['Queja de atención previa expresada en la conversación; bloquea aprobación por criterio operativo.']}
    # La negativa del TERCERO a tomar un recado NO es una falta del gestor.
    # Se dictamina como SE NIEGAN A TOMAR RECADO; la calidad debe seguir
    # evaluando identificación, privacidad, trato y demás controles reales.
    return None
