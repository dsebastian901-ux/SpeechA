"""Ventanas de corroboración ancladas al ASR; no ejecuta ni activa modelos."""
import math
import re

from app.services.conversation_evidence import normalize

FIELDS = {
    'ASSET_COERCION_REVIEW': ('treatment_validation',),
    'CONVENIO_OUTCOME_CONFLICT': ('negotiation_validation','status_validation'),
    'MISTREATMENT_REPORT': ('treatment_validation',),
    'THIRD_PARTY_PAYMENT_GUIDANCE': ('convenio_payment_validation',),
    'UNIDENTIFIED_CONTACT': ('contact_validation',),
    'UNCERTAIN_DISCLOSURE': ('privacy_validation',),
    'CARD_REFERENCE': ('card_validation',),
    'RECEIPT_UNCERTAIN': ('convenio_payment_validation',),
    'HOME_WARNING_UNATTRIBUTED': ('home_recovery_warning',),
    'OFFENSIVE_LANGUAGE': ('treatment_validation',),
    'UNCERTAIN_CONFRONTATION': ('treatment_validation',),
    'PAYMENT_DESTINATION': ('convenio_payment_validation',),
    'NEGOTIATION_INVALID_OR_UNCERTAIN': ('negotiation_validation',),
    'PAYMENT_OUTCOME_NOT_CONFIRMED': ('negotiation_validation',),
    'CALLBACK_NOT_DELIVERED': ('message_delivery_validation',),
    'MESSAGE_RECEIPT_NOT_CONFIRMED': ('message_workflow_validation',),
    'MESSAGE_BODY_NOT_CONFIRMED': ('message_workflow_validation',),
}
CUES = {
    'ASSET_COERCION_REVIEW': r'\b(?:bienes|muebles|vend\w*|empen\w*|penalizacion|penalidad)\b',
    'MISTREATMENT_REPORT': r'\b(?:atencion|queja|grit\w*|maltrat\w*|trataron mal|colg\w*)\b',
    'CARD_REFERENCE': r'\b(?:terminacion|digitos|referencia|tarjeta)\b',
    'UNCERTAIN_DISCLOSURE': r'\b(?:saldo|mensualidad|pesos|deuda|adeudo)\b',
    'RECEIPT_UNCERTAIN': r'\b(?:comprobante|ticket|whatsapp|foto)\b',
    'HOME_WARNING_UNATTRIBUTED': r'\b(?:bienes|domicilio|abogados|licenciados)\b',
    'OFFENSIVE_LANGUAGE': r'\b(?:chingad\w*|pendej\w*|madre|cabron\w*|pinche)\b',
    'PAYMENT_DESTINATION': r'\b(?:transferencia|cuenta|clabe|banco|aplicacion)\b',
    'CALLBACK_NOT_DELIVERED': r'\b(?:telefono|numero|anotar|whatsapp)\b',
    'MESSAGE_RECEIPT_NOT_CONFIRMED': r'\b(?:recado|mensaje|avisar|anotar|digame)\b',
    'MESSAGE_BODY_NOT_CONFIRMED': r'\b(?:recado|mensaje|comunique|avisar)\b',
}


def _quotes(value, depth=0):
    if depth>5:return
    if isinstance(value,dict):
        for key,child in value.items():
            if key in {'text','texto','phrase','evidence','evidencia_monto','evidencia_saldo_informado'}and isinstance(child,str)and child.strip():
                yield normalize(child)
            elif isinstance(child,(dict,list)):
                yield from _quotes(child,depth+1)
    elif isinstance(value,list):
        for child in value:yield from _quotes(child,depth+1)


def _timeline(data):
    source=normalize(data.get('texto'));cursor=0;rows=[]
    for segment in data.get('segmentos')or[]:
        text=normalize(segment.get('text',segment.get('texto','')))
        start=segment.get('start',segment.get('inicio'));end=segment.get('end',segment.get('fin'))
        if not text or not all(isinstance(v,(int,float))and math.isfinite(v)for v in (start,end))or not 0<=start<end:continue
        duration=data.get('duracion_segundos')
        if isinstance(duration,(int,float))and math.isfinite(duration)and duration>0 and end>duration+.01:continue
        at=source.find(text,cursor)
        if at<0:continue
        cursor=at+len(text)
        rows.append({'start':float(start),'end':float(end),'lo':at,'hi':cursor,'text':text})
    return source,rows


def _closing_exchange(data,timeline,active=None):
    """Locate the current negotiation's question, answer and recap together."""
    from app.services.payment_lifecycle import frames,financial_response_events
    from app.services.conversation_evidence import payment_commitment
    from app.services.negotiation_chronology import scope_start
    text=data.get('texto')or'';segments=data.get('segmentos')or[]
    rows=frames(text,segments)
    events=financial_response_events(text,segments)
    from app.services.negotiation_resolution import resolve_negotiation
    active=active or resolve_negotiation(text,segments,None)
    commitment=active['commitment']
    final=commitment.get('position',0)
    floor=scope_start(text,len(normalize(text)))
    anchors=([(active['start'],active['end'])] if active.get('plan_scope_proven') and active['start']is not None and active['end']is not None and active['start']>=floor else
             [(e.get('offer_position',e['position']),e['end']) for e in events if e['position']>=floor])
    if active['kind']=='ACCEPTED' and not active.get('plan_scope_proven'):
        # A generic acceptance refers back to a plan, not just its own words.
        # Include the immediately preceding proposal even if an earlier amount
        # question was also recognized elsewhere in the conversation.
        for i,row in enumerate(rows):
            if row['start']<=final<=row['end']:
                anchors.append((max(floor,rows[max(0,i-1)]['start']),row['end']))
                break
    if not anchors:
        for i,row in enumerate(rows[:-1]):
            if row['start']<floor or row['role']in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
            if re.search(r'\b(?:confirm\w*|acordamos|cantidad|monto|fecha)\b',row['text']) and re.search(
                    r'\b(?:pago|pagar|pagos|deposit|aplic|acordamos)\w*',row['text']):
                anchors.append((row['start'],rows[min(i+2,len(rows)-1)]['end']))
    if final>=floor and not anchors:
        for index,row in enumerate(rows):
            if row['start']<=final<=row['end']:
                anchors.append((max(floor,rows[max(0,index-1)]['start']),rows[min(index+1,len(rows)-1)]['end']))
                break
    spans=[]
    selected=anchors[-3:]
    if floor:
        # Include the validation area's first payment exchange, even when ASR
        # damaged its amount/date question. Do not carry the former agent's
        # alternative through a long phone-dictation interval.
        for index,row in enumerate(rows):
            if row['start']>=floor and re.search(r'\b(?:pago|pagar|movimiento)\b',row['text']):
                selected.insert(0,(row['start'],rows[min(index+3,len(rows)-1)]['end']))
                break
    for lo,hi in selected:
        covered=[r for r in timeline if r['lo']<hi and lo<r['hi']]
        if covered:spans.append((covered[0]['start'],covered[-1]['end']))
    return spans


def _callback_exchange(data,timeline):
    """Last local phone delivery exchange, including its question and reply."""
    cue=re.compile(CUES['CALLBACK_NOT_DELIVERED'])
    matches=[i for i,row in enumerate(timeline)if cue.search(row['text'])]
    if not matches:return []
    cluster=[matches[-1]]
    for index in reversed(matches[:-1]):
        if timeline[cluster[0]]['start']-timeline[index]['end']>45:break
        cluster.insert(0,index)
    first=cluster[0];last=cluster[-1]
    if first>0 and timeline[first]['start']-timeline[first-1]['end']<=8:first-=1
    for index in range(last+1,min(len(timeline),last+3)):
        if timeline[index]['start']-timeline[last]['end']>8:break
        last=index
    return [(timeline[first]['start'],timeline[last]['end'])]


def execution_for_window(item,code,start,end):
    """Un plan no es una escucha; comprobar registro y cobertura del fragmento."""
    if start is None or end is None:return 'NO_EJECUTADO'
    record=item.get('context_asr_recovery')or{}
    if record.get('model')!='Faster-Whisper:medium':return 'NO_EJECUTADO'
    from app.services.context_audio_recovery import record_digest
    from app.services.audio_block_evidence import binding
    if (record.get('record_sha256')!=record_digest(record)
            or record.get('source_binding')!=binding(item.get('result')or{},item.get('relation')or{})):
        return 'REGISTRO_MEDIUM_NO_VINCULADO'
    if not ((item.get('analytics_metadata')or{}).get('context_audio_validation')or{}).get('valid'):
        return 'REGISTRO_MEDIUM_PENDIENTE_DE_VALIDACION'
    if code not in record.get('required_findings',[]):return 'NO_EJECUTADO'
    spans=[(a.get('start'),a.get('end'))for g in record.get('groups',[])for a in g.get('attempts',[])
           if not a.get('error')and all(isinstance(a.get(k),(float,int))and math.isfinite(a[k])for k in ('start','end'))]
    frontier=start
    for a,b in sorted(spans):
        if a>frontier:break
        frontier=max(frontier,b)
    return 'MEDIUM_EJECUTADO_REGISTRO_VALIDADO'if frontier>=end else'NO_EJECUTADO_COMPLETO'


def plan_for_item(item):
    """Conservar cada bloqueo y señalar el intervalo a cotejar, nunca cerrarlo."""
    metadata=item.get('analytics_metadata')or{}
    decision=item.get('classification')or metadata.get('shared_classification')or{}
    if decision.get('clasificacion')=='SIN_RELACION_EXCEL':return []
    findings=[f for f in decision.get('decision_findings',[])if
              f.get('severity')in{'REVIEW','PENDING_ALERT'}]
    if not findings:return []
    data=item.get('result')or{};source,timeline=_timeline(data)
    duration=data.get('duracion_segundos')or 0
    duration=float(duration)if isinstance(duration,(int,float))and math.isfinite(duration)else 0
    primary_codes={f['code']for f in findings if f.get('code')not in{'STATUS_INVALID','STATUS_NOT_CONFIRMED'}}
    result=[]
    for finding in findings:
        code=finding['code']
        if code in{'STATUS_INVALID','STATUS_NOT_CONFIRMED'}and primary_codes:continue
        spans=[];basis='MARCA_ASR_Y_EVIDENCIA_DEL_HALLAZGO'
        if code=='UNIDENTIFIED_CONTACT'and duration>0:
            spans=[(0.,min(duration,40.))];basis='APERTURA_NOMINAL_Y_RESPUESTA'
        elif code=='WAIT_WITHOUT_RESUMPTION':
            for interval in (metadata.get('wait_validation')or{}).get('intervals')or[]:
                a,b=interval.get('start'),interval.get('end')
                if all(isinstance(v,(float,int))and math.isfinite(v)for v in (a,b))and 0<=a<b:
                    spans.append((max(0.,a-3),min(duration,b+3)if duration else b+3))
            basis='INTERVALO_ASR_COMPLETO_NO_PRUEBA_SILENCIO_ACUSTICO'
        elif code=='CALLBACK_NOT_DELIVERED':
            spans=_callback_exchange(data,timeline)
            basis='DICTADO_LOCAL_DE_CONTACTO_PREGUNTA_Y_RESPUESTA'
        elif code in {'CONVENIO_OUTCOME_CONFLICT','NEGOTIATION_INVALID_OR_UNCERTAIN',
                      'PAYMENT_OUTCOME_NOT_CONFIRMED','CONTEXT_AUDIO_UNVERIFIED',
                      'CONTEXT_AUDIO_THIRD_REQUIRED','CONTEXT_AUDIO_THIRD_INSUFFICIENT'}:
            spans=_closing_exchange(data,timeline,(metadata.get('negotiation_validation')or{}).get('active_negotiation'))
            basis='PREGUNTA_RESPUESTA_Y_CIERRE_EN_ORDEN_CRONOLOGICO'
            if not spans:
                # An unintelligible reply may have no parsed financial event.
                # Keep its explicitly located finding instead of falling back
                # to an unrelated midpoint diagnostic window.
                for field in FIELDS.get(code,('negotiation_validation',)):
                    for quote in set(_quotes(metadata.get(field)or{})):
                        if len(quote)<12:continue
                        at=source.find(quote)
                        if at>=0:
                            spans.extend((r['start'],r['end'])for r in timeline
                                         if r['lo']<at+len(quote)and at<r['hi'])
                basis='RESPUESTA_PENDIENTE_LOCALIZADA_EN_EVIDENCIA_ASR'
        else:
            quotes=[]
            for field in FIELDS.get(code,('negotiation_validation',)):
                quotes.extend(_quotes(metadata.get(field)or{}))
            for quote in set(quotes):
                if len(quote)<12:continue  # Un número aislado puede pertenecer a otra referencia.
                at=source.find(quote)
                if at<0:continue
                spans.extend((r['start'],r['end'])for r in timeline if r['lo']<at+len(quote)and at<r['hi'])
            if not spans:
                cue=re.compile(CUES.get(code,r'\b(?:pago|fecha|monto|cantidad|confirm|acuerdo)\w*'))
                spans=[(r['start'],r['end'])for r in timeline if cue.search(r['text'])]
                basis='INDICIO_EXPLICITO_EN_SEGMENTO_ASR'
        if not spans:
            spans=[(None,None)];basis='SIN_MARCAS_ASR_SUFICIENTES_PARA_UBICAR'
        unique=[]
        for a,b in sorted(set(spans),key=lambda p:-1 if p[0]is None else p[0]):
            if a is None:unique.append((a,b));continue
            a=max(0.,a-3)if code not in{'UNIDENTIFIED_CONTACT','WAIT_WITHOUT_RESUMPTION'}else a
            b=min(duration,b+3)if duration and code not in{'UNIDENTIFIED_CONTACT','WAIT_WITHOUT_RESUMPTION'}else b
            if unique and unique[-1][0]is not None and a<=unique[-1][1]and b-unique[-1][0]<=45:
                unique[-1]=(unique[-1][0],max(b,unique[-1][1]))
            else:unique.append((a,b))
        for a,b in unique:
            result.append({'file_name':item.get('file_name')or data.get('archivo'),
                'audio_sha256_expected':(item.get('context_asr_recovery')or{}).get('audio_sha256'),
                'finding_code':code,'start':a,'end':b,'location_basis':basis,
                'missing_evidence':' | '.join(finding.get('reasons')or[]),
                'required_model':'medium','execution':execution_for_window(item,code,a,b),
                'speaker_assignment_required':code in{'ASSET_COERCION_REVIEW','THIRD_PARTY_PAYMENT_GUIDANCE','UNIDENTIFIED_CONTACT','UNCERTAIN_DISCLOSURE','OFFENSIVE_LANGUAGE','HOME_WARNING_UNATTRIBUTED','UNCERTAIN_CONFRONTATION'},
                'classification_preserved':decision.get('clasificacion')})
    return result


def add_medium_plan_sheet(workbook,items):
    sheet=workbook.create_sheet('SEGUNDA_ESCUCHA_MEDIUM')
    headers=['Archivo','Hallazgo','Inicio (s)','Fin (s)','Evidencia faltante','Ubicación',
             'Modelo solicitado','Ejecución','Atribuir emisor','Dictamen conservado']
    sheet.append(headers)
    for item in items:
        for row in plan_for_item(item):
            sheet.append([row['file_name'],row['finding_code'],row['start'],row['end'],
                row['missing_evidence'],row['location_basis'],row['required_model'],row['execution'],
                'SI'if row['speaker_assignment_required']else'NO',row['classification_preserved']])
            for cell in sheet[sheet.max_row]:
                if isinstance(cell.value,str):cell.data_type='s'
    return sheet
