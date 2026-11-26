"""Espera sin retoma: ventanas ASR para revisión, sin atribuir abandono."""
import math
import re

from app.services.conversation_evidence import normalize, role_of


WAIT_LIMIT_SECONDS = 65.0  # Aclaración operativa del usuario, 6/nov/2026.
CUSTOMER_ROLES = {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}
WAIT_REQUEST = re.compile(
    r'\b(?:un momento|un momentito|espere (?:un momento|en (?:la )?linea)|'
    r'permitame(?=\s*(?:[,!.]|$|permitame\b))|'
    r'permanezca en (?:la )?linea|permitame (?:verificar|validar|revisar|consultar)|'
    r'no (?:me )?cuelg(?:a|ue)(?: la llamada)?[, ]+para que le (?:de|brinde|proporcione) (?:la )?informacion)\b')
RESUMPTION = re.compile(
    r'\b(?:gracias por (?:esperar|su espera|mantenerse)|sigo con usted|ya (?:regrese|volvi|estoy de vuelta)|'
    r'continuamos|le (?:comento|confirmo|indico|informo|explico)|verificando (?:el |su )?sistema|'
    r'ya (?:revisando|consultando|verificando)|su servidor[ae]?|'
    r'(?:puede|podria|requiere|necesita|tiene que) (?:usted )?(?:realizar|aplicar|hacer|cubrir|enviar)|'
    r'(?:su|el) (?:pago|importe|saldo) (?:es|seria|queda|se)|su (?:cuenta|tarjeta) (?:registra|presenta|se encuentra))\b')
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
    cursor=0
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
        position=source.find(normalize(fragment),cursor)
        if position<0:
            invalid+=1
            continue
        cursor=position+len(normalize(fragment))
        role = role_of(segment.get('speaker_role') or segment.get('role') or segment.get('speaker'))
        label = re.match(r'^\s*(gestor|agente|asesor|titular|familiar|tercero|interlocutor|cliente)\s*:\s*', fragment, re.I)
        if label:
            role = role_of(label[1])
        unit = {'start': start, 'end': end, 'text': fragment, 'speaker_role': role,
                'text_start':position,'text_end':cursor}
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

    # Las preguntas de gestión y sus respuestas acotadas ya se interpretan
    # en el motor financiero. Reutilizar esas posiciones para reconocer retoma;
    # no exigir una frase de cortesía determinada mientras el diálogo continúa.
    from app.services.payment_intent_frames import payment_frames
    financial_returns=[f['question_position']for f in payment_frames(text,segments)
        if f['own_financial_response'] or f['accepted'] or f['history']]
    from app.services.speech_scope import nonassertive_prefix
    pending = None
    for unit in units:
        value = normalize(unit['text'])
        if pending:
            if (unit['end']-unit['start']>=WAIT_LIMIT_SECONDS
                    and len(re.findall(r'\w+',value))<=8
                    and (CHECKING_PROMPT.fullmatch(value)or re.fullmatch(r'(?:(?:bueno|hola)[, ]+)?buen[ao]s? (?:dias?|tardes?|noches?)[.! ]*',value))):
                record(unit['start'],unit['end'],'PROMPT_DE_ESPERA_EN_SEGMENTO_ASR_IMPRECISO',unit['text'])
            # Un «¿bueno?, ¿me escucha?» del cliente no acredita regreso del
            # gestor. Con voz desconocida solo se toma una intervención plena.
            framed_return=any(unit['text_start']<=position<unit['text_end']for position in financial_returns)
            resumed = (unit['speaker_role'] == 'GESTOR' or
                       (unit['speaker_role'] not in CUSTOMER_ROLES and RESUMPTION.search(value)
                        and not re.search(r'\b(?:diga que|dice que|dijo que|repita que|por ejemplo)\b',value))
                       or framed_return)
            if resumed or _closing(value, allow_brief=True):
                record(pending['end'], unit['start'], 'ESPERA_ANUNCIADA_SIN_RETOMA', pending['text'], unit['text'])
                pending = None
        request = WAIT_REQUEST.search(value)
        if request and request.group()=='permitame'and unit['end']-unit['start']<WAIT_LIMIT_SECONDS:
            request=None  # Un prompt corto aislado no prolonga una espera por sí solo.
        if request and unit['speaker_role'] not in CUSTOMER_ROLES:
            prefix = value[max(0, request.start()-60):request.start()]
            reported=bool(nonassertive_prefix(value,request.start()) or (
                re.search(r'\b(?:hable|hacian|hacia|me dijeron|me decian)\b',prefix)
                and re.search(r'\b(?:hablaba|hablaron|dijeron|decian)\b',value[request.end():])))
            if not reported and not re.search(r'\b(?:no|nunca|dijo que|me dijeron que|diga que|si dice)\s*$', prefix) and not _closing(value, allow_brief=True):
                # Un prompt de dos palabras puede ocupar una ventana ASR de
                # varios minutos. No tratar toda esa ventana como habla plena
                # ni afirmar silencio: señalar su imprecisión para cotejo acústico.
                if len(re.findall(r'\w+',value))<=8 and unit['end']-unit['start']>=WAIT_LIMIT_SECONDS:
                    record(unit['start'],unit['end'],'PROMPT_DE_ESPERA_EN_SEGMENTO_ASR_IMPRECISO',unit['text'])
                if pending is None or unit['speaker_role']=='GESTOR':
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
