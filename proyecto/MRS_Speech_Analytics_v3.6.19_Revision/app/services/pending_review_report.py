"""Pendientes reales, con causa y evidencia; los códigos dependientes no suman llamadas."""
import json
from openpyxl.styles import Alignment

ACTIONS={
 'UNIDENTIFIED_CONTACT':('INTERLOCUTOR','Confirmar quién responde y si hubo transferencia al titular.'),
 'UNCERTAIN_DISCLOSURE':('PRIVACIDAD','Confirmar quién dijo la frase financiera y quién la recibió.'),
 'CONFIRMED_DISCLOSURE':('PRIVACIDAD','Divulgación confirmada; conservar bloqueo.'),
 'ARCO_INCOMPLETE':('ARCO','Cotejar el elemento ARCO que falta: derechos, procedimiento, correo, documentos o antigüedad.'),
 'CALLBACK_NOT_DELIVERED':('RECADO','Confirmar entrega y recepción del contacto; una oferta de dictarlo no acredita recepción.'),
 'CARD_REFERENCE':('TARJETA','Cotejar los dígitos del audio con numero_de_tarjeta; no completar desde Excel.'),
 'OFFENSIVE_LANGUAGE':('TRATO','Confirmar expresión, hablante y contexto de la ofensa.'),
 'MISTREATMENT_REPORT':('TRATO','Confirmar que la queja describe la atención de una llamada.'),
 'WAIT_WITHOUT_RESUMPTION':('ESPERA','Cotejar el intervalo de 65 segundos; los huecos ASR no prueban silencio acústico.'),
 'NEGOTIATION_INVALID_OR_UNCERTAIN':('NEGOCIACION','Verificar los importes, fechas y aceptación indicados en el motivo.'),
 'NO_COLLECTION_ATTEMPT':('GESTION','Confirmar si hubo una solicitud u oferta de pago al titular.'),
 'RECEIPT_UNCERTAIN':('COMPROBANTE','Cotejar la petición del comprobante y distinguirla de su envío anterior.'),
 'SHORT_DURATION':('DURACION','Verificar la duración y resolver primero los riesgos de seguridad independientes.'),
 'STATUS_INVALID':('ESTATUS','Confirmar el hecho de conversación que sostiene el estatus.'),
 'STATUS_NOT_CONFIRMED':('ESTATUS','Confirmar el estatus con evidencia de conversación.'),
}
FIELDS={
 'UNIDENTIFIED_CONTACT':'contact_validation','UNCERTAIN_DISCLOSURE':'privacy_validation',
 'ARCO_INCOMPLETE':'arco_validation','CALLBACK_NOT_DELIVERED':'message_delivery_validation',
 'CARD_REFERENCE':'card_validation','OFFENSIVE_LANGUAGE':'treatment_validation',
 'MISTREATMENT_REPORT':'treatment_validation','WAIT_WITHOUT_RESUMPTION':'wait_validation',
 'NEGOTIATION_INVALID_OR_UNCERTAIN':'negotiation_validation','NO_COLLECTION_ATTEMPT':'negotiation_validation',
 'RECEIPT_UNCERTAIN':'convenio_payment_validation','SHORT_DURATION':'duration_seconds',
 'STATUS_INVALID':'status_validation','STATUS_NOT_CONFIRMED':'status_validation'}


def _evidence(value):
 result=[]
 def walk(x):
  if isinstance(x,dict):
   text=x.get('text')or x.get('phrase')
   if text:
    result.append({'text':str(text),'start':x.get('start'),'end':x.get('end'),'speaker_role':x.get('speaker_role'),'method':x.get('method')})
   for k,v in x.items():
    if k not in{'text','phrase','shared_classification'}and isinstance(v,(list,dict)):walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(value)
 return result[:8]


def review_steps(item):
 classification=item.get('classification')or{};metadata=item.get('analytics_metadata')or{}
 if classification.get('clasificacion')!='REVISAR':return []
 findings=[f for f in classification.get('decision_findings',[])if f['severity']=='REVIEW']
 non_status=[f for f in findings if f['code']not in{'STATUS_INVALID','STATUS_NOT_CONFIRMED'}]
 result=[];seen=set()
 for f in findings:
  code=f['code']
  if code in{'STATUS_INVALID','STATUS_NOT_CONFIRMED'}and(non_status or 'STATUS_INVALID'in seen):continue
  seen.add(code);domain,action=ACTIONS.get(code,('EVIDENCIA','Verificar el motivo y el campo de evidencia señalado.'))
  field=FIELDS.get(code,f.get('source_field')or'');data=metadata.get(field,{})
  result.append({'code':code,'domain':domain,'reason':' | '.join(f.get('reasons')or[]),'action':action,
    'source_field':field,'evidence':_evidence(data),'dependent_status_codes':[v['code']for v in findings if v['code']in{'STATUS_INVALID','STATUS_NOT_CONFIRMED'}]})
 return result


def add_pending_review_sheet(workbook,items):
 sheet=workbook.create_sheet('REVISION_PENDIENTE')
 sheet.append(['Llamada en lote','Audio','Fecha','Tarjeta Excel','Gestor','Supervisor','Puntaje','Causa','Código','Motivo','Acción concreta','Campo de evidencia','Fragmentos y tiempos','Códigos dependientes de estatus'])
 for n,item in enumerate(items,1):
  rel=item.get('relation')or{}
  for step in review_steps(item):
   sheet.append([n,item.get('file_name',''),rel.get('fecha',''),rel.get('numero_de_tarjeta',''),rel.get('gestor',''),rel.get('supervisor',''),item.get('compliance_score'),step['domain'],step['code'],step['reason'],step['action'],step['source_field'],json.dumps(step['evidence'],ensure_ascii=False),', '.join(step['dependent_status_codes'])])
 for row in sheet.iter_rows(min_row=2):
  for c in row:
   if isinstance(c.value,str):c.data_type='s'
   c.alignment=Alignment(wrap_text=True,vertical='top')
 sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
 return sheet
