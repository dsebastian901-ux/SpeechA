"""Ámbito textual local: separar una afirmación actual de cita/negación/hipótesis.

No identifica voces ni convierte una hipótesis en infracción confirmada.
"""
import re

CURRENT = re.compile(r'\b(?:pero ahora|ahora (?:yo |le |les )?(?:confirmo|confirmamos|indico|solicito|pido)|sin embargo ahora)\b')
REPORTED = re.compile(r'\b(?:me dijeron|me dijo|me indicaron|usted me dijo|usted dijo|usted dice|dice|dijo|dijeron|diga|repita|me amenazo) que\b|\ben la llamada anterior\b|\bantes pensaba que\b|'
    r'\b(?:indique|mencione|repita)\b|\bque (?:se me |usted |el cliente )?(?:diga|dijera)\b')
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


def personal_family_background(text, start, end):
    """«Soy madre soltera» describe a quien habla, no parentesco con el titular.

    «Soy su madre» y «soy madre del titular» conservan su significado de
    intermediario. Este ámbito se comparte entre identidad y parentesco.
    """
    declaration=text[start:end]
    background=bool(re.search(r'\bsoy (?:madre|padre|hija|hijo)\b',declaration)
        and not re.search(r'\bsu\b',declaration)
        and re.match(r'\s+(?:solter[oa]|de familia|de (?:dos|tres|cuatro|\d+) hijos|unic[oa])\b',text[end:]))
    context=text[max(0,start-120):end+120]
    helper=bool(re.search(r'\bes mi (?:hij[oa]|espos[oa]|herman[oa]|madre|padre)\b',declaration)
        and re.search(r'\bmi (?:tarjeta|cuenta|pago)\b',context)
        and (re.match(r'\s+(?:quien|el que|la que) me (?:ayuda|apoya)\b',text[end:])
             or re.search(r'\bquien me (?:ayuda|apoya)\s*$',text[max(0,start-60):start])))
    return background or helper


def conditional_yes_reply(text):
    """«Si lo dividimos…» plantea una condición; no es «sí, acepto»."""
    return bool(re.match(r'si\s+(?:(?:lo|la|le|les|se)\s+)?'
        r'(?:dividimos|dividiera|pudiera|tuviera|fuera|consigue|gusta|quiere|realiza|paga)\b',text))
