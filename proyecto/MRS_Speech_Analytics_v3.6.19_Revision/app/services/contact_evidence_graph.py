"""Solicitud nominal y respuesta personal, con ámbito de gestión y evidencia.

No identifica por Excel, sí aislado, nombre del receptor de un recado ni ID
acústico. El objeto de una respuesta puede ser pago pasado o futuro; reconocer
interlocución no acredita cobertura, importe ni compromiso de pago.
"""
import re
from app.services.conversation_evidence import normalize,sentence_evidence,_role_at
from app.services.contextual_identity_evidence import BAD_IDENTITY,valid_nominal_request,proxy_account_evidence,own_marker_is_instruction

REQUEST=(r'(?:me (?:puede|puedes|podria|podre|pueden|puedo) (?:a )?comunicar (?:(?:por|de|el) favor )?con|'
 r'(?<=¿)con|con(?= (?:el senor|la senora|la senorita) )|(?:me )?puedo poder comunicar (?:por favor )?con|me comunica con|me comunico con|(?:me )?estoy comunicando con|nos estamos comunicando con|tengo (?:el )?(?:gusto|uso) con|tengo gusto con|hablo con|busco (?:a |al |a la )?|'
 r'estoy buscando a|estoy buscando al|(?:podra|podria|puede) comunicar (?:por favor )?con|se encontr(?:ara|aba|a)|encuentro|encuentra|encuentre|(?:buenos dias|buen dia|buenas tardes|buena tarde) con|es usted|usted es|ustedes)')
VARIANT=r'(?:tengo el busto con|te gusta con)'
NAMED_GREETING=r'(?:buenos dias|buen dia|buenas tardes|buena tarde)(?= (?:senorita|senora|senor) )'
BAD_NAME=re.compile(r'\b(?:que|como|donde|cuando|cuanto|si|no|usted|ustedes|puede|acudir|directamente|'
 r'habla|hablamos|llamada|credito|numero|referencia|contacto|cuenta|tarjeta|pago|banco|juridico|'
 r'corporativo|consulta|deudor|titular|persona|aplicacion|es|esta|conoce|tiene|tiempo)\b')
# No deducir que habla un tercero por palabras sueltas como "recado",
# "mensajito" o porque el gestor ofrece dejar un mensaje. El parentesco,
# intermediación y recepción se acreditan por rutas independientes.
RELAY=re.compile(r'\b(?:por otra persona|a otra persona|no soy la persona|'
 r'(?:dejo|registro|proporciono) (?:su |mi |este |el )?numero (?:como |de )referencia|'
 r'no (?:esta|se encuentra)(?: en este momento)?[?.]|'
 r'(?:conoce|conocer|conozca|ubica) a (?:esa|esta|la|el|al))\b')
QUOTE=re.compile(r'\b(?:dice que|dijo que|diga que|repita que|usted dijo|usted dice|el cliente dice|'
 r'si fuera|si tuviera|por ejemplo|supongamos|no es cierto que)\b[^.!?]{0,100}$')


def nominal_requests(text,segments=()):
 source=normalize(text);view=source.replace(',',' ')
 prefix=(REQUEST+'|'+VARIANT+'|'+NAMED_GREETING).replace(' ',r'\s+')
 for m in re.finditer(r'\b(?P<prefix>'+prefix+r')\s+(?P<person>[^.!?]{2,100}?)(?:[.!?]|(?=\s+(?:gracias|mucho gusto|me presento|me comunico|le hablo|mi nombre es)\b)|$)',view[:650]):
  person=re.sub(r'\bpor\s+favor\b','',m['person']);person=re.sub(r'^(?:(?:el|la) )?(?:senorita|senora|senor|caballero)\b\s*','',person).strip()
  if re.fullmatch(r'buenos dias|buen dia|buenas tardes|buena tarde',m['prefix']):
   if len(person.split())<2 or m.start()>300:continue
  if not person or BAD_IDENTITY.search(person)or BAD_NAME.search(person)or re.search(r'\d',person):continue
  if not valid_nominal_request(view,m.start(),person)or QUOTE.search(source[max(0,m.start()-100):m.start()]):continue
  if _role_at(text,segments,m.start())in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
  yield {'person':person,'start':m.start(),'end':m.end(),'text':source[m.start():m.end()],
         'asr_variant':bool(re.fullmatch(VARIANT.replace(' ',r'\s+'),m['prefix']))}


def personal_account_questions(text,segments=()):
 """Preguntar por MI cuenta acredita autorreferencia, nunca un acuerdo."""
 source=normalize(text);found=[]
 for m in re.finditer(r'(?P<question>[^.!?]{1,240})\?',source):
  question=m['question'].strip(' ¿')
  if not re.search(r'\bmi (?:tarjeta|cuenta|pago|saldo|estado de cuenta)\b',question):continue
  pos=source.find(question,m.start())
  if re.match(r'(?:gestor|tercero)\s*:',question)or _role_at(text,segments,pos)in{'GESTOR','TERCERO'}:continue
  if re.search(r'\b(?:diga|repita|usted dice|usted dijo|dice que|dijo que|por ejemplo|supongamos|si tuviera|si fuera)\b',question):continue
  found.append({'text':m.group(),'position':pos,'speaker_role':_role_at(text,segments,pos),
                'method':'PREGUNTA_SOBRE_CUENTA_PROPIA_NO_COMPROMISO','human_verified':False})
 return found


def nonholder_context(text,segments=()):
 source=normalize(text)
 if proxy_account_evidence(text,segments)or RELAY.search(source):return True
 from app.services.contact_dialogue_resolution import declared_intermediary
 from app.services.context_rules import unknown_debtor_statement
 if declared_intermediary(text,segments)['confirmed']or unknown_debtor_statement(text,segments):return True
 from app.services.contextual_identity_evidence import COUNTER
 for u in sentence_evidence(text,segments):
  s=normalize(u['text'])
  if u['speaker_role']=='GESTOR'or'?'in s or'¿'in s:continue
  for m in COUNTER.finditer(s):
   if QUOTE.search(s[:m.start()]):continue
   if m.group()=='esta trabajando'and not re.search(r'\b(?:el|ella|mi|su|no esta|no se encuentra)\b',s[:m.start()]):continue
   return True
 return False


def own_payment_responses(text,segments=()):
 source=normalize(text);found=[]
 question=(r'(?:ya (?:pudo|puedo|puede|ha podido|realizo|hizo)|(?:ya )?(?:podemos|podriamos|podiamos|puedo|podria) contar con|'
  r'(?:puede|podria|podrias|puedes) (?:realizar|efectuar|hacer|confirmar)|'
  r'(?:ya )?(?:tendra(?:s)?|tiene) (?:usted )?|cuando (?:puede|podria)|que cantidad (?:puede|podria))'
  r'[^?!]{0,140}\b(?:pago|pao|pagar|deposito|depositar|abono)\b[^?!]{0,90}')
 personal=re.compile(r'\b(?:(?:aun |todavia )?no (?:lo |le )?he podido|'
  r'(?:yo )?no (?:he podido|puedo|podria|pude) (?:realizarlo|hacerlo|pagar|depositar|abonar)|'
  r'(?:yo )?(?:me quede|estoy|ando|he estado|ya consegui|no tengo|no cuento|no dispongo|no traigo)|'
  r'ya (?:lo hice|lo realice|hice el pago|realice el pago)|yo (?:les |le )?(?:propuse|proponia|pago|pagaba|deposito|abono))\b')
 for m in re.finditer(r'\b(?P<question>'+question+r')\?\s*(?P<answer>[^?]{1,650})',source):
  q,a=m['question'],m['answer'];pos=m.start('answer')
  if _role_at(text,segments,pos)in{'GESTOR','TERCERO'}:continue
  if re.search(r'\b(?:comprobante|ticket|recibo|whatsapp|numero|telefono|folio|acta|sabe si|'
   r'el senor|la senora|el titular|la titular|su (?:esposo|esposa|hijo|hija|hermano|hermana))\b',q):continue
  qprefix=source[max(0,m.start()-100):m.start()]
  if QUOTE.search(qprefix)or QUOTE.search(a):continue
  if re.search(r'\b(?:sabe si|el senor|la senora|el titular|la titular)\b[^.!?¿]{0,70}$',qprefix):continue
  p=personal.search(a)
  if not p or QUOTE.search(a[:p.start()]):continue
  if _role_at(text,segments,pos+p.start())in{'GESTOR','TERCERO'}:continue
  if re.match(r'\s+(?:revisando|validando|solicitando|marcando|ofreciendo|llamando|contactando|en espera|hablando)\b',a[p.end():]):continue
  if re.match(r'\s+(?:su|sus)\b',a[p.end():]):continue
  if re.search(r'\b(?:reporte|comprobante|ticket|registro|sistema)\b',a[p.end():])and not re.search(r'\b(?:mi|yo|me estan|me siguen)\b',a):continue
  if re.search(r'\b(?:si fuera|si tuviera|si pudiera|cuando pueda|para que)\b',a[:p.start()]):continue
  if re.fullmatch(r'(?:yo )?(?:me quede|estoy|ando|he estado|ya consegui|no tengo|no cuento|no dispongo|no traigo)',p.group()):
   if not re.search(r'\b(?:trabajo|trabajando|enferm[oa]|hospital|operacion|dinero|cantidad|quincena|pagan|desemple[oa]|pagar|pagos?|depositar|abonar|salario|sueldo|liquidez)\b',a):continue
  found.append({'text':m.group(),'question':q,'answer':a,'position':pos,'speaker_role':_role_at(text,segments,pos),
                'method':'RESPUESTA_PERSONAL_A_PREGUNTA_DE_SU_PAGO','human_verified':False})
 return found


def contextual_contact(text,segments=()):
 none={'confirmed':False,'method':'SIN_SECUENCIA_PERSONAL_COMPLETA','evidence':''}
 if nonholder_context(text,segments):return none
 requests=list(nominal_requests(text,segments))
 if not requests:return none
 responses=own_payment_responses(text,segments)+personal_account_questions(text,segments)
 from app.services.payment_intent_frames import payment_frames
 for frame in payment_frames(text,segments):
  if frame['own_financial_response']:
   responses.append({'text':frame['evidence'],'position':frame['position'],'speaker_role':frame['speaker_role'],
     'method':'RESPUESTA_PERSONAL_EN_OBJETO_DE_PAGO','human_verified':False})
 from app.services.contextual_identity_evidence import OWN_ACCOUNT
 source=normalize(text);cursor=0
 from app.services.declarative_evidence import declarative_units
 for u in declarative_units(text,segments):
  value=normalize(u['text']);at=source.find(value,cursor)
  if at<0:continue
  cursor=at+len(value)
  if u['speaker_role']in{'GESTOR','TERCERO'}or'?'in value:continue
  own=OWN_ACCOUNT.search(value)
  if not own or QUOTE.search(value[:own.start()]):continue
  if own_marker_is_instruction(u['text'],own):continue
  if re.search(r'\b(?:si tuviera|si yo tuviera|si pudiera|diga|repita)\b',value[:own.start()]):continue
  responses.append({'text':u['text'],'position':at+own.start(),'speaker_role':u['speaker_role'],
                    'method':'AUTORREFERENCIA_PERSONAL','human_verified':False})
 for request in requests:
  for response in responses:
   if response['position']<=request['end']:continue
   if request['asr_variant']and not re.search(r'\b(?:mrs|mrc|mrss|m\.r\.s|mirs)\b',source):continue
   return {'confirmed':True,'method':'SOLICITUD_NOMINAL_Y_RESPUESTA_PERSONAL_EN_LA_MISMA_GESTION',
    'evidence':request['text']+' / '+response['text'],'request':request,'personal_response':response,
    'speaker_role':response['speaker_role'],'human_verified':False,'acoustic_voice_identified':False,
    'policy_source':'CRITERIO_USUARIO_CONTEXTO_COMPLETO'}
 return none


def unresolved_contact_details(text,segments=()):
 """Explicar qué enlace falta; diagnóstico, nunca autorización de identidad."""
 requests=list(nominal_requests(text,segments))
 responses=own_payment_responses(text,segments)+personal_account_questions(text,segments)
 from app.services.payment_intent_frames import payment_frames
 responses += [{'text':f['evidence'],'position':f['position'],'method':f['method']}
               for f in payment_frames(text,segments)if f['own_financial_response']]
 from app.services.contextual_identity_evidence import OWN_ACCOUNT
 from app.services.declarative_evidence import declarative_units
 for unit in declarative_units(text,segments):
  value=normalize(unit['text'])
  if unit['speaker_role']in{'GESTOR','TERCERO'}or'?'in value:continue
  own=OWN_ACCOUNT.search(value)
  if own and own_marker_is_instruction(unit['text'],own):continue
  if own and not QUOTE.search(value[:own.start()])and not re.search(r'\b(?:si tuviera|si pudiera|diga|repita)\b',value[:own.start()]):
   responses.append({'text':unit['text'],'method':'AUTORREFERENCIA_PERSONAL','human_verified':False})
 intermediary=nonholder_context(text,segments)
 missing=[]
 if not requests:
  missing.append('El ASR no conserva una búsqueda nominal con nombre legible y ámbito de identificación válidos.')
 if not responses:
  missing.append('No se enlaza la búsqueda con una respuesta personal sobre la cuenta o el pago; un sí, saludo o dato del Excel no basta.')
 if intermediary:
  missing.append('Hay señales de intermediación o de otra persona; falta confirmar quién continúa hablando y a quién pertenece la cuenta.')
 if not missing:
  missing.append('La búsqueda nominal y la respuesta personal no quedaron enlazadas en una secuencia válida de la misma gestión.')
 return {'reason':' '.join(missing),'missing_elements':missing,
         'nominal_request_evidence':requests[:3],'personal_response_evidence':responses[:3],
         'intermediation_present':intermediary,'human_verified':False,
         'method':'DIAGNOSTICO_DE_ENLACES_DE_IDENTIDAD_NO_CONFIRMACION'}
