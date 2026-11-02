"""Confirmación del usuario sobre una divulgación concreta; no diariza el ASR."""
from copy import deepcopy
from datetime import datetime, timezone
import re

from app.services.audio_block_evidence import binding, digest, validate_evidence
from app.services.conversation_evidence import assess_privacy, evidence_units

SCOPE = 'GESTOR_FINANCIAL_DISCLOSURE_TO_THIRD_PARTY_ONLY'


def disclosure_candidates(data, relation, audio_evidence=None):
    """Fragmentos financieros declarativos existentes, sin inventar texto o tiempos."""
    sources = [('ORIGINAL', data.get('texto', ''), data.get('segmentos') or [], binding(data, relation))]
    if audio_evidence is not None:
        status = validate_evidence(audio_evidence, data, relation, 'TERCERO')
        if status['valid'] and not status.get('quality', {}).get('degraded'):
            for label, text, segments in [
                ('ASR_ADICIONAL', 'text', 'segments'), ('CIERRE_ASR', 'tail_text', 'tail_segments')
            ]:
                sources.append((label, audio_evidence.get(text, ''), audio_evidence.get(segments) or [],
                                audio_evidence['record_sha256']))
    candidates = []
    for label, text, segments, source_hash in sources:
        for unit in evidence_units(text, segments):
            if unit['speaker_role'] not in {'GESTOR', 'NO DETERMINADO'}:
                continue
            # Esto selecciona contenido financiero; la voz y el destinatario
            # siguen sin confirmar hasta recibir las dos afirmaciones explícitas.
            probe = assess_privacy(unit['text'], [{'text': unit['text'], 'speaker_role': 'GESTOR'}],
                                   third_party_confirmed=True)
            if not probe['confirmed_disclosure']:
                continue
            candidate = {'source': label, 'source_hash': source_hash, 'text': unit['text'],
                         'start': unit['start'], 'end': unit['end']}
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def review_digest(record):
    return digest({k: record.get(k) for k in ('schema', 'scope', 'source_binding', 'evidence',
        'source', 'actor', 'recipient', 'actor_confirmed', 'third_party_confirmed', 'active')})


def make_disclosure_confirmation(data, relation, evidence, *, actor_confirmed=False,
                                 third_party_confirmed=False, audio_evidence=None):
    if actor_confirmed is not True or third_party_confirmed is not True:
        raise ValueError('Confirme explícitamente que el gestor divulgó la información a un tercero.')
    if (not isinstance(data, dict) or not data.get('archivo') or not str(data.get('texto') or '').strip()
            or not isinstance(relation, dict)
            or not re.fullmatch(r'\d{16}', str(relation.get('numero_de_tarjeta') or ''))):
        raise ValueError('Faltan transcripción o tarjeta de origen para vincular la confirmación.')
    if evidence not in disclosure_candidates(data, relation, audio_evidence):
        raise ValueError('El fragmento financiero no corresponde a la evidencia actual de esta llamada.')
    record = {'schema': 1, 'scope': SCOPE, 'source_binding': binding(data, relation),
              'evidence': deepcopy(evidence), 'source': 'EXPLICIT_USER_DISCLOSURE_CONFIRMATION',
              'actor': 'GESTOR', 'recipient': 'TERCERO', 'actor_confirmed': True,
              'third_party_confirmed': True, 'active': True,
              'reviewed_at': datetime.now(timezone.utc).isoformat()}
    record['record_sha256'] = review_digest(record)
    return record


def validate_disclosure_confirmation(data, relation, record, audio_evidence=None):
    status = {'present': record is not None, 'valid': False, 'review_required': False,
              'confirmed_disclosure': False, 'record': deepcopy(record)}
    if record is None:
        return status
    status.update(review_required=True,
                  reason='La confirmación de divulgación no corresponde a la evidencia actual; revisar o revocar.')
    try:
        expected = make_disclosure_confirmation(data, relation, record.get('evidence'),
            actor_confirmed=record.get('actor_confirmed'), third_party_confirmed=record.get('third_party_confirmed'),
            audio_evidence=audio_evidence)
        if (record.get('active') is not True or record.get('record_sha256') != review_digest(record)
                or any(record.get(k) != expected[k] for k in
                       ('schema', 'scope', 'source_binding', 'source', 'actor', 'recipient'))):
            return status
    except (ValueError, TypeError, AttributeError, KeyError):
        return status
    status.update(valid=True, review_required=False, confirmed_disclosure=True,
                  reason='Divulgación de información financiera por el gestor a un tercero, confirmada por el usuario.')
    return status
