"""Postproceso conservador de artefactos Whisper en llamadas MRS.

No corrige identidades, cifras, tarjetas, insultos ni estatus. Solo elimina
repeticiones mecanicas largas y cierres ajenos al audio con evidencia temporal.
El texto original se conserva en el JSON/metadatos cuando hay un cambio.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Tuple


def _short_key(text: Any) -> str:
    value = unicodedata.normalize('NFKD', str(text or '').lower())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+', value))


def sanitize_asr_segments(segments: List[Dict[str, Any]], duration_seconds: float
                          ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Depura solo bucles ASR terminales inequívocos; conserva todo lo demás.

    No inventa hablantes ni completa texto. No suprime frases sustantivas aunque
    su timestamp sobrepase la duración: esa discrepancia queda documentada.
    """
    source = [dict(item) for item in (segments or []) if isinstance(item, dict)]
    try:
        duration = float(duration_seconds or 0)
    except (TypeError, ValueError):
        duration = 0.0
    max_end = max((float(s.get('fin') or 0) for s in source), default=0.0)
    overrun = round(max(0.0, max_end-duration), 3) if duration > 0 else 0.0
    removed: List[Dict[str, Any]] = []
    keep = [True] * len(source)

    # Whisper puede repetir «Hola» 20 veces tras una llamada de 80 s.
    # Intervenir solo con >=6 frases cortas idénticas consecutivas
    # que ocupen el tramo final; preservar dos y la evidencia original.
    if duration > 0 and len(source) >= 6:
        end = len(source)
        final_key = _short_key(source[-1].get('texto'))
        start = end - 1
        if final_key and len(final_key.split()) <= 4:
            while start > 0 and _short_key(source[start-1].get('texto')) == final_key:
                start -= 1
            if (end-start >= 6 and
                    float(source[start].get('inicio') or 0) >= max(0.0, duration-35.0)):
                for idx in range(start+2, end):
                    keep[idx] = False
                    removed.append({'id': source[idx].get('id'),
                                    'texto': str(source[idx].get('texto') or '')[:120],
                                    'motivo': 'BUCLE_ASR_TERMINAL'})

    # Cierre generico de video sospechoso solo al final y cruzando el fin.
    # Nunca filtrar despedidas, importes, insultos o negociaciones.
    if duration > 0 and source:
        last_idx = len(source)-1
        last = source[last_idx]
        phrase = _short_key(last.get('texto'))
        if (keep[last_idx] and phrase in {'suscribete', 'suscribanse',
                                         'gracias por ver este video'}
                and float(last.get('inicio') or 0) >= duration-2.5
                and float(last.get('fin') or 0) > duration+0.25):
            keep[last_idx] = False
            removed.append({'id': last.get('id'),
                            'texto': str(last.get('texto') or '')[:120],
                            'motivo': 'CIERRE_AJENO_AL_AUDIO'})

    result = [s for s, ok in zip(source, keep) if ok]
    diagnostic = {
        'schema': 1,
        'changed': bool(removed),
        'segments_removed': len(removed),
        'reasons': sorted({r['motivo'] for r in removed}),
        'removed_examples': removed[:4],
        'original_max_timestamp': round(max_end, 3),
        'duration_seconds': duration,
        'timestamp_overrun_seconds': overrun,
        'timestamp_warning': overrun > 0.75,
        'text_requires_audio_verification': bool(overrun > 0.75 and not removed),
        'policy': 'ONLY_CLEAR_TERMINAL_ASR_ARTIFACTS_V1',
    }
    return result, diagnostic
