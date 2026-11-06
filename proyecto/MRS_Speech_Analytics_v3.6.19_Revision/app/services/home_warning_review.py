"""Advertencia en domicilio confirmada por usuario, limitada a la llamada y mora."""
from copy import deepcopy
from datetime import datetime,timezone
import re
from app.services.audio_block_evidence import binding,digest,validate_evidence
from app.services.conversation_evidence import assess_home_recovery_warning

SCOPE='GESTOR_HOME_RECOVERY_WARNING_IN_1_2PV_ONLY'


def warning_candidates(data,relation,audio_evidence=None):
    mora=re.sub(r'[^A-Z0-9]','',str(relation.get('asignacion') or '').upper())
    mora={'1':'1PV','MORA1':'1PV','2':'2PV','MORA2':'2PV'}.get(mora,mora)
    sources=[('ORIGINAL',data.get('texto',''),data.get('segmentos') or [],binding(data,relation))]
    if audio_evidence is not None:
        check=validate_evidence(audio_evidence,data,relation,'TERCERO')
        if check['valid'] and not check.get('quality',{}).get('degraded'):
            for label,text,segments in [('ASR_ADICIONAL','text','segments'),('CIERRE_ASR','tail_text','tail_segments')]:
                sources.append((label,audio_evidence.get(text,''),audio_evidence.get(segments) or [],audio_evidence['record_sha256']))
    found=[]
    for source,text,segments,checksum in sources:
        for unit in assess_home_recovery_warning(text,segments,mora)['evidence']:
            candidate={'source':source,'source_hash':checksum,'text':unit['text'],
                       'start':unit['start'],'end':unit['end'],'mora':mora}
            if candidate not in found:found.append(candidate)
    return found


def review_digest(record):
    return digest({k:record.get(k) for k in ('schema','scope','source_binding','evidence','source',
        'actor','actor_confirmed','warning_confirmed','active')})


def make_warning_confirmation(data,relation,evidence,*,actor_confirmed=False,warning_confirmed=False,audio_evidence=None):
    if actor_confirmed is not True or warning_confirmed is not True:
        raise ValueError('Confirme explícitamente que el gestor dice la advertencia escuchada.')
    if (not isinstance(data,dict) or not data.get('archivo') or not str(data.get('texto') or '').strip()
            or not isinstance(relation,dict) or not re.fullmatch(r'\d{16}',str(relation.get('numero_de_tarjeta') or ''))):
        raise ValueError('Faltan transcripción o tarjeta para vincular la advertencia.')
    if evidence not in warning_candidates(data,relation,audio_evidence):
        raise ValueError('La advertencia no corresponde a esta llamada y cuenta de 1–2 PV.')
    record={'schema':1,'scope':SCOPE,'source_binding':binding(data,relation),'evidence':deepcopy(evidence),
            'source':'EXPLICIT_USER_HOME_WARNING_CONFIRMATION','actor':'GESTOR','actor_confirmed':True,
            'warning_confirmed':True,'active':True,'reviewed_at':datetime.now(timezone.utc).isoformat()}
    record['record_sha256']=review_digest(record)
    return record


def validate_warning_confirmation(data,relation,record,audio_evidence=None):
    status={'present':record is not None,'valid':False,'review_required':False,'record':deepcopy(record)}
    if record is None:return status
    status.update(review_required=True,reason='La confirmación de advertencia no corresponde al contexto actual; revisar o revocar.')
    try:
        expected=make_warning_confirmation(data,relation,record.get('evidence'),
            actor_confirmed=record.get('actor_confirmed'),warning_confirmed=record.get('warning_confirmed'),audio_evidence=audio_evidence)
        if (record.get('active') is not True or record.get('record_sha256')!=review_digest(record)
                or any(record.get(k)!=expected[k] for k in ('schema','scope','source_binding','source','actor'))):return status
    except (ValueError,TypeError,AttributeError,KeyError):return status
    status.update(valid=True,review_required=False)
    status.pop('reason',None)
    return status
