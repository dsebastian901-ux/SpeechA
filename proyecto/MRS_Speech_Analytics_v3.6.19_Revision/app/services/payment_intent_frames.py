"""Pregunta, objeto y respuesta de pago con ámbito y posiciones de origen.

No atribuye voces acústicas ni usa el Excel. Una fecha de corte, un número de
WhatsApp y un pago histórico no equivalen a aceptar una promesa nueva.
"""
import re
from app.services.conversation_evidence import normalize,_role_at
from app.services.reported_payment_amounts import NUMBER,money_value
from app.services.conversation_cache import current_cache

DAY_WORDS=r'(?:treinta y uno|veintinueve|veintiocho|veintisiete|veintiseis|veinticinco|veinticuatro|veintitres|veintidos|veintiuno|veinte|diecinueve|dieciocho|diecisiete|dieciseis|quince|catorce|trece|doce|once|diez|nueve|ocho|siete|seis|cinco|cuatro|tres|dos|uno|treinta)'
DATE=re.compile(r'\b(?:hoy|manana|ahorita|ahora(?: mismo)?|enseguida|en seguida|inmediatamente|'
 r'(?:el |este |proximo )?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)|'
 r'(?:el )?(?:dia )?\d{1,2}(?: de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre))?)\b')
OTHER=re.compile(r'\b(?:whatsapp|telefono|numero|comprobante|ticket|recibo|folio|correo|anotar|apuntar|'
 r'visita|diligencia|domicilio|cita|doctor|consulta medica|estado de cuenta|estados de cuenta)\b')
PAYMENT=re.compile(r'\b(?:pago|pagar|pagando|depositar|deposito|abonar|abonando|abono|convenio|pesos|cantidad|monto)\b')
PAST=re.compile(r'\b(?:ayer|antier|anteayer|pasado|anterior|realizado|efectuado|reportado|ya (?:lo |les )?'
 r'(?:pague|pago|hice|realice|deposit[eoa])|(?:que dia|que fecha|cuando) (?:lo )?(?:hizo|realizo|pago|deposito))\b')
QUOTE=re.compile(r'\b(?:dice que|dijo que|diga que|usted dice|usted dijo|repita|por ejemplo|supongamos)\b[^.!?]{0,100}$')
CONDITION=re.compile(r'\b(?:creo|a lo mejor|tal vez|quizas|posiblemente|lo mas (?:seguro|probable)|'
 r'si (?:puedo|consigo|alcanzo|me (?:alcanza|dan|prestan|pagan|depositan))|no se (?:si|cuando|cuanto)|'
 r'voy a (?:ver|intentar|tratar)|no (?:puedo|podria) (?:asegurar|confirmar|prometer)|'
 r'(?:en estos dias|cuando (?:yo )?pueda|ojala))\b')
NEGATIVE=re.compile(r'^(?:(?:bueno|pues|ah|este|mire|mira|si)[, ]+){0,2}'
 r'(?:no(?:[,.! ]|$)|por el momento (?:todavia )?no\b|ahorita (?:todavia )?no\b|'
 r'(?:aun|todavia) no\b|(?:ya )?no me es posible\b|no es posible\b)')
ACTION=re.compile(r'\b(?:(?:yo )?(?:hago|hare|realizo|realizare|aplico|aplicare) (?:el |mi |un )?(?:pago|deposito|abono)|'
 r'(?:yo )?(?:lo hago|lo hare|lo realizo|lo realizare|lo aplico)|'
 r'(?:yo )?(?:voy a|me comprometo a) (?:realizar|hacer|aplicar|pagar|depositar|abonar)|'
 r'(?:yo )?(?:pagare|depositare|abonare))\b')
OWN=re.compile(r'\b(?:yo|mi (?:tarjeta|cuenta|pago)|mis pagos|me (?:pagan|quede|estan cobrando)|'
 r'(?:no |aun no |todavia no )?(?:lo |le )?he (?:podido|realizado)|'
 r'no (?:tengo|cuento con|dispongo de|pude|puedo)|estoy (?:sin trabajo|en el hospital|enferm[oa])|'
 r'(?:ya )?(?:pague|hice el pago|realice el pago)|(?:yo )?puedo (?:pagar|realizar|depositar|abonar)|lo puedo dejar|lo he realizado)\b')
YES=re.compile(r'^(?:(?:ah|bueno|ok|aja|este|eh|pues)[, ]+){0,2}(?:si|asi es|correcto|de acuerdo|esta (?:muy )?bien|claro)(?=[,.! ]|$)')


def negative_payment_question(question):
 return bool(re.search(r'\bno (?:(?:le|lo|la|les|nos|me|usted|se) ){0,2}'
     r'(?:pued\w*|pod\w*|cuent\w*|cont\w*|confirm\w*|aplic\w*|realiz\w*|tendr\w*|va a|'
     r'logr\w*|efectu\w*|pag\w*|deposit\w*|abon\w*|hace|hara\w*|haria\w*|est[ae]\w*)\b',normalize(question)))


def ambiguous_negative_reply(question, answer):
 """La repetición o cortesía no desambigua un NO a una pregunta negativa.

 «No, no tengo dinero» sí añade una explicación propia; «no, señora, no»
 conserva las dos interpretaciones posibles y no crea un estatus de pago.
 """
 return bool(negative_payment_question(question) and re.fullmatch(
     r'no(?:[\s,]+(?:no|senorita|senora|senor|caballero|joven|gracias))*[.! ]*',
     normalize(answer)))


def payment_frames(text,segments=()):
 cache=current_cache();key=(str(text or ''),id(segments))
 saved=cache.setdefault('payment_frames',{}).get(key)if cache is not None else None
 if saved is not None:return [dict(r)for r in saved]
 source=normalize(text);found=[];previous=0
 for close in re.finditer(r'\?',source):
  opening=source.rfind('¿',previous,close.start())
  if opening<0:
   boundaries=list(re.finditer(r'\.(?=\s|$)|[!?]',source[previous:close.start()]))
   opening=previous+(boundaries[-1].end()if boundaries else 0)
  previous=close.end();q=source[opening:close.start()].strip('¿ ')
  if not q or len(q)>310:continue
  qstart=source.find(q,opening);prefix=source[max(0,qstart-250):qstart]
  if OTHER.search(q)or QUOTE.search(prefix[-100:])or _role_at(text,segments,qstart)in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
  # La pregunta del cliente sobre MI pago o CUANTO TENGO QUE DAR no es
  # una oferta del gestor. No convertir su respuesta en decisión del cliente.
  if re.search(r'\b(?:mi (?:tarjeta|cuenta|pago|saldo)|mis pagos|yo|tengo que|debo (?:dar|pagar)|puedo (?:pagar|depositar|abonar)|sabe si|su (?:esposo|esposa|hijo|hija|mama|papa))\b',q):continue
  explicit=bool(PAYMENT.search(q));local=prefix[-220:]
  topics=list(re.finditer(r'\b(?:pago|pagar|deposito|pesos|convenio|cantidad|monto|whatsapp|telefono|numero|comprobante|ticket|recibo|folio|visita|domicilio|cita)\b',local))
  payment_context=bool(topics and PAYMENT.fullmatch(topics[-1].group()))
  date_question=bool(re.search(r'\b(?:que dia|que fecha|en que fecha|para cuando|cuando)\b',q))
  amount_question=bool(re.search(r'\b(?:que monto|de que monto|de cuanto|que cantidad|cuanto(?:s)?|(?:indicar|indica|confirmar|confirma) (?:el |su )?monto)\b',q))
  if not explicit and not((date_question or amount_question)and payment_context):continue
  if re.search(r'\b(?:le dan|le pagan|recibe|recibira|cobran|le depositan)\b[^?]{0,70}\b(?:aguinaldo|sueldo|salario|quincena|pension)\b',q):continue
  if re.search(r'\b(?:corte|fecha limite|fecha de vencimiento|vencio|vencera|vence|interes|restante del saldo)\b',q):continue
  past_question=bool(PAST.search(q)or re.search(
      r'\b(?:cuando|que dia|que fecha|en que fecha) (?:(?:ya|lo|usted) )?(?:fue|realizo|hizo|aplico|cubrio|efectuo|deposito)\b|'
      r'\b(?:realizo|hizo|aplico|cubrio|efectuo|deposito) (?:lo que es )?(?:(?:su|el|un|algun) )?(?:pago|deposito|abono)\b|'
      r'\b(?:ya (?:pudo|puedo|hizo|realizo|ha realizado|ha podido)|ha|habia) (?:efectuar|realizar|hacer|hecho|realizado|pagado|cubierto|depositado)\b',q))
  if past_question:kind='HISTORY'
  elif amount_question:kind='AMOUNT'
  elif date_question:kind='DATE'
  elif explicit:kind='PAYMENT'
  else:continue
  if kind=='PAYMENT'and not (DATE.search(q)or re.search(r'\b(?:confirm\w*|cuent\w*|conta\w*|puede|podria|tendra|tiene|acepta|posible|realiza|aplica|efectua)\b',q)):continue
  tail=source[close.end():close.end()+230]
  label=re.match(r'\s*(?:(?:titular|cliente|interlocutor|gestor|tercero|familiar)\s*:\s*)?',tail)
  pos=close.end()+label.end();tail=source[pos:pos+220]
  boundary=re.search(r'\.(?=\s|$)|[!?]|\b(?:gestor|titular|tercero|cliente|interlocutor)\s*:',tail)
  answer=tail[:boundary.start()if boundary else len(tail)].strip()
  if not answer or tail.startswith('¿')or(boundary and boundary.group()=='?'):continue
  role=_role_at(text,segments,pos)
  if role in{'GESTOR','TERCERO'}or QUOTE.search(answer):continue
  if re.match(r'(?:mi nombre|me presento|le (?:solicito|ofrezco|requiero|comento)|el banco|se le)\b',answer):continue
  # Una confirmación de método no acredita pago ni autorreferencia financiera.
  if re.search(r'\b(?:reporte|registro|sistema|validar|validando|anexar|ingresar)\b',answer)and not re.search(r'\b(?:mi (?:tarjeta|cuenta)|yo pague|no tengo (?:dinero|trabajo|la cantidad)|para pagar)\b',answer):continue
  if re.search(r'\b(?:su |el )comprobante\b',answer)and not ACTION.search(answer):continue
  if OTHER.search(answer)and not(ACTION.search(answer)or OWN.search(answer)):continue
  history=kind=='HISTORY'or bool(re.search(r'\b(?:ya (?:lo |les )?pague|ya (?:hice|realice)|pague (?:ayer|antier))\b',answer))
  condition=bool(CONDITION.search(answer));declined=bool(NEGATIVE.search(answer)or re.search(
      r'\bpero (?:no (?:puedo|podria|tengo (?:dinero|la cantidad)|cuento con (?:dinero|la cantidad))|no me alcanza)\b',answer))
  negative_question=negative_payment_question(q)
  # «¿No aplica el pago aún? No» puede negar la pregunta o confirmar que
  # no se ha pagado. Sin aclaración personal no acredita una negativa nueva.
  if ambiguous_negative_reply(q,answer):
   declined=False
  action=ACTION.search(answer);own=bool(OWN.search(answer)or action)
  dated_reply=bool(re.match(r'(?:(?:seria|para|hasta|va a ser|lo estaria realizando|lo estaria haciendo) )?(?:el (?:dia(?: de)? )?)?'
      r'(?:hoy|manana|ahorita|lunes|martes|miercoles|jueves|viernes|sabado|domingo|\d{1,2})(?:\b)',answer))
  # Un día en respuesta a CUANDO es un plan propio. Una hora o un importe
  # aislado en otro tipo de pregunta no se transforma en fecha.
  day_match=re.match(r'(?:(?:seria|para|hasta) )?(?:el (?:dia )?|dia )(?P<day>\d{1,2}|'+DAY_WORDS+r')\b',answer)
  day_value=money_value(day_match['day'])if day_match else None
  if day_value is not None and (not 1<=day_value<=31 or re.match(r'\s+(?:pesos|mil|horas)\b',answer[day_match.end():])):day_value=None
  substantive_date=kind=='DATE'and (dated_reply or day_value is not None)and not re.match(r'\d{1,2}(?:[.,]\d+)? pesos\b',answer)
  if re.search(r'\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b',answer):day_value=None
  if substantive_date:own=True
  if history:
   accepted=False;conditional=False;declined=False
  else:
   conditional=condition or bool(kind=='DATE'and re.search(r'\b(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo|\d{1,2}) o (?:el )?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo|\d{1,2})\b',answer))
   accepted=not(declined or conditional)and bool(action or (substantive_date and not negative_question))
   direct_confirm=bool(re.search(r'\b(?:confirm\w*|cuento|contamos|contariamos|podemos contar|podemos contemplar (?:su |el )?pago|seria (?:un |el |su )?pago|puede (?:realizar|aplicar)|lo (?:realizaria|estaria realizando|va a realizar))\b',q))
   if direct_confirm and not negative_question and YES.match(answer)and not(declined or conditional):accepted=True
   if kind=='AMOUNT'and re.search(r'\b(?:confirmaria|va a (?:realizar|pagar)|podemos contemplar)\b',q)and re.search(NUMBER,answer)and not(declined or conditional):accepted=True
   paired_terms=bool(kind=='AMOUNT'and re.search(r'\bfecha\b',q)and explicit
       and re.search(r'\b(?:hoy|manana|(?:el )?dia \d{1,2}|\d{1,2} de [a-z]+)\b',answer)
       and re.search(r'(?:^(?:de |por )?'+NUMBER+r'\b|\b(?:monto|cantidad) (?:es|seria|de|por) '+NUMBER+r'\b)',answer))
   if paired_terms and not(negative_question or declined or conditional):accepted=True;own=True
  meaningful=bool(accepted or declined or conditional or own)
  if not meaningful:continue
  evidence=source[qstart:pos+len(answer)]
  date_evidence=evidence
  if accepted and ((action and re.search(r'\b(?:ahorita|ahora|enseguida|en seguida|inmediatamente)\b',answer))or(kind=='DATE'and re.match(r'hoy\b',answer))):
   # Interpretación temporal explícita; no altera palabras ni tiempos ASR.
   immediate=True
  else:immediate=False
  found.append({'kind':kind,'position':pos,'end':pos+len(answer),'question':q,'question_position':qstart,'reply':answer,
   'accepted':bool(accepted),'declined':bool(declined),'conditional':bool(conditional),
   'own_financial_response':own,'history':history,'immediate':immediate,
   'evidence':evidence,'date_evidence':date_evidence,'speaker_role':role,
   'day_of_month':int(day_value)if substantive_date and day_value is not None else None,
   'day_text':day_match.group()if substantive_date and day_value is not None else '',
   'method':'OBJETO_Y_RESPUESTA_LOCAL_DE_PAGO','human_verified':False,'acoustic_voice_identified':False})
 if cache is not None:cache['payment_frames'][key]=[dict(r)for r in found]
 return found
