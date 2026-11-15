"""Rechazo por puntaje independiente de dudas ordinarias de etiqueta/identidad."""

ORDINARY_PENALTIES={
    'PEN001','PEN_CONV_LUGARES','PEN_CONV_WHATSAPP','PEN007','PEN009','PEN_SIN_INTENTO_NEGOCIACION',
}


def ordinary_score_rejection(metadata, score, minimum_score, duration_seconds):
    """Resolver el rechazo ya determinado por el puntaje sin ocultar seguridad.

    Conserva toda observación pendiente. No confirma identidad, estatus, pago o
    voz. Las dudas independientes quedan como alertas visibles del rechazo,
    según la decisión operativa del 15/nov/2026.
    """
    if float(score or 0)>=float(minimum_score):return False
    penalties=[p for p in metadata.get('penalties') or []if float(p.get('points')or 0)>0]
    if not penalties or any(p.get('id') not in ORDINARY_PENALTIES for p in penalties):return False
    if not any(float(p.get('points') or 0)>0 for p in penalties):return False
    expected=max(0,100-sum(float(p.get('points') or 0) for p in penalties))
    if abs(expected-float(score or 0))>.01:return False
    if metadata.get('critical_failures'):return False
    # El puntaje insuficiente por reglas ordinarias ya determina rechazo.
    # Las otras dudas se exportan como alertas pendientes, nunca como permiso
    # para aprobar. La prioridad de faltas graves se aplica en evaluate_quality.
    return True
