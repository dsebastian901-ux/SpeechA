"""Aviso genérico autorizado; conserva importes y mora detallada.

Decisión de la usuaria: «Sí, permitir el aviso genérico» (15/nov/2026).
No modifica el ASR ni convierte una confirmación humana en falsa.
"""
import re


def generic_arrears_match(phrase):
    from app.services.conversation_evidence import normalize
    value=normalize(phrase)
    if re.search(r'\bcubrir\b',value):return False  # Solicitud de cobro, no aviso genérico.
    if 'atraso' not in value and value!='por la trazo de su tarjeta':return False
    # El fragmento puede contener una cifra de mora, meses o mensualidades:
    # esos hechos siguen protegidos aunque incluyan la palabra «atraso».
    return not re.search(r'\d|\b(?:mes|meses|anos?|mens(?:u)?alidades?|deuda|adeudo|importe|monto|pesos|saldo)\b',value)


def mask_generic_arrears_for_legacy(text):
    """Ámbito exclusivo de detectores antiguos de palabras; nunca se exporta."""
    return re.sub(r'\batraso\b',lambda m:' '*len(m.group()),text)
