"""Caché acotada a UNA evaluación, aislada entre hilos y liberada al terminar.

No reutiliza dictámenes, datos de otra cuenta ni transcripciones previas.
Solo evita volver a alinear las mismas frases al consultar cada regla.
"""
from contextvars import ContextVar
from functools import wraps

_CURRENT = ContextVar('mrs_conversation_cache', default=None)


def current_cache():
    return _CURRENT.get()


def evaluation_cache(function):
    @wraps(function)
    def evaluate(*args, **kwargs):
        token = _CURRENT.set({'normalization':{}, 'sentences':{}, 'roles':{}})
        try:
            return function(*args, **kwargs)
        finally:
            _CURRENT.reset(token)
    return evaluate
