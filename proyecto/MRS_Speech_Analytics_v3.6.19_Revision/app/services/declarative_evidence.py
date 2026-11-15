"""Ámbito de declaraciones en texto ASR; no asigna hablantes ni tiempos.

Una pregunta y la respuesta pueden compartir oración/ventana de Whisper.
Se conservan las posiciones para no convertir preguntas o citas en hechos.
"""
import re


def statement_spans(source):
    """Tramos fuera de interrogaciones, incluidas las que no llevan apertura."""
    questions = []
    cursor = 0
    for closing in re.finditer(r'\?', source):
        end = closing.start()
        opening = source.rfind('¿', cursor, end)
        if opening >= 0:
            start = opening
        else:
            # Sin ¿, el signo final afecta a su cláusula, no a una respuesta
            # posterior ni a la afirmación anterior a un punto.
            start = max(source.rfind(c, cursor, end) for c in '.!?;') + 1
            start = max(cursor, start)
        questions.append((start, end + 1))
        cursor = end + 1
    opening = source.rfind('¿', cursor)
    if opening >= 0:
        questions.append((opening, len(source)))
    cursor = 0
    for start, end in questions:
        if start > cursor and source[cursor:start].strip():
            yield cursor, start
        cursor = max(cursor, end)
    if cursor < len(source) and source[cursor:].strip():
        yield cursor, len(source)


def declarative_units(text, segments=()):
    from app.services.conversation_evidence import sentence_evidence, normalize
    for unit in sentence_evidence(text, segments):
        source = normalize(unit['text'])
        for start, end in statement_spans(source):
            value = source[start:end].strip()
            if value:
                yield dict(unit, text=value)


def is_statement(source, start, end):
    return any(a <= start and end <= b for a, b in statement_spans(source))
