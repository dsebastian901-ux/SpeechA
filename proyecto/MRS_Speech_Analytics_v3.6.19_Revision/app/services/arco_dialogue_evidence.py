"""Conocimiento y antigüedad de línea expresados en diálogo, sin inferir el Excel."""
import re
from app.services.conversation_evidence import normalize,_role_at,recipient_statement
from app.services.message_contact_evidence import _outside_question


def clarified_line_tenure(text,segments=()):
    source=normalize(text)
    none={'confirmed':False,'method':'SIN_ANTIGUEDAD_ACLARADA','evidence':'','numeric_years':None}
    question=re.compile(r'\b(?:(?:cuanto|que) tiempo|desde (?:hace )?cuando|hace cuanto(?: tiempo)?)\b[^?!.]{0,100}\b(?:linea|numero|telefono)\b[^?!.]{0,35}[?.]')
    duration=re.compile(r'\b(?:un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|\d+) (?:anos?|mes(?:es)?|semanas?|dias?)\b')
    for q in question.finditer(source):
        if re.search(r'\b(?:recibiendo|llamadas|marcandole)\b',q.group()):continue
        tail=source[q.end():q.end()+420]
        stop=re.search(r'\b(?:correo|derechos?|ine|comprobante|pago|saldo|recibiendo llamadas|tiempo (?:le )?(?:marcan|llaman))\b',tail)
        if stop:tail=tail[:stop.start()]
        for value in duration.finditer(tail):
            pos=q.end()+value.start();end=q.end()+value.end()
            if _role_at(text,segments,pos)=='GESTOR'or not _outside_question(source,pos,end):continue
            prefix=tail[max(0,value.start()-65):value.start()]
            if re.search(r'\b(?:si tuviera|si fuera|por ejemplo|dijo que|dice que|diga que|no es cierto que)\b',prefix):continue
            return {'confirmed':True,'method':'RESPUESTA_DE_ANTIGUEDAD_TRAS_ACLARACION',
                'evidence':source[q.start():end],'speaker_role':_role_at(text,segments,pos),'numeric_years':None}
    recent=re.compile(r'\b(?:yo )?(?:acabo|acabamos) de (?:comprar|adquirir|contratar) (?:este |esta |el |la |un |una )?(?:telefono|celular|linea|numero|chip|sim)\b')
    for value in recent.finditer(source):
        if _role_at(text,segments,value.start())=='GESTOR'or not _outside_question(source,value.start(),value.end()):continue
        if re.search(r'\b(?:no|nunca|diga que|dice que|dijo que|no es cierto que)\s*$',source[max(0,value.start()-65):value.start()]):continue
        return {'confirmed':True,'method':'ADQUISICION_RECIENTE_REPORTADA_SIN_FECHA_INVENTADA',
            'evidence':value.group(),'speaker_role':_role_at(text,segments,value.start()),'numeric_years':None}
    return none


def listed_knowledge_denial(text,segments=()):
    source=normalize(text)
    none={'confirmed':False,'method':'SIN_NEGATIVA_A_LISTA_DE_RELACIONES','evidence':''}
    pattern=re.compile(r'\bconocid[oa][, ]+(?:(?:amig[oa]|vecin[oa])[, ]+)?familiar\b[^?!.]{0,90}[?.]\s*'
                       r'(?P<answer>no(?:[, ]+(?:la verdad es que no|la verdad no|no|para nada))?)(?=[.,!?]|$)')
    for match in pattern.finditer(source):
        if _role_at(text,segments,match.start('answer'))=='GESTOR':continue
        if re.search(r'\b(?:no|dice que|dijo que|diga que|si)\s*$',source[max(0,match.start()-65):match.start()]):continue
        if re.match(r'\s*\?',source[match.end():]):continue
        from app.services.conversation_evidence import assess_recado
        known=assess_recado(text,segments)
        if any(known.get(k)for k in ['family','work_relationships','third_party_relationships']):continue
        if recipient_statement(text,segments,r'\b(?:soy yo|soy (?:el|la) titular|si (?:lo|la) conozco)\b'):continue
        return {'confirmed':True,'method':'NIEGA_LISTA_EXPLICITA_DE_RELACIONES',
            'evidence':match.group(),'speaker_role':_role_at(text,segments,match.start('answer'))}
    return none
