"""Espera sin retoma: ventanas ASR para revisión, sin atribuir abandono."""
import math
import re

from app.services.conversation_evidence import normalize, role_of


WAIT_LIMIT_SECONDS = 65.0  # Aclaración operativa del usuario, 6/nov/2026.
CUSTOMER_ROLES = {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}
WAIT_REQUEST = re.compile(
    r'\b(?:un momento|un momentito|espere (?:un momento|en (?:la )?linea)|'
    r'permanezca en (?:la )?linea|permitame (?:verificar|validar|revisar|consultar))\b')
CHECKING_PROMPT = re.compile(
    r'(?:(?:bueno|hola|oiga|si|aja|ok|esta bien|aqui estoy|me escucha|sigue ahi|'
    r'me oye|alo|sigo aqui|aqui sigo|aqui espero|de acuerdo|gracias|por favor)[, .!?¿¡]*)+')


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) and value >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _nonverbal(text):
    return bool(re.fullmatch(r'[\s.!?…-]*|[\[(](?:musica|music|silencio|silence|ruido|noise)[\])].?', normalize(text)))


def _closing(text, allow_brief=False):
    value = normalize(text)
    for match in re.finditer(r'\b(?:hasta luego|nos vemos|gracias por su tiempo|'
                             r'que tenga (?:(?:un|una) )?(?:buen|buena|excelente|bonita) (?:dia|tarde|noche)|'
                             r'gracias[, ]+(?:buen dia|buena tarde))\b', value):
        if re.search(r'\b(?:no|nunca|diga|dijo|me dijeron que)\s*$', value[:match.start()]):
            continue
        if not WAIT_REQUEST.search(value[match.end():]):
            return True
    if allow_brief and re.search(r'(?:^|[.!?]\s*)(?:buen dia|buena tarde|buenas tardes|buenas noches)[.! ]*$', value):
        return True
    return False


def _closed_recording_tail(units):
    if _closing(units[-1]['text'], allow_brief=len(units) > 1):
        return True
    if len(units) < 2 or not _closing(units[-2]['text'], allow_brief=True):
        return False
    reply = normalize(units[-1]['text'])
    reply = re.sub(r'^\s*(?:gestor|agente|asesor|titular|familiar|tercero|interlocutor|cliente)\s*:\s*', '', reply)
    reply = reply.strip(' ¿¡?!.,')
    # Una cortesía breve después de la despedida no reabre la conversación.
    # El ASR puede pegar hasta cuatro letras a «igualmente». Solo se admite
    # esa variante tras una despedida explícita en el segmento anterior.
    return bool(re.fullmatch(r'(?:muchas gracias|gracias|[a-z]{0,4}igualmente|'
                             r'usted tambien|a usted|adios|hasta luego)', reply))


def _timed_units(text, segments, duration):
    source = normalize(text)
    units, speech, invalid = [], [], 0
    for segment in segments or ():
        if not isinstance(segment, dict):
            invalid += 1
            continue
        fragment = str(segment.get('text', segment.get('texto', '')) or '').strip()
        if not fragment or _nonverbal(fragment):
            continue
        start = _number(segment.get('start', segment.get('inicio')))
        end = _number(segment.get('end', segment.get('fin')))
        if (start is None or end is None or end <= start or
                (duration is not None and end > duration + 0.1) or normalize(fragment) not in source):
            invalid += 1
            continue
        role = role_of(segment.get('speaker_role') or segment.get('role') or segment.get('speaker'))
        label = re.match(r'^\s*(gestor|agente|asesor|titular|familiar|tercero|interlocutor|cliente)\s*:\s*', fragment, re.I)
        if label:
            role = role_of(label[1])
        unit = {'start': start, 'end': end, 'text': fragment, 'speaker_role': role}
        units.append(unit)
        words = segment.get('words', segment.get('palabras')) or []
        word_units = []
        for word in words:
            if not isinstance(word, dict):
                word_units = []
                break
            a = _number(word.get('start', word.get('inicio')))
            b = _number(word.get('end', word.get('fin')))
            value = str(word.get('word', word.get('palabra', '')) or '').strip()
            if a is None or b is None or a < start or b > end or b < a or not value:
                word_units = []
                break
            word_units.append(dict(unit, start=a, end=b, text=value))
        # Un conjunto parcial de palabras no demuestra que el resto fue silencio.
        compact = lambda value: re.sub(r'\W', '', normalize(value))
        spoken_text = fragment[label.end():] if label else fragment
        complete_words = word_units and compact(' '.join(w['text'] for w in word_units)) == compact(spoken_text)
        speech.extend(word_units if complete_words else [unit])
    return sorted(units, key=lambda u: (u['start'], u['end'])), sorted(speech, key=lambda u: (u['start'], u['end'])), invalid


def assess_call_wait(text, segments=(), duration_seconds=None):
    """65 s inclusive; anotar vacíos ASR y espera anunciada sin retoma.

    El hueco antes de iniciar conversación y la cola después de despedirse
    no se imputan como espera. Las ventanas son indicios, no diarización ni
    prueba acústica de silencio. Con tiempos ausentes se informa NO EVALUABLE.
    """
    duration = _number(duration_seconds)
    duration = duration if duration else None
    units, speech, invalid = _timed_units(text, segments, duration)
    intervals, measured = [], []

    def record(start, end, method, before, after=''):
        if end < start:
            return
        elapsed = end - start
        # Las marcas decimales ASR pueden restarse como 64.99999999999999
        # aunque el intervalo sea exactamente 65 s. No tolerar 64.999 s.
        if math.isclose(elapsed, WAIT_LIMIT_SECONDS, rel_tol=0, abs_tol=1e-9):
            elapsed = WAIT_LIMIT_SECONDS
        measured.append(elapsed)
        if elapsed >= WAIT_LIMIT_SECONDS:
            intervals.append({'start': start, 'end': end, 'seconds': elapsed,
                              'method': method, 'before_text': before, 'after_text': after})

    if speech:
        previous = speech[0]
        for current in speech[1:]:
            if current['start'] > previous['end']:
                record(previous['end'], current['start'], 'INTERVALO_SIN_TEXTO_ASR', previous['text'], current['text'])
            if current['end'] > previous['end']:
                previous = current
        if duration is not None and not _closed_recording_tail(units):
            record(previous['end'], duration, 'FINAL_SIN_RETOMA_ASR', units[-1]['text'])

    pending = None
    for unit in units:
        value = normalize(unit['text'])
        if pending:
            # Un «¿bueno?, ¿me escucha?» del cliente no acredita regreso del
            # gestor. Con voz desconocida solo se toma una intervención plena.
            resumed = (unit['speaker_role'] == 'GESTOR' or
                       (unit['speaker_role'] not in CUSTOMER_ROLES and
                        not CHECKING_PROMPT.fullmatch(value.strip('¿¡?! .,'))))
            if resumed or _closing(value, allow_brief=True):
                record(pending['end'], unit['start'], 'ESPERA_ANUNCIADA_SIN_RETOMA', pending['text'], unit['text'])
                pending = None
        request = WAIT_REQUEST.search(value)
        if request and unit['speaker_role'] not in CUSTOMER_ROLES:
            prefix = value[max(0, request.start()-60):request.start()]
            if not re.search(r'\b(?:no|nunca|dijo que|me dijeron que|diga que|si dice)\s*$', prefix) and not _closing(value, allow_brief=True):
                pending = unit
    if pending and duration is not None:
        record(pending['end'], duration, 'ESPERA_ANUNCIADA_HASTA_EL_FINAL', pending['text'])

    # Un hueco y una espera anunciada pueden describir la misma ventana.
    unique = {(e['start'], e['end']): e for e in intervals}
    intervals = sorted(unique.values(), key=lambda e: (e['start'], e['end']))
    reviewed = bool(intervals)
    return {
        'threshold_seconds': WAIT_LIMIT_SECONDS,
        'review_required': reviewed,
        'result': 'REVISAR - ESPERA DE 65 SEGUNDOS O MÁS' if reviewed else
                  'SIN ESPERA PROLONGADA DETECTADA' if speech else 'NO EVALUABLE - SIN TIEMPOS ASR UTILIZABLES',
        'max_no_conversation_seconds': max(measured, default=0.0) if speech else None,
        'intervals': intervals,
        'usable_segments': len(units), 'invalid_segments': invalid,
        'method': 'MARCAS_TIEMPO_ASR',
        'reason': 'Espera de 65 segundos o más sin retoma confirmada; revisar intervalo y audio.' if reviewed else '',
        'limit': 'Los tiempos ASR no prueban silencio acústico ni identifican al responsable; no generan falla grave por sí solos.',
    }
