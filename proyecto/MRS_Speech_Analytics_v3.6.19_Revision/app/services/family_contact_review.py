"""Parentesco confirmado por el usuario, ligado a la llamada y separado de ASR."""
from copy import deepcopy
from datetime import datetime, timezone
import re

from app.services.audio_block_evidence import binding, digest
from app.services.conversation_evidence import normalize

SCOPE='FAMILY_RELATIONSHIP_ONLY'
RELATIONSHIPS=frozenset({'HIJA','HIJO','MADRE','PADRE','ESPOSA','ESPOSO','HERMANA','HERMANO',
                         'ABUELA','ABUELO','TIA','TIO','PRIMA','PRIMO','FAMILIAR'})


def review_digest(record):
    return digest({k:record.get(k) for k in ('schema','scope','source_binding','relationship','user_confirmed','active','source')})


def make_family_confirmation(data,relation,relationship,*,user_confirmed=False):
    if user_confirmed is not True:
        raise ValueError('El parentesco requiere una confirmación explícita del usuario.')
    relationship=normalize(relationship).upper()
    if relationship not in RELATIONSHIPS:
        raise ValueError('Parentesco no reconocido; use HIJA, HIJO u otro familiar de la lista.')
    if (not isinstance(data,dict) or not data.get('archivo') or not str(data.get('texto') or '').strip()
            or not isinstance(relation,dict) or not re.fullmatch(r'\d{16}',str(relation.get('numero_de_tarjeta') or ''))):
        raise ValueError('Faltan transcripción o tarjeta de origen para vincular la confirmación.')
    record={'schema':1,'scope':SCOPE,'source_binding':binding(data,relation),'relationship':relationship,
            'source':'EXPLICIT_USER_FAMILY_CONFIRMATION','user_confirmed':True,'active':True,
            'reviewed_at':datetime.now(timezone.utc).isoformat()}
    record['record_sha256']=review_digest(record)
    return record


def validate_family_confirmation(data,relation,record):
    status={'present':record is not None,'valid':False,'user_confirmed':False,'review_required':False,
            'relationship':'','record':deepcopy(record)}
    if record is None:return status
    status.update(review_required=True,reason='La confirmación de parentesco no corresponde a la llamada actual; revisar o revocar.')
    try:
        expected=make_family_confirmation(data,relation,record.get('relationship'),user_confirmed=record.get('user_confirmed'))
        if (record.get('active') is not True or record.get('record_sha256')!=review_digest(record)
                or any(record.get(k)!=expected[k] for k in ('schema','scope','source_binding','relationship','source'))):
            return status
    except (ValueError,TypeError,AttributeError):
        return status
    status.update(valid=True,user_confirmed=True,review_required=False,relationship=expected['relationship'])
    status.pop('reason',None)
    return status
