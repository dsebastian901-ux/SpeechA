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

        # Repetir una misma oferta no crea dos parcialidades.
        # Solo admitir dos importes idénticos cuando se anuncian
        # expresamente dos pagos / primera y segunda exhibición.
        if abs(float(first[2]) - float(second[2])) < 0.01 and not re.search(
                r'\b(?:dos pagos|dos abonos|dos parcialidades|primer(?:o|a)? pago|'
                r'segund[oa] pago|primera parcialidad|segunda parcialidad)\b',
                fragment):
            continue
        if re.search(r'\bhoy\s+o\s+manana\b', fragment):
            continue

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


_DATE_MONTHS = r'(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)'
_WEEKDAY = r'(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)'


def accepted_amount_values(accepted_evidence, mentions):
    """Exclude calendar days from amounts in an accepted installment recap.

    Numbers in «2000 pesos el lunes 23-30 y 7 de diciembre» are
    [2000], not [2000, 23, 30, 7]. Preserve true small payments with
    explicit currency/payment anchors, e.g. «pago 20 pesos».
    """
    source = normalize(accepted_evidence or '')
    calendar_spans = [
        (m.start(), m.end()) for m in re.finditer(
            rf'\b(?:\d{{1,2}}\s*(?:-|,|/|y)\s*)+\d{{1,2}}\s+de\s+{_DATE_MONTHS}\b',
            source,
        )
    ]
    calendar_spans += [
        (m.start('day'), m.end('day')) for m in re.finditer(
            rf'\b(?:el\s+)?(?:dia\s+)?{_WEEKDAY}\s+(?P<day>\d{{1,2}})\b',
            source,
        )
    ]
    accepted = set()
    for mention in mentions:
        pos, end, value = int(mention[0]), int(mention[1]), float(mention[2])
        raw = source[pos:end].strip()
        if value <= 31 and re.fullmatch(r'\d{1,2}', raw):
            if any(pos >= start and end <= stop for start, stop in calendar_spans):
                continue
            following = source[end:end+24]
            preceding = source[max(0, pos-17):pos]
            if (re.match(rf'\s+de\s+{_DATE_MONTHS}\b', following)
                    or re.search(rf'\b(?:dia|dias|{_WEEKDAY[3:-1]})\s*$', preceding)):
                continue
        accepted.add(value)
    return accepted
