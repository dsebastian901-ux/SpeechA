"""Distingue la versión del programa de la versión que dictaminó cada audio.

Reanudar un lote no reevalúa automáticamente audios ya completados. Nunca
presentar todos sus resultados antiguos como si fueran del motor nuevo.
"""
from collections import Counter


def summarize_result_revisions(items, current_engine):
    revisions = Counter()
    previous = 0
    unknown = 0
    processed = 0
    for item in items or ():
        if item.get("status") != "completado":
            continue
        processed += 1
        stored = item.get("analytics_metadata") or (item.get("analytics") or {}).get("metadata") or {}
        revision = str(stored.get("engine_revision") or "SIN_VERSION")
        revisions[revision] += 1
        if revision == "SIN_VERSION":
            unknown += 1
        elif revision != current_engine:
            previous += 1
    return {
        "processed": processed,
        "revisions": dict(revisions),
        "previous_engine_results": previous,
        "unknown_engine_results": unknown,
        "requires_explicit_reanalysis": bool(previous or unknown),
    }
