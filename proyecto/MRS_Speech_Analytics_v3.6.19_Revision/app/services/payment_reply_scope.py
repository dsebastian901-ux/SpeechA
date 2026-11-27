"""A request to repair communication is not an answer about paying."""
import re

COMMUNICATION = re.compile(
    r'\b(?:oigo|oye|oir|escucho|escucha|escuche|escuchar|entiendo|entiende|'
    r'entendi|entendio|entender|comprendo|comprende|comprender|repita|repetir)\b|'
    r'\bse (?:corta|corto|entrecorta)\b')
FINANCIAL_DECISION = re.compile(
    r'\bno (?:puedo|podria|voy a|quiero|pienso) (?:pagar|abonar|depositar|cubrir)|'
    r'\bno (?:acepto|me comprometo)|\bno tengo (?:dinero|trabajo|esa cantidad|la cantidad)|'
    r'\bno me alcanza|\bsi (?:puedo pagar|consigo dinero)|'
    r'\b(?:me comprometo a|voy a) (?:pagar|depositar|abonar)|\b(?:pagare|depositare|abonare)\b')


def communication_repair(reply):
    from app.services.conversation_evidence import normalize
    value = normalize(reply)
    difficulty=(any(re.search(r'\b(?:no|tampoco)\b[^.!?;]{0,45}$',value[max(0,m.start()-45):m.start()])
                    for m in COMMUNICATION.finditer(value))
                or re.search(r'\b(?:repita|repetir|se (?:corta|corto|entrecorta))\b',value))
    return bool(difficulty and COMMUNICATION.search(value) and not FINANCIAL_DECISION.search(value))
