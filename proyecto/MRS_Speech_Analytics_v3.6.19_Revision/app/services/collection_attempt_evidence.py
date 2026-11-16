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
# Una pregunta sobre un depósito ya realizado no es una nueva gestión.
# Examinar SOLO la cláusula de la pregunta, no todo el audio: una consulta
# sobre un pago de ayer no invalida un requerimiento posterior para mañana.
_HISTORICAL_PAYMENT_QUALIFIER = re.compile(
    r"\b(?:que\s+(?:ya\s+)?(?:realizo|realizaron|efectuo|efectuaron|"
    r"hizo|hicieron|deposito|depositaron|pago|pagaron|abono|abonaron)\b|"
    r"(?:de|del|correspondiente\s+a)\s+(?:ayer|antier|la\s+semana\s+pasada|"
    r"el\s+mes\s+pasado)\b|ya\s+(?:hizo|realizo|efectuo|deposito|pago)\b)"
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
            # La solicitud futura se analiza localmente: no anularla porque
            # en una oración anterior mencionaron un comprobante o pago.
            if _QUOTES.search(prefix):
                continue
            # Solo el complemento de ESTE requerimiento; no usar una frase
            # histórica anterior como justificación para omitir cobro nuevo.
            after = re.split(r"[?.!;]", normalized[match.end():], maxsplit=1)[0][:150]
            if _HISTORICAL_PAYMENT_QUALIFIER.search(after):
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
