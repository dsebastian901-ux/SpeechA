"""Execution and usefulness are separate states; no voting away contradictions."""


def third_state(required, attempts, semantic):
    from app.services.context_audio_recovery import reading_quality
    if not required:
        return 'NO_REQUERIDA'
    if len(attempts) < 3:
        return 'PENDIENTE'
    if attempts[2].get('error'):
        return 'FALLIDA'
    if any(r['state'] == 'CONTRADICTORIO' for r in semantic['rules']):
        return 'CONTRADICTORIA'
    if not reading_quality(attempts[2]) or not any(
            r['state'] in {'CONFIRMADO', 'DESCARTADO_CON_EVIDENCIA'} for r in semantic['rules']):
        return 'INSUFICIENTE'
    return 'EJECUTADA'


def primary_fact_conflict(purpose, primary, attempts, relation):
    """Lexical ASR variation is not a third-listening trigger.

    Only incompatible facts from the primary interval justify extra contrast.
    An unparsed original remains on record; it is not a contrary observation.
    """
    from app.services.context_fact_consensus import extract_facts
    from app.services.context_audio_recovery import digest
    if not primary:
        return False
    original = extract_facts({'text': primary}, purpose, relation)
    recovered = [f for a in attempts for f in extract_facts(a, purpose, relation)]
    return any(a['rule'] == b['rule'] and
               (a['polarity'] != b['polarity'] or digest(a['value']) != digest(b['value']))
               for a in original for b in recovered)
