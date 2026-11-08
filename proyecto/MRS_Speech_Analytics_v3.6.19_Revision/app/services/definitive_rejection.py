"""Incumplimientos ordinarios comprobables; no resuelve alertas de seguridad."""
import re
from app.services.conversation_evidence import normalize,sentence_evidence,_role_at

ORDINARY_REVIEW_CODES={'STATUS_INVALID','STATUS_NOT_CONFIRMED','UNIDENTIFIED_CONTACT',
    'FAMILY_CONFIRMATION','RECADO_CONFIRMATION','CALLBACK_NOT_DELIVERED',
    'SHORT_DURATION','INVALID_DURATION','OUTPUT_NAME_MISSING','NO_COLLECTION_ATTEMPT'}


def explicit_message_refusal(text,segments=(),acceptance=()):
    source=normalize(text);events=[];cursor=0
    pattern=re.compile(r'\b(?:no (?:quiero|puedo|voy a) (?:recibir|tomar|pasar|dar|transmitir) (?:el |un |su )?(?:recado|mensaje)|'
                       r'no (?:le |se lo )?(?:voy a|puedo|quiero) (?:pasar|dar|transmitir) (?:el |un |su )?(?:recado|mensaje)|'
                       r'no soy (?:su )?mensajer[oa]|no me interesa recibir (?:el |su )?recado|'
                       r'no tengo (?:donde|con que) (?:anotar|apuntar)|no puedo (?:anotar|apuntar|anotarlo|apuntarlo)|'
                       r'no traigo (?:aqui )?(?:en que|con que|como) (?:anotar|apuntar))\b')
    for unit in sentence_evidence(text,segments):
        value=normalize(unit['text']);at=source.find(value,cursor)
        if at>=0:cursor=at+len(value)
        if unit['speaker_role']in{'GESTOR','TITULAR'}or at<0:continue
        for match in pattern.finditer(value):
            before=value[max(0,match.start()-90):match.start()]
            if '?'in value or re.search(r'\b(?:dice que|dijo que|diga que|repita que|no es cierto que|'
                                       r'no es verdad que|si|en caso de que|cuando)\b[^.!?]{0,30}$',before):continue
            if re.search(r'\b(?:anotar|apuntar)\b',match.group()):
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
    none={'confirmed':False,'evidence':[],'reason':''}
    if not events:
        # Imposibilidad de anotar seguida de cierre para llamar después. Una
        # alternativa propuesta sin entrega no equivale a recado recibido.
        unable=re.search(r'\bno (?:puedo (?:anotar|apuntar|anotarlo|apuntarlo)|tengo[^.!?]{0,35}\b(?:anotar|apuntar))\b',source)
        deferred=re.search(r'\b(?:me comunico|nos comunicamos|le marco|me comunicare|me voy a comunicar|nos comunicaremos) (?:nuevamente |entonces )?(?:mas tarde|en otro momento|nuevamente)\b',source[-220:])
        if unable and deferred and not re.search(r'\b(?:problemas?|dificultades?|nada que|impedimentos?)\b',unable.group()):
            before=source[max(0,unable.start()-600):unable.start()]
            from app.services.message_dialogue_evidence import callback_available
            if (not any(source.rfind(normalize(e.get('text','')))>unable.end() for e in acceptance if e.get('text')) and not callback_available(text,segments) and re.search(r'\b(?:recado|numero|telefono)\b',before)
                    and _role_at(text,segments,unable.start())not in{'GESTOR','TITULAR'}
                    and not re.search(r'\b(?:dice que|dijo que|diga que|por ejemplo|si)\s*$',before[-90:])):
                return {'confirmed':True,'evidence':[{'text':source[unable.start():],'method':'NO_PUEDE_ANOTAR_Y_SE_CIERRA_PARA_LLAMAR_DESPUES','human_verified':False}],
                    'reason':'El interlocutor no puede anotar y la llamada se cierra para llamar después, sin recado recibido.'}
        final_contact = re.search(r'\b(?:ya no (?:tenemos|tengo) comunicacion|no (?:tengo|tenemos) (?:como|forma de) (?:contactarlo|contactarla|avisarle)|no se nada de (?:el|ella))\b',source)
        ended = re.search(r'\b(?:hasta luego|gracias|me (?:voy a seguir comunicando|comunico (?:mas tarde|en otro momento)))\b',source[-180:])
        if final_contact and ended and not acceptance and _role_at(text,segments,final_contact.start())not in{'GESTOR','TITULAR'}:
            return {'confirmed':True,'evidence':[{'text':final_contact.group(),'method':'IMPOSIBILIDAD_EXPRESA_DE_TRANSMITIR_RECADO_CON_CIERRE','human_verified':False}],
                    'reason':'El interlocutor declara que no tiene forma de contactar al titular y la llamada cierra sin aceptación del recado.'}
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
    allowed=ORDINARY_REVIEW_CODES|({'MISTREATMENT_REPORT'}if confirmed_complaint else set())
    if any(f['severity']=='CRITICAL'or f['code']not in allowed for f in blocking):return None
    if confirmed_complaint:
        return {'rule_group':11,'code':'CONFIRMED_SERVICE_COMPLAINT','severity':'CONFIRMED_NONCRITICAL',
            'source_field':'treatment_validation','reasons':['Queja de atención previa expresada en la conversación; bloquea aprobación por criterio operativo.']}
    refused=metadata.get('explicit_message_refusal')or{}
    if refused.get('confirmed'):
        return {'rule_group':4,'code':'EXPLICIT_MESSAGE_REFUSAL','severity':'CONFIRMED_NONCRITICAL',
            'source_field':'explicit_message_refusal','reasons':[refused['reason']]}
    if duration_seconds is not None and 0<float(duration_seconds)<60:
        return {'rule_group':13,'code':'CONFIRMED_SHORT_DURATION','severity':'CONFIRMED_NONCRITICAL',
            'source_field':'duration_seconds','reasons':['Duración comprobada inferior al mínimo de 60 segundos.']}
    return None
