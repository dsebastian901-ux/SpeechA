"""Relectura local acotada para hechos de interlocución, sin cambiar el ASR original.

Dos encuadres deben coincidir. No recupera importes, referencias, excepciones,
voces ni confirmaciones humanas. Un desacuerdo conserva el dictamen inicial.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from app.services.audio_block_evidence import binding
from app.services.conversation_evidence import normalize,holder_confirmation,recipient_statement
from app.services.contextual_identity_evidence import nonholder_counter_evidence,proxy_account_evidence,BAD_IDENTITY,valid_nominal_request
from app.services.payment_reference_validation import callback_numbers

SCHEMA=2


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),default=str).encode()).hexdigest()


def record_digest(record):
    return digest({k:v for k,v in record.items()if k not in{'record_sha256','seconds'}})


def reading_quality(reading):
    text=str(reading.get('text')or'');words=re.findall(r'\w+',normalize(text))
    if len(words)<4:return False
    if len(words)>=15:
        if max(Counter(words).values())/len(words)>.45:return False
        grams=[tuple(words[n:n+4])for n in range(len(words)-3)]
        if grams and max(Counter(grams).values())>=5:return False
    segments=reading.get('segments')or[]
    probabilities=[];silences=[]
    for segment in segments:
        ratio=segment.get('compression_ratio')
        if isinstance(ratio,(int,float)) and (not math.isfinite(ratio) or ratio>2.4):return False
        for field,target in [('avg_logprob',probabilities),('no_speech_prob',silences)]:
            value=segment.get(field)
            if isinstance(value,(int,float))and not math.isfinite(value):return False
            if isinstance(value,(float,int))and math.isfinite(value):target.append(value)
    if probabilities and sum(probabilities)/len(probabilities)<-1.15:return False
    if silences and sum(silences)/len(silences)>.65:return False
    return True


def nominal_words(text):
    """Solo palabras del nombre solicitado al abrir la llamada; nunca del Excel."""
    source=normalize(text)[:500]
    intro=(r'(?:me (?:puede|puedes|podria|podre) comunicar (?:por favor |de favor |el favor )?con|'
           r'me comunica con|me comunico con|tengo (?:el )?(?:gusto|uso) con|busco (?:a |al |el |la )?|'
           r'encuentr[aeo]|se encuentra|con (?:el senor|la senora|la senorita))')
    for match in re.finditer(r'\b'+intro+r'\s*(?:\.\s*){0,3}(?P<person>[^.!?]{3,100})',source):
        person=match['person']
        if (BAD_IDENTITY.search(person)or re.search(r'\d',person)
                or not valid_nominal_request(source,match.start(),person)):continue
        words=[w for w in re.findall(r'[a-z]+',person)if len(w)>=3 and w not in
               {'senor','senora','senorita','titular','favor','por','con','del','los','las','este','gracias','mrs','juridico'}]
        if words:return set(words)
    return set()


def nominal_self_reply(text):
    """Respuesta autorreferida solo después de una solicitud nominal válida.

    No atribuye la voz ni sustituye las comprobaciones de tercero.
    """
    folded=normalize(text)
    expression=re.compile(
        r'\b(?:me (?:puede|puedes|podria|podre) comunicar(?: por favor)? con|'
        r'tengo(?: el)? gusto con|hablo con)\s+'
        r'(?P<person>[^.!?]{3,100})[.?]\s*'
        r'(?:titular\s*:\s*)?(?:si[, ]+)?soy yo\b')
    from app.services.conversation_evidence import _role_at
    for match in expression.finditer(folded):
        if (_role_at(text, [], match.end()-len('soy yo')) not in {'GESTOR','TERCERO'}
                and valid_nominal_request(folded,match.start(),match['person'])
                and not BAD_IDENTITY.search(match['person'])):
            return True
    return False


def needs_recovery(metadata):
    """Releer dudas acústicas de TODO REVISAR, sin convertir la relectura en aprobación."""
    decision=metadata.get('shared_classification')or{}
    category=str(decision.get('clasificacion')or'')
    if (category not in {'REVISAR','NO_APROBADO_MENOR_80'} and not (
        category in {'FALLA_GRAVE','NO_APROBADO','FALLA_MINIMA'} and decision.get('pending_alerts'))):
        return set()
    wanted=set()
    if category=='REVISAR' and metadata.get('quality_contact_type')=='CONTACTO NO DETERMINADO':
        wanted.add('holder')
    workflow=metadata.get('message_workflow_validation')or{}
    if (metadata.get('quality_contact_type')!='TITULAR'and workflow.get('directed_body')
            and workflow.get('recipient_accepted')and not workflow.get('callback_available')
            and not workflow.get('final_refusal')):
        wanted.add('callback')
    if ((metadata.get('message_delivery_validation')or{}).get('review_required')
            and metadata.get('quality_contact_type')!='TITULAR'):
        wanted.add('callback')
    if (str(metadata.get('quality_contact_type')or'').startswith('TERCERO')
            and workflow.get('directed_body')and not workflow.get('callback_available')
            and not workflow.get('final_refusal')):
        wanted.add('callback')
    if category=='REVISAR' or decision.get('pending_alerts'):
        # Se solicitan lecturas adicionales para comprobar, NO para eximir,
        # los otros bloqueos del dictaminador.
        findings=(decision.get('pending_alerts')or decision.get('decision_findings')or [])
        codes={str(f.get('code')or'')for f in findings if isinstance(f,dict)}
        if codes & {'CONTEXT_AUDIO_THIRD_REQUIRED','CONTEXT_AUDIO_CONTRADICTION'}:
            wanted.update((metadata.get('context_audio_validation')or{}).get('recovery_reasons')or['general'])
        if 'CONTEXT_AUDIO_REQUIRED_INVALID'in codes:
            codes.update((metadata.get('context_audio_validation')or{}).get('required_findings',[]))
        if codes & {'CONVENIO_OUTCOME_CONFLICT','RECEIPT_UNCERTAIN','PAYMENT_OUTCOME_NOT_CONFIRMED',
                    'NEGOTIATION_INVALID_OR_UNCERTAIN','STATUS_INVALID','STATUS_NOT_CONFIRMED',
                    'RECOVERED_AMOUNT_UNVERIFIED','FINANCIAL_CONFIRMATION'}:
            wanted.add('financial')
        if codes & {'ASSET_COERCION_REVIEW','THIRD_PARTY_PAYMENT_GUIDANCE','UNCERTAIN_DISCLOSURE','WARNING_CONFIRMATION',
                    'HOME_WARNING_UNATTRIBUTED','OFFENSIVE_LANGUAGE',
                    'UNCERTAIN_CONFRONTATION','CONTEXT_AUDIO_RISK','ADDITIONAL_AUDIO_EVIDENCE',
                    'WAIT_WITHOUT_RESUMPTION','CARD_REFERENCE'}:
            wanted.add('safety')
        if not wanted:
            wanted.add('general')
    return wanted


def _cue_time(data,purpose):
    """Elegir un fragmento desde marcas ASR existentes, no desde Excel."""
    keywords={
        'financial':r'\b(?:pago|pagar|abono|deposito|comprobante|whatsapp|importe|pesos|manana|convenio)\b',
        'safety':r'\b(?:domicilio|visita|abogado|amenaza|referencias|tarjeta|groser|espera|colgo|confront)\w*',
        'general':r'\b(?:pago|recado|telefono|tarjeta|fecha|monto|convenio|negativa)\b',
        'callback':r'\b(?:numero|telefono|anotar|whatsapp)\b',
    }
    cues=[]
    for segment in data.get('segmentos')or[]:
        value=normalize(segment.get('texto',segment.get('text','')))
        if re.search(keywords.get(purpose,keywords['general']),value):
            at=segment.get('inicio',segment.get('start'))
            if isinstance(at,(int,float))and math.isfinite(at)and at>=0:
                cues.append(float(at))
    # Recuperación focal de riesgo/prueba: primer indicio, de contacto el último.
    return (cues[-1]if purpose=='callback'else cues[0])if cues else None


def windows(data,wanted):
    duration=float(data.get('duracion_segundos')or 0)
    if not math.isfinite(duration)or duration<=0:return []
    result=[]
    if 'holder'in wanted:
        result.append(('holder',[(0.,min(duration,28.)),(0.,min(duration,33.))]))
    if 'callback'in wanted:
        at=_cue_time(data,'callback')
        start=max(0.,(at if at is not None else duration-24.)-6.)
        result.append(('callback',[(start,min(duration,start+35.)),
                                   (max(0.,start-3.),min(duration,start+40.))]))
    # Cada objetivo conserva dos encuadres distintos, <=45 segundos.
    # Los hallazgos no relacionados con identidad/teléfono siguen pendientes
    # hasta que el dictaminador los valide con evidencia atribuible.
    for purpose in ('financial','safety','general'):
        if purpose not in wanted:continue
        at=_cue_time(data,purpose)
        start=max(0.,(at if at is not None else duration/2)-6.)
        first=(start,min(duration,start+30.))
        second=(max(0.,start-3.),min(duration,start+36.))
        if first!=second and all(end>begin for begin,end in (first,second)):
            result.append((purpose,[first,second]))
    return result


def needs_third_read(purpose,attempts,relation=None):
    """Otra decodificación aporta contraste de hechos, nunca una voz independiente."""
    from app.services.context_fact_consensus import consensus
    return len(attempts)==2 and consensus(purpose,attempts,relation)['third_recommended']


def reading_summary(record):
    """Fragmentos breves para interfaz/Excel; conserva evidencia completa en el checkpoint."""
    rows=[]
    for group in (record or {}).get('groups')or[]:
        purpose=group.get('purpose','')
        for idx,attempt in enumerate(group.get('attempts')or[],1):
            rows.append({'purpose':purpose,'attempt':idx,
                'start':attempt.get('start'),'end':attempt.get('end'),
                'text':str(attempt.get('text')or'')[:350],
                'error':attempt.get('error','')})
    return rows


def execution_status(record):
    """Contabilidad de llamadas al decodificador, separada del consenso."""
    attempts=[a for group in (record or{}).get('groups',[])for a in group.get('attempts',[])]
    return {'attempted':len(attempts),'completed':sum(not bool(a.get('error'))for a in attempts),
            'failed':sum(bool(a.get('error'))for a in attempts),'model':(record or{}).get('model')}


def _focused_windows(data,metadata):
    """Ejecutar las ventanas del reporte, agrupadas sin duplicar el mismo PCM."""
    from app.services.medium_review_plan import plan_for_item
    decision=metadata.get('shared_classification')or{}
    plan=plan_for_item({'result':data,'analytics_metadata':metadata,'classification':decision})
    duration=float(data.get('duracion_segundos')or 0);groups={}
    if not math.isfinite(duration)or duration<=0:return []
    for row in plan:
        a,b=row['start'],row['end']
        if a is None or b is None:continue
        code=row['finding_code']
        purpose=('holder'if code=='UNIDENTIFIED_CONTACT'else'callback'if code.startswith(('CALLBACK','MESSAGE_'))else
                 'safety'if code in{'ASSET_COERCION_REVIEW','THIRD_PARTY_PAYMENT_GUIDANCE','UNCERTAIN_DISCLOSURE','HOME_WARNING_UNATTRIBUTED','OFFENSIVE_LANGUAGE',
                    'UNCERTAIN_CONFRONTATION','WAIT_WITHOUT_RESUMPTION','CARD_REFERENCE','MISTREATMENT_REPORT'}else'financial')
        while a<b:
            end=min(b,a+38.)
            first=(a,end);second=(max(0.,a-2.),min(duration,end+2.))
            if first==second:first=(a,max(a,end-1.))
            if all(y>x for x,y in (first,second)):
                groups[(purpose,first,second)]=(purpose,[first,second])
            if end==b:break
            a=end-2.
    return list(groups.values())


def collect(audio_path,data,relation,metadata,read_window,model,*,include_tail=False,focused=False):
    """read_window lee PCM real mediante el modelo ya cargado, sin prompt de cuenta."""
    requested=needs_recovery(metadata)
    plan=_focused_windows(data,metadata)if focused else windows(data,requested)
    located=bool(plan)
    if focused and not plan:
        # Leer un encuadre diagnóstico acotado aunque falten marcas útiles.
        # No presentarlo como localización confirmada del bloqueo ni usarlo
        # para cerrar automáticamente una duda situada en otro lugar.
        plan=windows(data,requested)
    if not plan:return None
    path=Path(audio_path)
    from app.config.release import ENGINE_REVISION
    from app.services.context_fact_consensus import consensus, VALIDATOR_REVISION
    decision=metadata.get('shared_classification')or{}
    record={'schema':SCHEMA,'kind':'LOCAL_CONTEXT_ASR_CONSENSUS',
        'source_binding':binding(data,relation),'audio_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'audio_file':path.name,'model':str(model),'human_verified':False,
        'speaker_roles_confirmed':False,'groups':[], 'engine_revision':ENGINE_REVISION,
        'validator_revision':VALIDATOR_REVISION,
        'recovery_location_confirmed':located if focused else True,
        'required_findings':[f['code']for f in decision.get('decision_findings',[])
                             if f.get('severity')in{'REVIEW','PENDING_ALERT'} and f.get('code')],
        'classification_before':decision.get('clasificacion'),
        'recovery_reasons':sorted(requested), 'independent_sources':1}
    # El cierre también pasa por los mismos controles de consenso y calidad.
    duration=float(data.get('duracion_segundos')or 0)
    if include_tail and duration>45 and not any(purpose=='safety' and pair[-1][1]>=duration for purpose,pair in plan):
        plan.append(('safety_tail',[(duration-25.,duration),(duration-30.,duration)]))
    for purpose,pair in plan:
        primary=[]
        for segment in data.get('segmentos')or[]:
            a=segment.get('inicio',segment.get('start'));b=segment.get('fin',segment.get('end'))
            if isinstance(a,(float,int))and isinstance(b,(float,int))and a<pair[0][1]and b>pair[0][0]:
                primary.append(str(segment.get('texto',segment.get('text',''))))
        primary_text=' '.join(primary)
        attempts=[]
        def execute(start,end,beam,index,reason):
            import time
            began=time.perf_counter()
            attempt={'start':start,'end':end,'beam_size':beam,'listening_index':index,
                     'model':str(model),'trigger_reason':reason}
            try:
                reading=read_window(start,end,beam)
                attempt.update(text=str(reading.get('text')or''),segments=reading.get('segments')or[])
            except Exception as error:
                attempt.update(text='',segments=[],error=type(error).__name__)
            attempt['seconds']=time.perf_counter()-began
            attempt['text_sha256']=digest(attempt['text'])
            return attempt
        for index,((start,end),beam) in enumerate(zip(pair,(5,10)),1):
            attempts.append(execute(start,end,beam,index,'CONTRASTE_FOCAL_INICIAL'))
        primary_disagrees=bool(focused and primary_text and
            normalize(primary_text)!=normalize(attempts[0].get('text')))
        first_two=consensus(purpose,attempts,relation)
        third_required=needs_third_read(purpose,attempts,relation)or primary_disagrees
        third_reason=('DISCREPANCIA_CON_ASR_ORIGINAL' if primary_disagrees else first_two['reason_code'])
        if third_required:
            duration=float(data.get('duracion_segundos')or 0)
            start=max(0.,pair[0][0]-2.)
            end=min(duration,start+45.,max(pair[0][1],pair[1][1])+2.)
            if (start,end)in pair:
                start=max(0.,start-1.)
            if end>start and end-start<=45.:
                attempts.append(execute(start,end,8,3,third_reason))
        # Comparar con el ASR original sin reemplazarlo ni atribuir una voz.
        record['groups'].append({'purpose':purpose,'attempts':attempts,
            'first_two_consensus':first_two,'third_read_required':bool(third_required),
            'third_read_reason':third_reason if third_required else '',
            'primary_text':primary_text,'primary_overlap_is_segment_level':True,
            'third_read_required_by_primary_disagreement':primary_disagrees,
            'primary_text_matches_first_read':normalize(primary_text)==normalize(attempts[0].get('text')),
            'consensus':consensus(purpose,attempts,relation)})
    record['record_sha256']=record_digest(record)
    return record


def validate(record,data,relation,audio_path):
    result={'present':record is not None,'valid':False,'holder':False,'callback':None,
            'evidence':[],'risks':[],'review_required':False,'message_receipt':None,
            'human_verified':False,'method':'LOCAL_CONTEXT_ASR_CONSENSUS'}
    if record is None:return result
    if isinstance(record,dict):
        result.update(required_findings=record.get('required_findings',[]),
            recovery_reasons=record.get('recovery_reasons')or
                [g.get('purpose')for g in record.get('groups',[])if isinstance(g,dict)])
    try:
        path=Path(audio_path)
        checks=[('VERSION_DE_REGISTRO_NO_COMPATIBLE',record.get('schema')==SCHEMA),
                ('TIPO_DE_REGISTRO_NO_COMPATIBLE',record.get('kind')=='LOCAL_CONTEXT_ASR_CONSENSUS'),
                ('REGISTRO_MODIFICADO',record.get('record_sha256')==record_digest(record)),
                ('TEXTO_O_CUENTA_DISTINTOS',record.get('source_binding')==binding(data,relation)),
                ('AUDIO_LOCAL_NO_DISPONIBLE',path.is_file())]
        result['invalid_reason_codes']=[code for code,passed in checks if not passed]
        if (record.get('schema')!=SCHEMA or record.get('kind')!='LOCAL_CONTEXT_ASR_CONSENSUS'
                or record.get('human_verified')is not False or record.get('speaker_roles_confirmed')is not False
                or record.get('record_sha256')!=record_digest(record)
                or record.get('source_binding')!=binding(data,relation)
                or path.name!=record.get('audio_file')or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest()!=record.get('audio_sha256')):
            result['reason']='La relectura no corresponde al audio, texto y cuenta actuales.'
            if not result['invalid_reason_codes']:result['invalid_reason_codes']=['AUDIO_O_DECLARACION_DE_ATRIBUCION_INCOMPATIBLES']
            return result
        duration=float(data.get('duracion_segundos')or 0)
        if not math.isfinite(duration)or duration<=0:raise ValueError('Duración inválida')
        result['valid']=True
        from app.services.context_fact_consensus import consensus, VALIDATOR_REVISION
        result.update(validator_revision=VALIDATOR_REVISION,
            recovery_location_confirmed=record.get('recovery_location_confirmed',True),
            audio_sha256=record.get('audio_sha256'), audio_file=record.get('audio_file'),
            model=record.get('model'), engine_revision=record.get('engine_revision'),
            required_findings=record.get('required_findings',[]),
            recovery_reasons=record.get('recovery_reasons',[]), independent_sources=1,
            classification_before=record.get('classification_before'), fact_validations=[])
        result['readings']=reading_summary(record)
        for group_index,group in enumerate(record.get('groups')or[]):
            all_attempts=group.get('attempts')or[]
            if len(all_attempts)not in (2,3)or [a.get('beam_size')for a in all_attempts[:2]]!=[5,10]:raise ValueError('Lecturas incompletas')
            if len(all_attempts)==3 and all_attempts[2].get('beam_size')!=8:raise ValueError('Tercera lectura inválida')
            if any(not(0<=float(a['start'])<float(a['end'])<=duration+.01)
                   or float(a['end'])-float(a['start'])>45 for a in all_attempts):raise ValueError('Ventana inválida')
            if (all_attempts[0]['start'],all_attempts[0]['end'])==(all_attempts[1]['start'],all_attempts[1]['end']):raise ValueError('Ventanas idénticas')
            purpose=group.get('purpose','')
            semantic=consensus(purpose,all_attempts,relation)
            result['fact_validations'].append(semantic)
            required=needs_third_read(purpose,all_attempts[:2],relation) or bool(
                group.get('third_read_required_by_primary_disagreement'))
            if required and (len(all_attempts)!=3 or all_attempts[2].get('error')
                             or not reading_quality(all_attempts[2])):
                result.setdefault('third_listening_pending',[]).append(purpose)
                result['review_required']=True
            contradictions=[r['rule']for r in semantic['rules']if r['state']=='CONTRADICTORIO']
            if contradictions:
                result.setdefault('contradictory_fact_rules',[]).extend(contradictions)
                result['review_required']=True
            good=[a for a in all_attempts if not a.get('error')and reading_quality(a)]
            # Una relectura no puede aportar solamente hechos favorables e
            # ignorar una expresión ofensiva que la primera lectura omitió.
            for attempt in all_attempts:
                offensive=re.search(r'\b(?:que poca madre|chingad[ao]s?|chingues|chingue|'
                    r'pendej[oa]s?|cabron(?:a|es)?|mierda|pinche|put[ao]s?)\b',normalize(attempt['text']))
                if offensive:
                    result['risks'].append({'type':'EXPRESION_OFENSIVA_SIN_VOZ_CONFIRMADA',
                        'text':attempt['text'],'start':attempt['start'],'end':attempt['end'],
                        'human_verified':False})
                from app.services.context_rules import prohibited_threat
                mora=normalize((relation or{}).get('asignacion')or(relation or{}).get('mora')).upper().replace(' ','')
                threats=prohibited_threat(attempt.get('text'),attempt.get('segments')or[],mora=mora or '1PV')
                if threats:
                    result['risks'].append({'type':'ADVERTENCIA_DOMICILIARIA_PENDIENTE',
                        'text':attempt['text'],'start':attempt['start'],'end':attempt['end'],
                        'human_verified':False})
                from app.services.conversation_evidence import assess_privacy
                from app.services.contact_dialogue_resolution import declared_intermediary
                from app.services.contact_evidence_graph import nonholder_context
                original_third=bool(nonholder_context(data.get('texto'),data.get('segmentos')or[])or
                    declared_intermediary(data.get('texto'),data.get('segmentos')or[])['confirmed'])
                original_holder=bool(result['holder']or holder_confirmation(
                    data.get('texto'),data.get('segmentos')or[])['confirmed'])
                privacy=assess_privacy(attempt.get('text'),attempt.get('segments')or[],
                    third_party_confirmed=original_third,titular=original_holder)
                for candidate in privacy['evidence']:
                    if candidate.get('confirmed')or candidate.get('review_required'):
                        result['risks'].append({'type':'INFORMACION_PROTEGIDA_SIN_VOZ_CONFIRMADA',
                            'text':candidate['text'],'phrase':candidate.get('phrase',''),
                            'start':attempt['start'],'end':attempt['end'],'human_verified':False})
            if any(r['rule']=='CONFRONTATION'and r['state']in{'CONFIRMADO','SIN_ATRIBUCION','CONTRADICTORIO'}
                   and any(e['speaker_role']in{'GESTOR','NO DETERMINADO'}for e in
                       r['matching_evidence']+r['contradictory_evidence'])
                   for r in semantic['rules']):
                result['risks'].append({'type':'CONFRONTACION_PENDIENTE','human_verified':False})
            if purpose in{'financial','general'}and original_holder and any(
                f['rule']=='PAYMENT_PLAN'and f['state']=='CONFIRMADO'for f in semantic['rules']):
                from app.services.supplemental_rule_checks import financial_context_risks
                checked={}
                for attempt in good:
                    key=normalize(attempt['text'])
                    if key not in checked:checked[key]=financial_context_risks(attempt['text'],relation)
                    if checked[key]:
                        result['risks'].append({'type':'SUPPLEMENTAL_FINANCIAL_RISK',
                            'codes':checked[key],'text':attempt['text'],'start':attempt['start'],
                            'end':attempt['end'],'human_verified':False})
            # No resolver con una única lectura; dos evidencias concordantes
            # como mínimo y ninguna contradicción explícita en una tercera.
            if len(good)<2:continue
            attempts=good[:2]
            if len(all_attempts)==3 and len(good)==3:
                if group.get('purpose')=='holder':
                    from app.services.contact_dialogue_resolution import declared_intermediary
                    contradiction=any(nonholder_counter_evidence(a['text'],a.get('segments')or[])or
                        declared_intermediary(a['text'])['confirmed'] or proxy_account_evidence(a['text'])
                        for a in good)
                    if contradiction:continue
                    positive=[a for a in good if holder_confirmation(a['text'])['confirmed'] or nominal_self_reply(a['text'])]
                    if len(positive)>=2:attempts=positive[:2]
                elif group.get('purpose')=='callback':
                    sets=[{p['digits']for p in callback_numbers(a['text'])}for a in good]
                    singles=[n for n in sets if len(n)==1]
                    if singles and len(set.union(*singles))>1:continue
                    if len(singles)>=2 and singles[0]==singles[1]:
                        attempts=[good[sets.index(singles[0])],good[sets.index(singles[1],sets.index(singles[0])+1)]]
            if group.get('purpose')in {'financial','safety','general','safety_tail'}:
                # La segunda escucha de estas materias aporta fragmentos para
                # revisión, no acredita automáticamente identidad ni pagos.
                result['evidence'].append({'purpose':group['purpose'],
                    'texts':[a['text']for a in good],
                    'method':'LECTURA_FOCAL_DIAGNOSTICA',
                    'source':'LOCAL_AUDIO_CONTEXT','human_verified':False})
                # La relectura diagnóstica no genera otro bloqueo: se mantienen
                # los bloqueos existentes, salvo riesgo NUEVO confirmado por
                # la evidencia acústica que debe atribuirse.
                continue
            if group.get('purpose')=='holder':
                if any(a['start']!=0 or a['end']>(36 if a.get('beam_size')==8 else 34)
                       for a in attempts):continue
                source=normalize(data.get('texto'))
                from app.services.contact_dialogue_resolution import declared_intermediary
                from app.services.context_rules import unknown_debtor_statement
                from app.services.conversation_evidence import assess_recado
                raw_segments=data.get('segmentos')or[]
                from app.services.contact_evidence_graph import nonholder_context
                if (nonholder_context(data.get('texto'),raw_segments)or nonholder_counter_evidence(data.get('texto'),raw_segments)or proxy_account_evidence(data.get('texto'),raw_segments)
                    or declared_intermediary(data.get('texto'),raw_segments)['confirmed']
                    or unknown_debtor_statement(data.get('texto'),raw_segments)
                    or assess_recado(data.get('texto'),raw_segments)['family']):continue
                source_names=nominal_words(data.get('texto'))
                names=[nominal_words(a['text'])for a in attempts]
                if not source_names or any(source_names!=n for n in names):continue
                proofs=[]
                for attempt in attempts:
                    value=attempt['text']
                    contradicted=(nonholder_counter_evidence(value,attempt.get('segments')or[])or proxy_account_evidence(value)
                        or declared_intermediary(value)['confirmed']or unknown_debtor_statement(value)
                        or assess_recado(value)['family'])
                    direct=recipient_statement(value,[],r'\b(?:soy yo|soy (?:el|la) titular|habla (?:el|la) titular)\b')
                    proof=holder_confirmation(value)
                    named_valid=nominal_self_reply(value) and nominal_words(value)==source_names
                    proofs.append({'confirmed':not contradicted and
                        (proof['confirmed']or direct or named_valid)})
                if all(p['confirmed']for p in proofs):
                    result['holder']=True
                    result['evidence'].append({'purpose':'holder','texts':[a['text']for a in attempts],
                        'method':'NOMINAL_IDENTITY_CORROBORATED_IN_TWO_LOCAL_READINGS',
                        'source':'LOCAL_AUDIO_CONTEXT','human_verified':False})
            elif group.get('purpose')=='callback':
                numbers=[{p['digits']for p in callback_numbers(a['text'])}for a in attempts]
                if len(numbers[0])==len(numbers[1])==1 and numbers[0]==numbers[1]:
                    primary_numbers={p['digits']for p in callback_numbers(data.get('texto')or'')}
                    if primary_numbers and not(numbers[0]&primary_numbers):continue
                    result['callback']=next(iter(numbers[0]))
                    from app.services.conversation_evidence import assess_recado,sensitive_financial_matches
                    from app.services.definitive_rejection import explicit_message_refusal
                    original_receipt=assess_recado(data.get('texto')or'',data.get('segmentos')or[])
                    refused=explicit_message_refusal(data.get('texto')or'',data.get('segmentos')or[],original_receipt['acceptance'])
                    receipts=[assess_recado(a['text'])for a in attempts]
                    if not refused['confirmed']and all(r['acceptance']and not r['refusal']for r in receipts):
                        result['message_receipt']={'text':' / '.join(a['text']for a in attempts),
                            'source':'LOCAL_AUDIO_CONTEXT','method':'RECEPCION_Y_CONTACTO_CORROBORADOS_EN_DOS_LECTURAS',
                            'speaker_role':'NO DETERMINADO','human_verified':False,
                            'readings':[{'text':a['text'],'start':a['start'],'end':a['end']}for a in attempts]}
                    if not result['holder']:
                        for a in attempts:
                            for candidate in sensitive_financial_matches(a['text']):
                                result['risks'].append({'type':'INFORMACION_PROTEGIDA_SIN_VOZ_CONFIRMADA',
                                    'text':a['text'],'phrase':candidate.group(),'start':a['start'],'end':a['end'],
                                    'human_verified':False})
                    result['evidence'].append({'purpose':'callback','texts':[a['text']for a in attempts],
                        'method':'CALLBACK_MATCH_IN_TWO_LOCAL_READINGS','source':'LOCAL_AUDIO_CONTEXT',
                        'human_verified':False})
        result['outcomes']=[]
        for group_index,group in enumerate(record.get('groups')or[]):
            purpose=group.get('purpose','')
            if purpose=='holder' and result['holder']:
                status='IDENTIDAD_CORROBORADA'
            elif purpose=='callback' and result['callback']:
                status='CONTACTO_CORROBORADO'
            else:
                status='SIN_CONSENSO_O_ATRIBUCION'
            semantic=result['fact_validations'][group_index]
            result['outcomes'].append({'purpose':purpose,'result':status,
                'attempts':len(group.get('attempts')or[]),
                'consensus':semantic,
                'reason_code':semantic.get('reason_code','REGISTRO_NO_VALIDADO'),
                'reason':('Coincidencia validada bajo los controles de identidad y privacidad.'
                          if status!='SIN_CONSENSO_O_ATRIBUCION' else
                          semantic.get('reason_code','Información insuficiente para validar la regla.'))})
        if result['risks']:
            result.update(review_required=True,
                reason='Riesgos en relectura local pendientes de validar: '+', '.join(
                    sorted({r['type']for r in result['risks']}))+'. Verificar emisor y regla aplicable.')
        elif result['review_required']:
            result['reason']='Segunda escucha focal disponible; la evidencia requiere atribución o validación del dictaminador antes de modificar el resultado.'
        elif not result['holder'] and not result['callback']:
            result['reason']='Relectura focal registrada; sin coincidencia suficiente para resolver automáticamente la duda. Se conservan los bloqueos originales.'
    except (ValueError,TypeError,KeyError,AttributeError,OSError):
        result.update(valid=False,holder=False,callback=None,message_receipt=None,evidence=[],
                      fact_validations=[],reason='Registro de relectura incompleto o no verificable.')
    return result
