"""Recepción enlazada a oferta de contacto, preparación y dictado real.

No deduce recepción de agradecimientos ni completa teléfonos. La recepción,
el contenido y el contacto completo siguen siendo hechos independientes.
"""
import re
from app.services.conversation_evidence import normalize,_role_at,sentence_evidence

QUOTE=re.compile(r'\bno (?:le )?$|\b(?:dice que|dijo que|diga que|repita que|por ejemplo|supongamos)\b[^.!?]{0,45}$')


def exchange_receipts(text,segments=()):
 source=normalize(text);found=[]
 # Una respuesta de preparación debe estar entre una oferta de contacto para
 # el ausente y el comienzo efectivo del dictado. No basta «tome nota».
 offers=list(re.finditer(r'\b(?:le )?(?:puedo|podria|podre|pudiera) dejar(?:le|lo)? (?:un |el )?numero\b[^?!]{0,180}',source))
 ready=re.compile(r'\b(?P<answer>a ver[, ]+(?:diga(?:me|nme)|¿?cual (?:es )?(?:el )?numero)|(?:¿?cual (?:es )?(?:el )?numero)|(?:¿?que numero es))\b')
 for offer in offers:
  if QUOTE.search(source[max(0,offer.start()-70):offer.start()]):continue
  if not re.search(r'\b(?:recado|mensaje|se comunique|se pudiera comunicar|nos contacte|nos contactara|se ponga en contacto|se lo pueda compartir)\b',source[max(0,offer.start()-250):offer.end()+250]):continue
  tail=source[offer.start():min(len(source),offer.end()+400)]
  for answer in ready.finditer(tail):
   pos=offer.start()+answer.start('answer')
   if pos<offer.end()-len(offer.group())+15 or _role_at(text,segments,pos)in{'GESTOR','TITULAR'}:continue
   after=source[offer.start()+answer.end():offer.start()+answer.end()+150]
   if not re.search(r'\b(?:numero (?:es|seria)|es (?:el )?\d{2}|\d{2}[,. ])',after):continue
   found.append({'text':source[offer.start():offer.start()+answer.end()], 'position':pos,
    'method':'PREPARA_RECEPCION_ENTRE_OFERTA_Y_DICTADO','speaker_role':_role_at(text,segments,pos),
    'human_verified':False,'contact_digits_verified':False})
 # Una promesa personal de avisar al ausente es recepción, aunque no repita
 # el sustantivo «recado». Se exige contacto completo y retorno previo.
 from app.services.message_dialogue_evidence import callback_available
 if callback_available(text,segments):
  cursor=0
  for unit in sentence_evidence(text,segments):
   value=normalize(unit['text']);at=source.find(value,cursor)
   if at<0:continue
   cursor=at+len(value)
   if unit['speaker_role']in{'GESTOR','TITULAR'}:continue
   if not re.fullmatch(r'(?:(?:si|ok|bueno|muy bien|vamos bien)[, ]+){0,3}(?:ya|yo) le (?:digo|aviso|comento)[.!]?',value):continue
   if not re.search(r'\b(?:recado|mensaje|se comunique|se ponga en contacto|le indique|indiquenle)\b',source[max(0,at-1200):at]):continue
   found.append(dict(unit,position=at,method='CONFIRMA_AVISO_TRAS_CONTACTO_Y_MENSAJE',human_verified=False,contact_digits_verified=False))
 return found


def polite_return_request(text,segments=()):
 """Petición cortés al ausente, con contacto y oferta de dejarlo ya presentes."""
 source=normalize(text);found=[]
 for m in re.finditer(r'\bsi se pudiera comunicar (?:conmigo|con nosotros)[, ]+por favor\b',source):
  if _role_at(text,segments,m.start())in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
  before=source[max(0,m.start()-900):m.start()]
  if not re.search(r'\b(?:le puedo dejar un numero|le (?:dejo|voy a dejar) (?:un|el) numero|recado|mensaje)\b',before):continue
  if QUOTE.search(before[-80:]):continue
  found.append({'text':m.group(),'position':m.start(),'method':'PETICION_CORTES_DE_RETORNO_AL_AUSENTE','human_verified':False})
 return found
