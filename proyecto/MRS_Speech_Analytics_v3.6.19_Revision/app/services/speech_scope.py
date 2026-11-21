"""Ámbito textual local: separar una afirmación actual de cita/negación/hipótesis.

No identifica voces ni convierte una hipótesis en infracción confirmada.
"""
import re

CURRENT = re.compile(r'\b(?:pero ahora|ahora (?:yo |le |les )?(?:confirmo|confirmamos|indico|solicito|pido)|sin embargo ahora)\b')
REPORTED = re.compile(r'\b(?:me dijeron|me dijo|me indicaron|usted me dijo|usted dijo|usted dice|dice|dijo|dijeron|diga|repita|me amenazo) que\b|\ben la llamada anterior\b|\bantes pensaba que\b')
HYPOTHETICAL = re.compile(r'\b(?:si (?:fuera|fuese|tuviera|tuviese|pudiera|pudiese)|en caso de|supongamos(?: que)?|por ejemplo)\b')
NEGATED = re.compile(r'\b(?:no|nunca|jamas)(?: (?:se|le|les|lo|la))?\s*$|\bno (?:es|seria) (?:cierto|verdad) que\s*$')


def local_prefix(text, position):
    """El punto/coma de importes no es un separador de cláusula."""
    prefix=text[:position]
    starts=[0]
    starts.extend(m.end() for m in re.finditer(r'[;!?]|\.(?=\s|$)',prefix))
    starts.extend(m.start() for m in CURRENT.finditer(prefix))
    return prefix[max(starts):]


def nonassertive_prefix(text, position):
    prefix=local_prefix(text,position)
    return bool(REPORTED.search(prefix) or HYPOTHETICAL.search(prefix) or NEGATED.search(prefix))
