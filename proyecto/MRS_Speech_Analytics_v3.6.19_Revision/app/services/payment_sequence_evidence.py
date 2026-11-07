"""Dos pagos solo se suman si existe una secuencia de pago explícita y local."""
import re
from app.services.conversation_evidence import normalize


def bounded_two_payment_sequence(source, candidates):
    """No sumar precios, propuestas alternativas, centavos o días repetidos.

    Las parcialidades ordinales se resuelven en installment_validation. Aquí
    se cubre el formato compacto «1000 hoy y 1500 mañana» con dos acciones.
    """
    source = normalize(source)
    unique = {}
    for _, _, mention in candidates:
        unique.setdefault((mention[0],mention[1]), mention)
    mentions = sorted(unique.values(), key=lambda m:m[0])
    for first, second in zip(mentions, mentions[1:]):
        if second[0]-first[1] > 180 or first[2] < 10 or second[2] < 10:
            continue
        fragment = source[max(0,first[0]-65):min(len(source),second[1]+65)]
        if re.search(r'\b(?:o bien|o en|en lugar de|mejor|alternativa|antes me|me dijeron|whatsapp|telefono|referencia)\b',fragment):
            continue
        actions = re.findall(r'\b(?:pago|pagar|pague|deposito|depositar|abono|abonar)\b',fragment)
        if not actions or not re.search(r'\bhoy\b[^.!?]{0,180}\bmanana\b',fragment):
            continue
        # Ambos importes deben estar ligados a la secuencia, no solo cerca.
        middle = source[first[1]:second[0]]
        if not re.search(r'\b(?:y|restante|otro|segundo)\b',middle) and not re.match(r'y\b',source[second[0]:]):
            continue
        return [float(first[2]),float(second[2])]
    return []
