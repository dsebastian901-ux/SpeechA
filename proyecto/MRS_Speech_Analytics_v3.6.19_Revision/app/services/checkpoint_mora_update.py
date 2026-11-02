"""Recuperar solo mora faltante desde cuentas verificadas, sin reinterpretar audios."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re

from app.services.mora_payment_policy import REGULARIZATION_MORAS, LIQUIDATION_MORAS
from app.services.relation_service import RelationService


def fill_missing_mora(payload, excel_path):
    source=Path(excel_path).expanduser().resolve()
    raw=source.read_bytes()
    service=RelationService()
    loaded=service.load_excel(source)
    records={r.archivo_original:r.to_dict() for r in service.records}
    invalid={r.get('archivo_original') for r in loaded['errores']}
    items=payload.get('items')
    if not isinstance(items,list) or not items:
        raise ValueError('El checkpoint no contiene llamadas.')
    names=[i.get('file_name') for i in items]
    if not all(names) or len(names)!=len(set(names)):
        raise ValueError('El checkpoint contiene nombres ausentes o duplicados.')
    updated=deepcopy(payload)
    digest=hashlib.sha256(raw).hexdigest()
    timestamp=datetime.now(timezone.utc).isoformat()
    filled=0
    for item in updated['items']:
        name=item['file_name']
        if name in invalid or name not in records:
            raise ValueError('Una llamada no tiene una fila única y válida en el Excel seleccionado.')
        original=records[name]
        relation=item.get('relation')
        if not isinstance(relation,dict):
            raise ValueError('Una llamada no contiene datos de cuenta para cotejar.')
        card=str(relation.get('numero_de_tarjeta') or '')
        if not re.fullmatch(r'\d{16}',card) or card!=original['numero_de_tarjeta']:
            raise ValueError('La tarjeta del Excel no coincide con la cuenta del checkpoint.')
        for key,value in relation.items():
            if key not in {'asignacion','nombre_final'} and (key not in original or value!=original[key]):
                raise ValueError(f'Cambió un dato de cuenta ajeno a mora: {key}. No se incorporó el Excel.')
        if relation.get('nombre_final')!=original['nombre_final']:
            review=item.get('output_name_review') or {}
            if (review.get('source')!='EXPLICIT_USER_CHOICE_NUMERO_DE_TARJETA'
                    or review.get('previous_name')!=original['nombre_final']
                    or review.get('corrected_name')!=relation.get('nombre_final')):
                raise ValueError('El nombre de salida difiere del Excel sin su corrección autorizada previa.')
        mora=original['asignacion']
        canonical=service._mora_key(mora)
        if canonical not in REGULARIZATION_MORAS|LIQUIDATION_MORAS:
            raise ValueError('Una cuenta tiene mora vacía o no reconocida en el Excel.')
        current=relation.get('asignacion') or ''
        if current:
            if service._mora_key(current)!=canonical:
                raise ValueError('La mora existente contradice el Excel; no se sobrescribe.')
            continue
        relation['asignacion']=mora
        item['mora_excel_import']={
            'policy':'FILL_MISSING_MORA_ONLY','source_workbook':source.name,
            'source_workbook_sha256':digest,'source_sheet':'Relacion_Audios',
            'previous_value':current,'imported_value':mora,'canonical_value':canonical,
            'card_and_existing_account_fields_checked':True,'imported_at':timestamp,
            'new_human_audio_confirmation':False,
        }
        filled+=1
    summary={'source_workbook':source.name,'source_workbook_sha256':digest,
             'source_sheet':'Relacion_Audios','policy':'FILL_MISSING_MORA_ONLY',
             'evaluations':len(items),'filled':filled,'already_present':len(items)-filled,
             'other_account_fields_changed':False,'whisper_executed':False,
             'new_human_audio_confirmations':0}
    updated['mora_excel_update']=summary
    assert source.read_bytes()==raw,'El Excel cambió durante la lectura.'
    return updated,summary
