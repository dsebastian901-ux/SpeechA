"""Atribución textual limitada a autopresentación institucional y su cláusula.

No identifica una voz acústica, no extiende un rol a un segmento ni alterna
hablantes. Una cita, un cambio de turno o un rol conocido contradictorio lo anulan.
"""
import re
from app.services.conversation_evidence import normalize

COMPANY=r'(?:m\s*[. ]*r\s*[. ]*s|m\s*[. ]*r\s*[. ]*e\s*[. ]*s|m\.?\s*reyes|mrs)'
INTRO=re.compile(r'\b(?:me (?:estoy )?comunicando de|me comunico de|nos (?:estamos )?comunicando de|nos comunicamos de|hablamos de|le (?:hablo|marcamos) de)\b'
                 r'[^.!?]{0,65}\b'+COMPANY+r'\b')
RELAY=re.compile(r'\b(?:mencione(?:le)?|indique(?:le)?|comente(?:le)?|comparta(?:le)?)\b[^.!?]{0,85}\b(?:se comunico|nos (?:estamos )?comunicando|nos comunicamos)\b'
                 r'[^.!?]{0,90}\b'+COMPANY+r'\b')
QUOTED=re.compile(r'\b(?:dice que|dijo que|me dijo|me dijeron|usted dijo|usted dice|segun|repita|diga que|por ejemplo|supongamos|si yo fuera|soy su (?:espos[oa]|madre|padre|hij[oa]))\b')


def institutional_clause_evidence(unit_text,phrase):
    source=normalize(unit_text);target=normalize(phrase);at=source.find(target)
    if at<0:return None
    for pattern in (INTRO,RELAY):
        for m in pattern.finditer(source[:at]):
            if at-m.end()>230:continue
            prefix=source[max(0,m.start()-110):m.start()]
            bridge=source[m.end():at]
            if QUOTED.search(prefix)or QUOTED.search(bridge)or '?'in bridge or '¿'in bridge:continue
            if re.search(r'\b(?:no|nunca)\s*$',prefix):continue
            # No propagar la identidad tras una respuesta del interlocutor.
            if re.search(r'\b(?:yo |mi |mis |no tengo|ya pague|yo pague|soy su |es mi )',bridge):continue
            if '.'in bridge:continue
            return {'method':'AUTOPRESENTACION_INSTITUCIONAL_EN_MISMA_CLAUSULA',
                    'text':source[m.start():at+len(target)],'speaker_role':'GESTOR',
                    'human_verified':False,'acoustic_voice_identified':False,
                    'scope':'EXCLUSIVE_FINANCIAL_STATEMENT_WITH_SELF_IDENTIFICATION'}
    return None
