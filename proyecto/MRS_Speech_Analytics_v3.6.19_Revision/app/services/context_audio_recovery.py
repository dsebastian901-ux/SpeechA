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
from app.services.contextual_identity_evidence import COUNTER,proxy_account_evidence,BAD_IDENTITY,valid_nominal_request
from app.services.payment_reference_validation import callback_numbers

SCHEMA=1


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
        for field,target in [('avg_logprob',probabilities),('no_speech_prob',silences)]:
            value=segment.get(field)
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


def needs_recovery(metadata):
    decision=metadata.get('shared_classification')or{}
    if decision.get('clasificacion')!='REVISAR':return set()
    wanted=set()
    if metadata.get('quality_contact_type')=='CONTACTO NO DETERMINADO':wanted.add('holder')
    workflow=metadata.get('message_workflow_validation')or{}
    if (workflow.get('directed_body')and workflow.get('recipient_accepted')
            and not workflow.get('callback_available')and not workflow.get('final_refusal')):
        wanted.add('callback')
    if ((metadata.get('message_delivery_validation')or{}).get('review_required')
            and metadata.get('quality_contact_type')!='TITULAR'):
        wanted.add('callback')
    return wanted


def windows(data,wanted):
    duration=float(data.get('duracion_segundos')or 0)
    if not math.isfinite(duration)or duration<=0:return []
    result=[]
    if 'holder'in wanted:
        result.append(('holder',[(0.,min(duration,28.)),(0.,min(duration,33.))]))
    if 'callback'in wanted:
        cues=[]
        for segment in data.get('segmentos')or[]:
            if re.search(r'\b(?:numero|telefono|anotar|whatsapp)\b',normalize(segment.get('texto',segment.get('text','')))):
                value=segment.get('inicio',segment.get('start'))
                if isinstance(value,(float,int))and 0<=value<duration:cues.append(float(value))
        at=cues[-1]if cues else max(0.,duration-30.)
        start=max(0.,at-6.)
        result.append(('callback',[(start,min(duration,start+35.)),
                                   (max(0.,start-3.),min(duration,start+40.))]))
    return result


def collect(audio_path,data,relation,metadata,read_window,model):
    """read_window lee PCM real mediante el modelo ya cargado, sin prompt de cuenta."""
    requested=needs_recovery(metadata)
    plan=windows(data,requested)
    if not plan:return None
    path=Path(audio_path)
    record={'schema':SCHEMA,'kind':'LOCAL_CONTEXT_ASR_CONSENSUS',
        'source_binding':binding(data,relation),'audio_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'audio_file':path.name,'model':str(model),'human_verified':False,
        'speaker_roles_confirmed':False,'groups':[]}
    for purpose,pair in plan:
        attempts=[]
        for (start,end),beam in zip(pair,(5,10)):
            attempt={'start':start,'end':end,'beam_size':beam}
            try:
                reading=read_window(start,end,beam)
                attempt.update(text=str(reading.get('text')or''),segments=reading.get('segments')or[])
            except Exception as error:
                attempt.update(text='',segments=[],error=type(error).__name__)
            attempts.append(attempt)
        record['groups'].append({'purpose':purpose,'attempts':attempts})
    record['record_sha256']=record_digest(record)
    return record


def validate(record,data,relation,audio_path):
    result={'present':record is not None,'valid':False,'holder':False,'callback':None,
            'evidence':[],'risks':[],'review_required':False,
            'human_verified':False,'method':'LOCAL_CONTEXT_ASR_CONSENSUS'}
    if record is None:return result
    try:
        path=Path(audio_path)
        if (record.get('schema')!=SCHEMA or record.get('kind')!='LOCAL_CONTEXT_ASR_CONSENSUS'
                or record.get('human_verified')is not False or record.get('speaker_roles_confirmed')is not False
                or record.get('record_sha256')!=record_digest(record)
                or record.get('source_binding')!=binding(data,relation)
                or path.name!=record.get('audio_file')or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest()!=record.get('audio_sha256')):
            result['reason']='La relectura no corresponde al audio, texto y cuenta actuales.'
            return result
        duration=float(data.get('duracion_segundos')or 0)
        if not math.isfinite(duration)or duration<=0:raise ValueError('Duración inválida')
        result['valid']=True
        for group in record.get('groups')or[]:
            attempts=group.get('attempts')or[]
            if len(attempts)!=2 or [a.get('beam_size')for a in attempts]!=[5,10]:continue
            if any(a.get('error')or not reading_quality(a)for a in attempts):continue
            if any(not(0<=float(a['start'])<float(a['end'])<=duration+.01)
                   or float(a['end'])-float(a['start'])>45 for a in attempts):continue
            if (attempts[0]['start'],attempts[0]['end'])==(attempts[1]['start'],attempts[1]['end']):continue
            # Una relectura no puede aportar solamente hechos favorables e
            # ignorar una expresión ofensiva que la primera lectura omitió.
            for attempt in attempts:
                offensive=re.search(r'\b(?:que poca madre|chingad[ao]s?|chingues|chingue|'
                    r'pendej[oa]s?|cabron(?:a|es)?|mierda|pinche|put[ao]s?)\b',normalize(attempt['text']))
                if offensive:
                    result['risks'].append({'type':'EXPRESION_OFENSIVA_SIN_VOZ_CONFIRMADA',
                        'text':attempt['text'],'start':attempt['start'],'end':attempt['end'],
                        'human_verified':False})
            if group.get('purpose')=='holder':
                if any(a['start']!=0 or a['end']>34 for a in attempts):continue
                source=normalize(data.get('texto'))
                from app.services.contact_dialogue_resolution import declared_intermediary
                from app.services.context_rules import unknown_debtor_statement
                from app.services.conversation_evidence import assess_recado
                raw_segments=data.get('segmentos')or[]
                if (COUNTER.search(source)or proxy_account_evidence(data.get('texto'),raw_segments)
                    or declared_intermediary(data.get('texto'),raw_segments)['confirmed']
                    or unknown_debtor_statement(data.get('texto'),raw_segments)
                    or assess_recado(data.get('texto'),raw_segments)['family']):continue
                source_names=nominal_words(data.get('texto'))
                names=[nominal_words(a['text'])for a in attempts]
                if not source_names or any(source_names!=n for n in names):continue
                proofs=[]
                for attempt in attempts:
                    value=attempt['text']
                    contradicted=(COUNTER.search(normalize(value))or proxy_account_evidence(value)
                        or declared_intermediary(value)['confirmed']or unknown_debtor_statement(value)
                        or assess_recado(value)['family'])
                    direct=recipient_statement(value,[],r'\b(?:soy yo|soy (?:el|la) titular|habla (?:el|la) titular)\b')
                    proof=holder_confirmation(value)
                    proofs.append({'confirmed':not contradicted and(proof['confirmed']or direct)})
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
                    result['evidence'].append({'purpose':'callback','texts':[a['text']for a in attempts],
                        'method':'CALLBACK_MATCH_IN_TWO_LOCAL_READINGS','source':'LOCAL_AUDIO_CONTEXT',
                        'human_verified':False})
        if result['risks']:
            result.update(review_required=True,
                reason='La relectura local detectó lenguaje ofensivo sin voz confirmada; verificar el fragmento.')
    except (ValueError,TypeError,KeyError,AttributeError,OSError):
        result.update(valid=False,holder=False,callback=None,reason='Registro de relectura incompleto o no verificable.')
    return result
