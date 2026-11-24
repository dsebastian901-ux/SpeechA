"""Comparación por archivo estable; nunca emparejar por posición o nombre de cuenta."""
from collections import Counter
import hashlib
import json
from pathlib import Path


def stable_items(payload):
    found={}
    for item in payload.get('items')or[]:
        name=str(item.get('file_name')or(item.get('result')or{}).get('archivo')or'')
        if not name or '/'in name or '\\'in name or ':'in name:
            raise ValueError('La comparación exige identificadores de archivo válidos.')
        key=name.casefold()
        if key in found:raise ValueError('Identificador duplicado; no se puede comparar de forma segura.')
        found[key]=item
    return found


def compare_payloads(before, after):
    old=stable_items(before);new=stable_items(after)
    if old.keys()!=new.keys():
        raise ValueError('Los checkpoints no contienen los mismos identificadores de llamada.')
    rows=[]
    for key in sorted(old):
        first,last=old[key],new[key]
        previous=first.get('classification')or{};current=last.get('classification')or{}
        context=(last.get('analytics_metadata')or{}).get('context_audio_validation')or{}
        old_codes={f['code']for f in previous.get('decision_findings',[])if
                   f.get('severity')in{'REVIEW','CRITICAL','PENDING_ALERT'}}
        new_codes={f['code']for f in current.get('decision_findings',[])if
                   f.get('severity')in{'REVIEW','CRITICAL','PENDING_ALERT'}}
        approved=str(current.get('clasificacion')or'').startswith('APROBADO')
        rows.append({'id':key,'before':previous.get('clasificacion'),
            'after':current.get('clasificacion'),'score_before':first.get('compliance_score'),
            'score_after':last.get('compliance_score'),'changed':previous.get('clasificacion')!=current.get('clasificacion'),
            'removed_blocking_codes':sorted(old_codes-new_codes),
            'remaining_blocking_codes':sorted(new_codes),
            'approval_with_pending_block':bool(approved and new_codes),
            'approval_transition_requires_evidence_audit':bool(approved and old_codes-new_codes),
            'identity_evidence':(last.get('analytics_metadata')or{}).get('contact_validation')or{},
            'recovered_evidence_valid':context.get('valid'),
            'fact_validations':context.get('fact_validations',[]),
            'justification':current.get('motivo')or'',
            'second_listening':last.get('relectura_r59')})
    return {'calls':len(rows),'before':dict(Counter(r['before']for r in rows)),
            'after':dict(Counter(r['after']for r in rows)),
            'changed':sum(r['changed']for r in rows),
            'transitions':dict(Counter(str(r['before'])+' -> '+str(r['after'])for r in rows)),
            'rows':rows}


def compare_checkpoints(before, after, output_file):
    paths=[Path(before).resolve(),Path(after).resolve()]
    target=Path(output_file).resolve()
    if target in paths or target.exists():raise ValueError('La comparación requiere un archivo de salida nuevo.')
    raw=[p.read_bytes()for p in paths]
    result=compare_payloads(*(json.loads(value.decode('utf-8-sig'))for value in raw))
    result['source_sha256']=[hashlib.sha256(value).hexdigest()for value in raw]
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8')as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    if any(p.read_bytes()!=value for p,value in zip(paths,raw)):
        raise RuntimeError('Un archivo de origen cambió durante la comparación.')
    return result
