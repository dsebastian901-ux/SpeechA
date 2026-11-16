"""Una pregunta de cobro atribuible al gestor prueba intento, NO aceptación.

agent_statement omite interrogaciones a propósito; conservar ese filtro para
los compromisos y detectar separadamente preguntas futuras de cobranza.
Nunca confirma importe, fecha, convenio, ni hablante acústico de Whisper.
"""
import re

from app.services.conversation_evidence import normalize, sentence_evidence


_REQUEST = re.compile(
    r"\b(?:usted\s+)?podria\s+realizar\s+su\s+pago(?:\s+de)?\s+"
    r"(?:\d+|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|"
    r"diez|cien|quinientos|ochocientos|mil)\b|"
    r"\b(?:ya|usted)\s+tendra\s+(?:usted\s+)?(?:su\s+|el\s+)?pago\s+"
    r"(?:para\s+)?(?:el\s+dia\s+de\s+)?(?:hoy|manana)\b|"
    r"\b(?:podemos|podriamos)\s+contar\s+con\s+(?:su\s+|el\s+)?pago\b|"
    r"\b(?:se\s+)?confirma(?:ria)?\s+su\s+pago\s+para\s+"
    r"(?:el\s+dia\s+de\s+)?(?:hoy|manana)\b"
)
_QUOTES = re.compile(
    r"\b(?:diga\s+que|dijo\s+que|usted\s+dijo|usted\s+dice|"
    r"repita|por\s+ejemplo|supongamos\s+que)\b"
)
_NOT_REQUEST = re.compile(
    r"\b(?:ya\s+(?:pague|pago|realice|hice)|pago\s+(?:anterior|pasado)|"
    r"comprobante\s+(?:de|del)\s+pago|el\s+pago\s+ya\s+se\s+realizo)\b"
)


def collection_request_question(text, segments=()):
    """Evidencia positiva de solicitud; sin atribuir voz cuando no hay roles."""
    none = {
        "detected": False,
        "evidence": "",
        "speaker_role": "NO DETERMINADO",
        "method": "SIN_SOLICITUD_FUTURA_LOCAL",
    }
    for unit in sentence_evidence(text, segments):
        role = unit.get("speaker_role") or "NO DETERMINADO"
        if role in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
            continue
        normalized = normalize(unit.get("text") or "")
        for match in _REQUEST.finditer(normalized):
            prefix = normalized[max(0, match.start() - 85):match.start()]
            clause = normalized[max(0, match.start() - 120):match.end() + 80]
            if _QUOTES.search(prefix) or _NOT_REQUEST.search(clause):
                continue
            if re.search(r"\b(?:no|nunca)\s+$", prefix):
                continue
            return {
                "detected": True,
                "evidence": unit.get("text") or "",
                "speaker_role": role,
                "method": "SOLICITUD_DE_PAGO_FUTURO",
                "human_verified": False,
                "acoustic_voice_identified": False,
            }
    return none
