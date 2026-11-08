"""Seguimiento de fallecimiento reportado; conserva estatus según la usuaria.

No certifica fallecimiento civil ni exime privacidad, trato o negociación.
"""
import re
from app.services.conversation_evidence import normalize,sentence_evidence,_role_at


def death_followup(text,segments=()):
    source=normalize(text);reports=[]
    for u in sentence_evidence(text,segments):
        if u['speaker_role']=='GESTOR':continue
        value=normalize(u['text'])
        if re.search(r'\b(?:ya (?:acabo de decir que )?fallecio|(?:mi |su |la |el )?(?:titular|mama|papa|madre|padre|herman[oa]) (?:ya )?fallecio|ya (?:les )?(?:inform[eao]|coment[eao])[^.!?]{0,60}\bfallecio)\b',value):
            if '?'in value or re.search(r'\b(?:no|si|supongamos|dice que|diga que|me dijeron que)\b[^.!?]{0,20}\bfallecio',value):continue
            reports.append(u)
    # Fecha respondida a la pregunta de fallecimiento en un seguimiento documental.
    q=re.search(r'\b(?:hace )?cuanto tiempo fallecio(?:[, ]+perdon)?\?\s*(?P<answer>\d{1,2} de [a-z]+)',source)
    if q and _role_at(text,segments,q.start('answer'))!='GESTOR':reports.append({'text':q.group(),'method':'FECHA_DE_DEFUNCION_REPORTADA','human_verified':False})
    document=re.search(r'\b(?:mande|mandar|enviar|mandando|mandando|compartir(?:me)?|mandar|manden|envie|solicita)[^.!?]{0,65}\b(?:acta de defuncion|acto certificado de funcion|certificado de defuncion)\b',source)
    from app.services.message_dialogue_evidence import callback_available
    contact=bool(reports and document and callback_available(text,segments))
    valid=bool(reports and document and contact)
    return {'valid':valid,'reported_death':bool(reports),'requested_death_document':bool(document),
        'contact_available':bool(contact),'evidence':reports,'document_evidence':document.group()if document else'',
        'human_verified':False,'civil_death_verified':False,'policy_source':'ACLARACION_USUARIO_CONSERVAR_ESTATUS_FALLECIMIENTO_20261108'}
