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
 'CONTEXT_AUDIO_RISK':('TRATO','Escuchar el intervalo indicado de la relectura local; confirmar expresión y hablante.'),
 'MISTREATMENT_REPORT':('TRATO','Confirmar que la queja describe la atención de una llamada.'),
 'WAIT_WITHOUT_RESUMPTION':('ESPERA','Cotejar el intervalo de 65 segundos; los huecos ASR no prueban silencio acústico.'),
 'NEGOTIATION_INVALID_OR_UNCERTAIN':('NEGOCIACION','Verificar los importes, fechas y aceptación indicados en el motivo.'),
 'NO_COLLECTION_ATTEMPT':('GESTION','Confirmar si hubo una solicitud u oferta de pago al titular.'),
 'RECEIPT_UNCERTAIN':('COMPROBANTE','Cotejar la petición del comprobante y distinguirla de su envío anterior.'),
 'SHORT_DURATION':('DURACION','Verificar la duración y resolver primero los riesgos de seguridad independientes.'),
 'STATUS_INVALID':('ESTATUS','Confirmar el hecho de conversación que sostiene el estatus.'),
 'STATUS_NOT_CONFIRMED':('ESTATUS','Confirmar el estatus con evidencia de conversación.'),
 'SHORT_MANAGEMENT_INCOMPLETE':('DURACION','Confirmar los elementos faltantes de gestión; una llamada menor de 60 s solo puede aprobar con gestión completa.'),
 'CONTACT_CONTRADICTION':('INTERLOCUTOR','Resolver las respuestas contradictorias sobre conocer al titular; cotejar si se habla de personas distintas.'),
 'PAYMENT_DESTINATION':('SEGURIDAD_PAGO','Confirmar a quién pertenece el destino de pago y los datos de transferencia señalados.'),
 'LIQUIDATION_UNATTRIBUTED':('NEGOCIACION','Confirmar si la liquidación es una oferta actual del gestor, una pregunta o el relato de un acuerdo anterior.'),
 'CALL_END':('CIERRE','Cotejar el final y la devolución de llamada; no atribuir abandono solo por un hueco ASR.'),
 'INVALID_DURATION':('DURACION','Comprobar la duración del audio y el límite máximo configurado.'),
 'UNCERTAIN_CONFRONTATION':('TRATO','Confirmar la expresión y quién la dice; el texto por sí solo no demuestra el tono.'),
 'RECADO_CONFIRMATION':('RECADO','Comprobar que la confirmación guardada corresponde al mismo audio, texto y contexto de cuenta.'),
 'FAMILY_CONFIRMATION':('INTERLOCUTOR','Comprobar el parentesco en el mismo audio y contexto; no trasladar confirmaciones entre llamadas.'),
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
   if isinstance(x.get('evidence'),str) and x['evidence']:
    result.append({'text':x['evidence'],'start':x.get('start'),'end':x.get('end'),'speaker_role':x.get('speaker_role'),'method':x.get('method')})
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
 if not non_status:
  # Ambos códigos describen el mismo estatus: mostrar primero el motivo
  # específico y conservar el genérico como dependencia, no otra revisión.
  findings.sort(key=lambda f:f['code']=='STATUS_NOT_CONFIRMED')
 result=[];seen=set()
 for f in findings:
  code=f['code']
  if code in{'STATUS_INVALID','STATUS_NOT_CONFIRMED'}and(non_status or 'STATUS_INVALID'in seen):continue
  seen.add(code);domain,action=ACTIONS.get(code,('EVIDENCIA','Verificar el motivo y el campo de evidencia señalado.'))
  field=FIELDS.get(code,f.get('source_field')or'');data=metadata.get(field,classification.get(field,{}))
  evidence=_evidence(data)
  if not evidence and code in {'UNIDENTIFIED_CONTACT','STATUS_INVALID','STATUS_NOT_CONFIRMED'}:
   raw=item.get('result')or{}
   segments=raw.get('segmentos')or[]
   selected=segments[:4] if code=='UNIDENTIFIED_CONTACT' else segments[-4:]
   for segment in selected:
    if not isinstance(segment,dict):continue
    fragment=segment.get('text')or segment.get('texto')
    if fragment:evidence.append({'text':fragment,'start':segment.get('start',segment.get('inicio')),
     'end':segment.get('end',segment.get('fin')),'speaker_role':segment.get('speaker_role')or'NO DETERMINADO',
     'method':'CONTEXTO_ASR_PARA_COTEJO_NO_CONFIRMACION_DE_VOZ'})
   if not evidence and raw.get('texto'):
    evidence=[{'text':raw['texto'][:1000] if code=='UNIDENTIFIED_CONTACT' else raw['texto'][-1000:],
               'start':None,'end':None,'speaker_role':'NO DETERMINADO','method':'CONTEXTO_ASR_SIN_TIEMPOS'}]
  if not evidence:
   # Una falta de extracción no produce una cita probatoria. Mostrar el
   # contexto original permite cotejar el motivo, sin inventar voz o tiempos.
   transcript=str((item.get('result')or{}).get('texto')or'')
   if transcript:
    evidence=[{'text':transcript[:12000],'start':None,'end':None,'speaker_role':'NO DETERMINADO',
      'method':'CONTEXTO_ASR_COMPLETO_PARA_COTEJO'if len(transcript)<=12000 else'CONTEXTO_ASR_TRUNCADO_A_12000_PARA_COTEJO'}]
  result.append({'code':code,'domain':domain,'reason':' | '.join(f.get('reasons')or[]),'action':action,
    'source_field':field,'evidence':evidence,'dependent_status_codes':[v['code']for v in findings if v['code']in{'STATUS_INVALID','STATUS_NOT_CONFIRMED'}]})
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
