"""Incorporar lecturas ASR como evidencia separada, sin sustituir hechos originales."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

from app.services.asr_evidence_quality import block_reading_quality,usable_groups
from app.services.conversation_evidence import normalize,SENSITIVE
from app.services.transcription_services import TranscriptionService


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def binding(result,relation):
    return digest({'file_name':result.get('archivo'),'text':TranscriptionService._normalize_asr_money_display(str(result.get('texto') or '')).strip(),
        'segments':result.get('segmentos') or [],'duration':float(result.get('duracion_segundos') or 0),
        'account':{k:v for k,v in (relation or {}).items() if k!='nombre_final'}})


def record_digest(record):
    return digest({k:record.get(k) for k in ('schema','kind','binding','source_checkpoint_sha256',
        'receipt_sha256','audio_sha256','model','human_verified','speaker_roles_confirmed',
        'text','segments','tail_text','tail_segments')})


def clean_segments(values):
    allowed={'id','seek','start','end','text','tokens','temperature','avg_logprob','compression_ratio','no_speech_prob','words'}
    result=[]
    if not isinstance(values,list):raise ValueError('La lectura no contiene segmentos ASR válidos.')
    for value in values:
        if not isinstance(value,dict) or not isinstance(value.get('text'),str):raise ValueError('Segmento ASR no válido.')
        item={k:deepcopy(v) for k,v in value.items() if k in allowed}
        if item.get('words'):
            item['words']=[{k:deepcopy(v) for k,v in word.items() if k in {'start','end','word','probability'}} for word in item['words']]
        result.append(item)
    return result


def validate_evidence(record,result,relation,contact_type,positive_evaluator=None):
    if record is None:return {'present':False,'valid':True,'review_required':False,'risks':[]}
    if (not isinstance(record,dict) or record.get('schema')!=1 or record.get('kind')!='AUTOMATED_ASR_ONLY'
            or record.get('binding')!=binding(result,relation) or record.get('human_verified') is not False
            or record.get('speaker_roles_confirmed') is not False):
        return {'present':True,'valid':False,'review_required':True,'risks':[],
                'reason':'La lectura adicional no corresponde a la transcripción o cuenta actual; revisar evidencia.'}
    if record.get('record_sha256')!=record_digest(record):
        return {'present':True,'valid':False,'review_required':True,'risks':[],
                'reason':'La lectura adicional cambió después de incorporarse; revisar evidencia.'}
    try:
        primary=clean_segments(record['segments']);tail=clean_segments(record.get('tail_segments') or [])
    except (KeyError,TypeError,ValueError):
        return {'present':True,'valid':False,'review_required':True,'risks':[], 'reason':'Lectura adicional mal formada.'}
    quality=block_reading_quality(primary,tail);risks=[]
    for mode,segments in [('LECTURA_COMPLETA',primary),('CIERRE',tail)]:
        for text in usable_groups(segments):
            s=normalize(text)
            if contact_type!='TITULAR' and SENSITIVE.search(s):
                risks.append({'type':'PRIVACIDAD_SIN_HABLANTE_CONFIRMADO','source':mode,
                              'evidence':SENSITIVE.search(s).group()})
            offensive=re.search(r'\b(?:que poca madre|pendej[oa]|cabron[a]?|mierda|pinche|puta|puto)\b|(?<!\w)uta[.!?¡¿\s]*$',s)
            if offensive:risks.append({'type':'EXPRESION_OFENSIVA_SIN_HABLANTE_CONFIRMADO','source':mode,'evidence':offensive.group()})
            if positive_evaluator is not None:
                detected=positive_evaluator(text,dict(relation))
                # Solo señales positivas: nunca las omisiones de una lectura
                # parcial, su puntaje o su dictamen como sustituto del original.
                card=detected.get('card_validation') or {}
                if card.get('result')=='TARJETA INCORRECTA' or str(card.get('result') or '').startswith('REVISAR -'):
                    risks.append({'type':'REFERENCIA_ADICIONAL_POR_CONFIRMAR','source':mode,'evidence':card.get('reason') or card.get('result')})
                for penalty in detected.get('penalties') or []:
                    if penalty.get('id') in {'PEN002','PEN003','PEN004','PEN005','PEN012','PEN_CONV_FRAUDE','PEN_QUEJA_MALTRATO'}:
                        risks.append({'type':'ALERTA_NO_CONFIRMADA_'+penalty['id'],'source':mode,'evidence':penalty['reason']})
                n=detected.get('negotiation_validation') or {}
                if n.get('amount_invalid') and n.get('commitment_confirmed'):
                    risks.append({'type':'IMPORTE_ADICIONAL_POR_CONFIRMAR','source':mode,'evidence':n.get('motivo_validacion_monto','')})
                if contact_type=='TITULAR' and detected.get('contact_type') in {'TERCERO','TERCERO / FAMILIAR','TERCERO / TRABAJO','NO CONOCEN A DEUDOR'}:
                    risks.append({'type':'INTERLOCUTOR_CON_LECTURAS_CONTRADICTORIAS','source':mode,'evidence':detected['contact_type']})
            old=normalize(result.get('texto'))
            if (re.search(r'\bno (?:le )?voy a pasar su recado\b',old)
                    and re.search(r'\byo le voy a (?:poner|pasar) su recado\b',s)):
                risks.append({'type':'RECADO_CON_LECTURAS_CONTRADICTORIAS','source':mode,
                              'evidence':'El texto original y la lectura adicional difieren en la negación del recado.'})
    risks=[dict(t) for t in {tuple(sorted(r.items())) for r in risks}]
    risks.sort(key=lambda r:(r['type'],r['source'],r['evidence']))
    return {'present':True,'valid':True,'review_required':bool(risks),'quality':quality,'risks':risks,
            'human_verified':False,'reason':('Lectura adicional con señales contradictorias o de cumplimiento pendientes de confirmar; revisar audio.' if risks else '')}


def attach_audio_block(master_path,evidence_path,output_directory=None,*,source_checkpoint=None):
    from app.services.checkpoint_output import create_checkpoint_output
    from app.services.checkpoint_reanalysis import reanalyze_checkpoint
    from app.services.analytics_service import AnalyticsService
    master_path=Path(master_path).resolve();evidence_path=Path(evidence_path).resolve()
    raw=master_path.read_bytes();original=json.loads(raw.decode('utf-8-sig'))
    evidence_raw=evidence_path.read_bytes();evidence=json.loads(evidence_raw.decode('utf-8-sig'))
    if not isinstance(original,dict) or not original.get('items'):raise ValueError('El lote no contiene llamadas.')
    items=original['items'];names=[i.get('file_name') for i in items]
    if not all(names) or len(set(names))!=len(names):raise ValueError('El lote contiene llamadas ausentes o duplicadas.')
    master={i['file_name']:i for i in items};origin=None
    if evidence.get('schema')!=1 or not evidence.get('items') or evidence.get('human_verified') is not False:
        raise ValueError('Seleccione un JSON de lecturas ASR, no un checkpoint o aprobación.')
    if (evidence.get('whisper_executed') is not True or evidence.get('completed_calls')!=len(evidence['items'])
            or evidence.get('errors')!=0):
        raise ValueError('La fuente no acredita lecturas ASR completas sin errores.')
    if evidence.get('source_checkpoint_sha256')!=hashlib.sha256(raw).hexdigest():
        if source_checkpoint is not None:
            source_raw=Path(source_checkpoint).read_bytes()
            if hashlib.sha256(source_raw).hexdigest()!=evidence.get('source_checkpoint_sha256'):
                raise ValueError('El checkpoint de origen no coincide con el hash de la lectura.')
            source=json.loads(source_raw.decode('utf-8-sig'))
            source_items=source.get('items') or [];origin={i['file_name']:i for i in source_items}
            if len(origin)!=len(source_items):raise ValueError('El origen contiene duplicados.')
        else:origin={}
    records={}
    for read in evidence['items']:
        name=read.get('file_name')
        if name not in master or name in records:raise ValueError('Lectura ajena al lote o repetida.')
        target=master[name];data=target.get('result') or {};relation=target.get('relation') or {}
        if origin is not None:
            if name in origin:
                old=origin[name]
                if {k:v for k,v in old.get('relation',{}).items() if k!='nombre_final'}!={k:v for k,v in relation.items() if k!='nombre_final'}:
                    raise ValueError('La cuenta cambió respecto del origen de la lectura.')
                if any((old.get('result') or {}).get(k)!=(data or {}).get(k) for k in ('texto','segmentos','duracion_segundos')):
                    raise ValueError('El texto cambió respecto del checkpoint que originó la lectura.')
            elif read.get('source_binding')!=binding(data,relation):
                raise ValueError('La lectura pertenece a otro checkpoint; se necesita su origen para comprobar la cuenta.')
        if (read.get('original_text')!=data.get('texto') or read.get('original_segments')!=data.get('segmentos')
                or read.get('original_text_sha256')!=hashlib.sha256(str(data.get('texto') or '').encode()).hexdigest()
                or abs(float(read.get('audio_duration') or 0)-float(data.get('duracion_segundos') or 0))>.25
                or not re.fullmatch(r'[0-9a-f]{64}',str(read.get('audio_sha256') or ''))):
            raise ValueError('Texto, segmentos, duración o identificación de audio no coinciden; no se incorpora la lectura.')
        if read.get('status')!='completado':raise ValueError('La lectura contiene errores; incorporar solo resultados completos.')
        record={'schema':1,'kind':'AUTOMATED_ASR_ONLY','binding':binding(data,relation),
                'source_checkpoint_sha256':evidence['source_checkpoint_sha256'],
                'receipt_sha256':hashlib.sha256(evidence_raw).hexdigest(),'audio_sha256':read['audio_sha256'],
                'model':evidence.get('model'),'human_verified':False,'speaker_roles_confirmed':False,
                'text':str(read.get('text') or ''),'segments':clean_segments(read.get('segments')),
                'tail_text':str(read.get('tail_text') or ''),'tail_segments':clean_segments(read.get('tail_segments') or [])}
        if (' '.join(s['text'].strip() for s in record['segments'])!=record['text']
                or ' '.join(s['text'].strip() for s in record['tail_segments'])!=record['tail_text']):
            raise ValueError('El texto ASR no coincide con sus segmentos; no se incorpora.')
        record['record_sha256']=record_digest(record)
        record['quality']=block_reading_quality(record['segments'],record['tail_segments']);records[name]=record
    updated=deepcopy(original)
    for item in updated['items']:
        if item['file_name'] in records:
            previous=item.get('audio_block_evidence')
            if previous and previous!=records[item['file_name']]:item.setdefault('audio_block_evidence_history',[]).append(previous)
            item['audio_block_evidence']=records[item['file_name']]
    target=create_checkpoint_output(output_directory,'Evidencia_Audios_'+AnalyticsService.ENGINE_REVISION.rsplit('-',1)[-1]+'_',nested_results=True)
    intermediate=target/'checkpoint_con_lecturas.json';intermediate.write_text(json.dumps(updated,ensure_ascii=False,indent=2),encoding='utf-8')
    output=reanalyze_checkpoint(intermediate,target/'resultados')
    final=Path(output['checkpoint']);payload=json.loads(final.read_text());payload['audio_block_import']={
        'source_master_sha256':hashlib.sha256(raw).hexdigest(),'reading_sha256':hashlib.sha256(evidence_raw).hexdigest(),
        'matched_calls':len(records),'human_verified':False,'original_results_preserved':True,'whisper_executed':False}
    payload['audio_block_import']['source_engine_revision']=evidence.get('engine_revision')
    payload['audio_block_import']['source_whisper_executed']=evidence.get('whisper_executed') is True
    final.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    from openpyxl import load_workbook
    book=load_workbook(output['report']);note=book['NOTA_REANALISIS']
    note['A2']='Esta incorporación no ejecutó Whisper ni copió audios; usa las lecturas ASR recibidas por separado.'
    note.append(['Lecturas adicionales vinculadas',len(records)])
    note.append(['Lecturas con alertas técnicas (no infracciones)',sum(r['quality']['degraded'] for r in records.values())])
    note.append(['Voces o hechos confirmados por una persona en esta incorporación',0])
    note.append(['Las transcripciones originales y las confirmaciones previas permanecen intactas.'])
    book.save(output['report']);book.close()
    assert master_path.read_bytes()==raw and evidence_path.read_bytes()==evidence_raw
    return dict(output,matched_calls=len(records))
