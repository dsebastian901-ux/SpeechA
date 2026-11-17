"""Gestión de aclaración ya abierta, sin acreditar su resolución bancaria."""
import re
from app.services.conversation_evidence import normalize,_role_at,recipient_statement,agent_statement
from app.services.declarative_evidence import declarative_units


def active_clarification(text,segments=()):
    source=normalize(text);reported=[]
    for unit in declarative_units(text,segments):
        if unit['speaker_role']=='GESTOR':continue
        value=normalize(unit['text'])
        match=re.search(r'\b(?:ya (?:tengo|meti|ingrese|levante|presente)(?: una| la)? aclaracion|'
            r'ya me tiene aclaracion|(?:yo )?(?:hice|ingrese|levante|presente) (?:una|la|mi) aclaracion)\b',value)
        if match and not re.search(r'\b(?:no|dice que|dijo que|diga que|si|cuando)\s*$',value[:match.start()]):
            reported.append(unit['text'])
    acknowledged=recipient_statement(text,segments,
        r'\bme (?:mandaron|enviaron|dieron|proporcionaron) (?:el |un |mi )?folio\b')
    requested=agent_statement(text,segments,
        r'\b(?:mande|envie|mandar|enviar|manden)\b[^.!?]{0,55}\b(?:foto del |el |ese )?folio\b')
    # La pregunta del folio también forma parte de la gestión de seguimiento;
    # se exige además su acuse explícito y una fecha de resolución, no un sí.
    requested=requested or bool(re.search(r'\bme puede (?:dar|enviar|mandar) (?:el |su )?folio\b',source))
    resolution=False
    for match in re.finditer(r'\b(?:cuando|que dia)\b[^?!.]{0,70}\b(?:fecha de )?resolucion\b[^?!.]{0,25}\?\s*'
        r'(?P<answer>(?:le digo que |le comento que )?(?:manana|hoy|el (?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)|el dia \d{1,2}))\b',source):
        if _role_at(text,segments,match.start('answer'))!='GESTOR':resolution=True
    confirmed=bool(reported and acknowledged and requested and resolution)
    return {'confirmed':confirmed,'evidence':' / '.join(reported)if confirmed else'',
            'case_number_reported_by_customer':bool(acknowledged),'document_requested':bool(requested),
            'resolution_date_reported':resolution,'bank_confirmation':False,'human_verified':False}
