"""Recepción local de dictado; no reconstruye dígitos ni atribuye voz acústica."""
import re
from app.services.conversation_evidence import normalize,_role_at
from app.services.payment_reference_validation import callback_numbers,TOKEN,_digits


def callback_acknowledgements(text,segments=()):
    source=normalize(text);found=[]
    for phone in callback_numbers(text):
        after=source[phone['text_end']:phone['text_end']+80]
        m=re.match(r'[,.?!¿ ]*(?P<answer>si|asi es|ok|esta bien|correcto)\b',after)
        if not m:continue
        pos=phone['text_end']+m.start('answer')
        if _role_at(text,segments,pos)in{'GESTOR','TITULAR'}:continue
        if re.match(r'[,. ]*(?:pero no|no puedo|no quiero|si tengo tiempo)\b',after[m.end():]):continue
        found.append({'text':phone['text']+' '+m.group(),'phrase':m['answer'],'method':'ACUSE_LOCAL_TRAS_DICTADO_DE_CONTACTO',
            'speaker_role':_role_at(text,segments,pos),'start':None,'end':None,'human_verified':False,'contact_digits_verified':False})
    return found


def expanded_return_instruction(text,segments=()):
    source=normalize(text);found=[]
    pattern=re.compile(r'\b(?:que (?:se (?:va a|pueda|puede|debe(?: de)?) comunicar|pueda (?:regalar|regresar) (?:una? |la )llamada)|'
                       r'(?:a |en |ahi en )?(?:ese|este) numero (?:se (?:va a|debe(?: de)?|puede|tiene que) comunicar)|'
                       r'para que (?:se ponga|se pueda poner) (?:en )?contacto)\b')
    for m in pattern.finditer(source):
        if _role_at(text,segments,m.start())in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        before=source[max(0,m.start()-60):m.start()]
        if re.search(r'\b(?:no|dice que|dijo que|diga que|repita que|por ejemplo|si)\s*$',before):continue
        found.append({'text':m.group(),'method':'INSTRUCCION_EXPLICITA_DE_RETORNO','human_verified':False})
    return found
