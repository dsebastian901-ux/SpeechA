"""Ventanas de corroboración ancladas al ASR; no ejecuta ni activa modelos."""
import math
import re

from app.services.conversation_evidence import normalize

FIELDS = {
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
                'required_model':'medium','execution':'NO_EJECUTADO',
                'speaker_assignment_required':code in{'UNIDENTIFIED_CONTACT','UNCERTAIN_DISCLOSURE','OFFENSIVE_LANGUAGE','HOME_WARNING_UNATTRIBUTED','UNCERTAIN_CONFRONTATION'},
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
