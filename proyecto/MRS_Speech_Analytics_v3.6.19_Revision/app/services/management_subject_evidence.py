"""Distinguir al receptor identificado del sujeto explícito de la gestión."""
import re
from app.services.conversation_evidence import normalize, _role_at
from app.services.declarative_evidence import is_statement

NAME=r'[a-z][a-z ,\-]{2,110}?'
HONORIFIC=r'(?:(?:el|la) )?(?:senorita|senora|senor|caballero) '
STOP={'senor','senora','senorita','caballero','el','la','de','del','con','por','favor'}


def name_words(value):
    return {w for w in re.findall(r'[a-z]+',value)if len(w)>2 and w not in STOP}


def management_subject(text,segments=()):
    source=normalize(text)
    none={'confirmed':False,'method':'SIN_CAMBIO_DE_SUJETO_DE_GESTION','evidence':''}
    openings=list(re.finditer(
        r'\b(?:me comunica con|me comunico con|me (?:puede|podria|podre) comunicar con|'
        r'tengo(?: el)? gusto con|se encuentra|buenas tardes[, ]+con|buen dia[, ]+con)\s+'
        r'(?P<person>'+NAME+r')[.?]',source[:800]))
    patterns=[
        ('LOCALIZACION_INICIAL_DE_PERSONA_DISTINTA',re.compile(
            r'\btratando de localizar (?:al|a la) (?P<person>(?:'+HONORIFIC+r')?'+NAME+r')[.?]')),
        ('REFERENCIA_DE_PERSONA_AUSENTE',re.compile(
            r'\b(?P<person>ella|el|esta persona|esa persona|el titular|la titular) '
            r'(?:(?:me|le|lo|la|a usted) )?(?:dejo|deja) '
            r'(?:este|el|su|un) numero (?:de usted )?como (?:numero de )?(?:referencia|contacto)\b')),
        ('OBJETO_EXPLICITO_DE_LA_LLAMADA',re.compile(
            r'\b(?:el (?:motivo|fin) de (?:la|mi|esta) llamada es )'
            r'(?:simplemente )?(?:confirmar(?:se)?|verificar) si (?:usted )?'
            r'(?:conoce a|se encuentra)\s+(?P<person>(?:'+HONORIFIC+r')?'+NAME+r')[.?]')),
        ('PERSONA_QUE_DEJO_REFERENCIA',re.compile(
            r'\b(?:(?:el|la) (?:senor|senora|senorita) |que )'
            r'(?P<person>'+NAME+r')\s+(?:dejo|deja) (?:usted |a usted )?'
            r'(?:su|el|un|este) numero (?:de usted )?(?:como )?(?:numero de )?(?:referencia|contacto)\b')),
    ]
    for method,pattern in patterns:
        for match in pattern.finditer(source):
            if _role_at(text,segments,match.start())in{'TITULAR','TERCERO','INTERLOCUTOR'}:continue
            prefix=source[max(0,match.start()-90):match.start()]
            if re.search(r'\b(?:no|dice(?: que)?|dijo(?: que)?|diga(?: que)?|repita(?: que)?|por ejemplo|si fuera)\s*$',prefix):continue
            if not is_statement(source,match.start(),match.start()+12):continue
            if re.search(r'\b(?:usted|ustedes|yo|nosotros|banco|cuenta|tarjeta|'
                         r'referencia|contacto|deuda|saldo|pago|telefono|numero|'
                         r'gerente|supervisor|asesor|licenciado|no|nunca|dice|dijo|debe|tiene|necesita)\b',match['person']):continue
            target=name_words(match['person'])
            prior=[m for m in openings if m.end()<match.start()]
            if method in {'OBJETO_EXPLICITO_DE_LA_LLAMADA','LOCALIZACION_INICIAL_DE_PERSONA_DISTINTA'}:
                if method=='LOCALIZACION_INICIAL_DE_PERSONA_DISTINTA'and match.start()>650:continue
                if not prior:continue
                receiver=name_words(prior[-1]['person'])
                if not receiver or not target or not(receiver-target)or not(target-receiver):continue
            tail=source[match.end():]
            if re.search(r'\b(?:se lo comunico|ya se lo paso|le paso al titular|'
                         r'ahora habla (?:el|la) titular|soy yo|soy (?:el|la) titular)\b',tail):continue
            if not re.search(r'\b(?:recado|mensaje|referencia|contacto|localizar|se comunique|'
                             r'no (?:lo|la) conozco|no se quien es|no esta|no se encuentra)\b',match.group()+' '+tail):continue
            return {'confirmed':True,'method':method,'evidence':match.group(),
                    'target_name':match['person'],'position':match.start(),
                    'human_verified':False,'speaker_roles_confirmed':False}
    return none
