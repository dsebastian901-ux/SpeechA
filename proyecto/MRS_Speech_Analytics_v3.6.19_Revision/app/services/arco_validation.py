"""Procedimiento ARCO: derechos expresos, correo e INE y comprobante de línea."""
import re
from app.services.conversation_evidence import agent_statement, normalize, sentence_evidence, _role_at


ID_DOCUMENT = r'(?:ine|identificacion oficial)'
LINE_DOCUMENT = r'(?:(?:comprobante|recibo) (?:de (?:la |su )?)?(?:linea(?: telefonica)?|telefono|titularidad de (?:la |su )?linea|propiedad de (?:la |su )?linea))'
REQUEST = r'\b(?:envie|enviar|enviarnos|mande|mandar|adjunte|adjuntar|adjuntando|proporcione|proporcionar|presente|presentar|solicito|solicitamos|solicitare|pido|requiere|requerimos|necesito|necesitamos)\b'


def document_requests(text, segments=()):
    requested={'ine':False,'line_proof':False};evidence=[];previous='';alternatives=False
    for unit in sentence_evidence(text,segments):
        if unit['speaker_role'] in {'TITULAR','TERCERO','INTERLOCUTOR'}:
            previous='';continue
        s=normalize(unit['text'])
        if '?' in s or '¿' in s or re.search(r'\b(?:yo (?:puedo|voy a|debo)|puedo yo) (?:enviar|mandar|adjuntar)\b',s):
            previous='';continue
        block=(previous+' '+s if previous and re.match(
            r'^(?:y|tambien|ademas)\s+(?:lo que es|su|el|la|un|una)\b',s) else s)
        found={}
        for key,pattern in [('ine',ID_DOCUMENT),('line_proof',LINE_DOCUMENT)]:
            for match in re.finditer(r'\b'+pattern+r'\b',block):
                prefix=block[max(0,match.start()-200):match.start()]
                if not re.search(REQUEST,prefix):continue
                negative=bool(re.search(r'\b(?:no|nunca|jamas|tampoco|evite|evitar|prohibido)\b[^.!?]{0,180}$',prefix))
                requested[key]=not negative;found[key]=not negative
                evidence.append({'document':key,'requested':not negative,'text':unit['text'],
                                 'speaker_role':unit['speaker_role'],'start':unit['start'],'end':unit['end']})
        if found.get('ine') and found.get('line_proof'):
            alternatives=bool(re.search(
                r'\b'+ID_DOCUMENT+r'\s+(?:o|u)\s+(?:(?:solo|solamente|el|su|un)\s+)*'+LINE_DOCUMENT+r'\b|'
                r'\b'+LINE_DOCUMENT+r'\s+(?:o|u)\s+(?:(?:solo|solamente|la|su|una)\s+)*'+ID_DOCUMENT+r'\b',block))
        previous=block if found else ''
    return {'ine_requested':requested['ine'],'line_proof_requested':requested['line_proof'],
            'documents_as_alternatives':alternatives,
            'both_documents_requested':all(requested.values()) and not alternatives,'evidence':evidence}


def qualitative_line_tenure(text,segments=()):
    source=normalize(text)
    question=re.compile(r'\b(?:(?:desde )?hace cuanto(?: tiempo)?|cuanto tiempo)\b'
        r'[^?!.]{0,90}\b(?:linea|numero|telefono)\b[^?!.]{0,25}\?\s*'
        r'(?:(?:gestor|interlocutor|cliente|tercero)\s*:\s*)?'
        r'(?:(?:uy|pues)[, ]+)?(?:(?:senor|senora|senorita|joven)[, ]+)?'
        r'(?P<answer>toda la vida|muchos anos|varios anos)\b')
    for match in question.finditer(source):
        role=_role_at(text,segments,match.start('answer'))
        tail=source[match.end():match.end()+55].split('.')[0]
        if role=='GESTOR' or re.search(r'\b(?:no|apenas|en realidad)\b',tail):continue
        return {'confirmed':True,'method':'RESPUESTA_CUALITATIVA_ANTIGUEDAD',
                'evidence':match.group(),'speaker_role':role,'numeric_years':None}
    return {'confirmed':False,'method':'SIN_RESPUESTA_CUALITATIVA','evidence':'','numeric_years':None}


def assess_arco(text,segments=(),*,email_given=False):
    rights=agent_statement(text,segments,r'\bderechos? (?:a )?arco\b')
    process=agent_statement(text,segments,
        r'\b(?:puede ejercer|para ejercer|solicitar|tramitar|ejercer|procedimiento|proceso|tramite|hacer efectivos?)\b'
        r'.{0,85}\bderechos? (?:a )?arco\b|'
        r'\bderechos? (?:a )?arco\b.{0,85}\b(?:puede ejercer|puede solicitar|se tramitan|debe solicitar)\b')
    documents=document_requests(text,segments)
    removal=agent_statement(text,segments,
        r'\b(?:solicitar|tramitar|pedir)\b.{0,35}\bbaja\b.{0,45}\b(?:numero|linea)\b.{0,55}\bbase de datos\b')
    denied=any(u['speaker_role'] not in {'TITULAR','TERCERO','INTERLOCUTOR'} and re.search(
        r'\bno (?:puede|podra|voy a|vamos a|le voy a|se puede) (?:ejercer|tramitar|explicar|solicitar)\b.{0,65}\barco\b|'
        r'\bno (?:existen|aplican)\b.{0,45}\bderechos? (?:a )?arco\b',normalize(u['text']))
        for u in sentence_evidence(text,segments))
    complete=bool(rights and process and email_given and documents['both_documents_requested'] and not denied)
    # Un indicio de orientación no satisface el guion. Evita certificar una
    # omisión acústica cuando ASR conserva pasos relacionados pero no el término.
    arco_reference=agent_statement(text,segments,r'\barco\b')
    partial=bool(not process and not denied and (
        (removal and documents['both_documents_requested'])
        or (arco_reference and (email_given or documents['ine_requested'] or documents['line_proof_requested']))))
    reasons=[]
    if not rights:reasons.append('No se detectó mención expresa de derecho(s) ARCO; requiere cotejo del audio.')
    elif not process:reasons.append('La mención de derecho(s) ARCO no confirma la explicación del procedimiento.')
    if not email_given:reasons.append('No se confirmó el correo oficial de privacidad; no completar un dominio dudoso.')
    if not documents['ine_requested']:reasons.append('No se detectó solicitud de INE o identificación oficial.')
    if not documents['line_proof_requested']:reasons.append('No se detectó solicitud del comprobante de la línea.')
    if documents['documents_as_alternatives']:reasons.append('INE y comprobante se ofrecieron como alternativas; se requieren ambos documentos.')
    if denied:reasons.append('Se detectó negación expresa del trámite de derechos ARCO.')
    return {'rights_mentioned':rights,'process_explained':bool(rights and process and not denied),
            'email_given':bool(email_given),**documents,'removal_guidance':removal,'process_denied':denied,
            'complete_procedure':complete,'partial_guidance_requires_audio':partial,'reasons':reasons}
