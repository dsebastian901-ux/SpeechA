"""Separar pagos de servicio por convenio de transferencias a una cuenta."""
import re
from app.services.conversation_evidence import normalize,sentence_evidence,_role_at
from app.services.payment_reference_validation import TOKEN,_digits,SEPARATOR

BANKS={'BBVA':r'bbva|bancomer|vancomer|van comer','SANTANDER':r'santander','BANAMEX':r'banamex|citibanamex|citi banamex'}
CODES={'BBVA':'1042378','SANTANDER':'3411','BANAMEX':'4626'}

def bank_service_payment(text,segments=()):
    source=normalize(text)
    destination=bool(re.search(r'\b(?:clabe|cuenta bancaria|cuenta interbancaria|cuenta personal|cuenta de destino|numero de cuenta|transfiera a|transferir a|spei)\b',source))
    routes=[];codes=[]
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role'] in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        value=normalize(unit['text'])
        offer=re.search(r'\b(?:pagos? de servicios?|ingresa(?:r)? (?:el )?numero de convenio|'
                        r'por (?:bancomer|bbva|santander|banamex) tiene que ingresar (?:el )?numero de convenio)\b',value)
        if offer and not re.search(r'\b(?:no|nunca|no es)\s*$',value[:offer.start()]):
            routes.append(dict(unit,phrase=offer.group(),method='PAGO_DE_SERVICIO_POR_CONVENIO'))
    for anchor in re.finditer(r'\bconvenio\s*(?:(?:numero|que es|es|el)\s*[, :]*\s*){0,4}',source):
        if _role_at(text,segments,anchor.start()) in {'TITULAR','TERCERO','INTERLOCUTOR'}:continue
        if re.search(r'\b(?:no|no es|no corresponde al)\s*$',source[max(0,anchor.start()-40):anchor.start()]):continue
        tail=source[anchor.end():anchor.end()+180]
        tokens=list(TOKEN.finditer(tail))
        if not tokens or not re.fullmatch(r'[\s,:]*',tail[:tokens[0].start()]):continue
        before=source[max(0,anchor.start()-180):anchor.start()]
        bank_mentions=[(m.start(),bank) for bank,pattern in BANKS.items() for m in re.finditer(r'\b(?:'+pattern+r')\b',before)]
        if not bank_mentions:continue
        bank=max(bank_mentions)[1];group=[tokens[0]]
        for token in tokens[1:]:
            if not SEPARATOR.fullmatch(tail[group[-1].end():token.start()]):break
            group.append(token)
        if re.match(r'\s*(?:pesos|pagos?|mensualidades|dias?|semanas)\b',tail[group[-1].end():]):continue
        parts=[_digits(t.group()) for t in group]
        if any(p is None for p in parts):continue
        digits=''.join(parts);expected=CODES[bank]
        valid=digits==expected or digits==expected*2
        codes.append({'bank':bank,'digits':digits,'expected':expected,'valid':valid,
                      'text':source[anchor.start():anchor.end()+group[-1].end()],
                      'method':'CONVENIO_LITERAL_O_DICTADO_POR_GRUPOS'})
    invalid=any(not record['valid'] for record in codes)
    # No certificar una CLABE ni agregar bancos por mencionar su nombre.
    # Si no se dicta convenio, la omisión de opciones conserva su puntuación.
    return {'present':bool(routes or codes),'service_only':bool(routes or codes) and not destination,
            'review_required':invalid,'routes':routes,'codes':codes,
            'authorized_banks':sorted({record['bank'] for record in codes if record['valid']}),
            'separates_from_clabe':bool(routes or codes) and not destination and not invalid}
