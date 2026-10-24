"""Detección conservadora de posibles referencias de tarjeta dictadas por grupos.
Las coincidencias ASR se envían a revisión; no se confirman como fraude.
"""
import re
import unicodedata

TENS = {"veinte":20,"treinta":30,"cuarenta":40,"cincuenta":50,"sesenta":60,"setenta":70,"ochenta":80,"noventa":90}
ONES = {"cero":0,"uno":1,"un":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9}
SMALL = {"diez":10,"once":11,"doce":12,"trece":13,"catorce":14,"quince":15,"dieciseis":16,"diecisiete":17,"dieciocho":18,"diecinueve":19}

def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFD",str(text).lower()) if unicodedata.category(c)!="Mn")

def _number(token):
    token=token.strip().replace("  "," ")
    if re.fullmatch(r"\d{1,2}",token):return token.zfill(2)
    if token in ONES:return str(ONES[token]).zfill(2)
    if token in SMALL:return str(SMALL[token]).zfill(2)
    if token in TENS:return str(TENS[token]).zfill(2)
    if token.startswith("veinti") and token[6:] in ONES:return str(20+ONES[token[6:]]).zfill(2)
    m=re.fullmatch(r"(veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa) y (uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)",token)
    if m:return str(TENS[m[1]]+ONES[m[2]]).zfill(2)
    return None

WORDS=sorted(set(ONES)|set(SMALL)|set(TENS),key=len,reverse=True)
TOKEN=re.compile(r"(?<!\w)(?:\d{1,19}|veinti(?:uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)|(?:veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa) y (?:uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)|"+"|".join(WORDS)+r")(?!\w)")
CONTEXT=re.compile(r"(?:referencia(?: de pago)?|numeros? de (?:la |su )?tarjeta|(?:los |sus )?(?:16|dieciseis) digitos(?: de (?:la |su )?tarjeta)?|tarjeta|dictar(?:e|le)? (?:la |el )?(?:referencia|numero)|numero (?:para|con el que) pagar)")
STOP=re.compile(r"\b(?:whatsapp|comprobante|saldo|pesos|bancos|establecimientos|telefon[oa]|celular|fecha|monto|importe)\b")
SEPARATOR=re.compile(r"^(?:[\W_]|\b(?:aja|si|correcto|ok|bien)\b)*$")


def _digits(token):
    if token.isdigit():
        return token
    if token in ONES:
        return str(ONES[token])
    return _number(token)


def find_reference(text, expected=''):
    """Extraer una dictación completa, sin ventanas móviles ni ceros inventados.

    Las repeticiones de pares y las dictaciones incompletas son ambiguas; no
    se comparan fragmentos fabricados con la tarjeta de Excel. Una discrepancia
    de transcripción exige revisión, no confirma fraude ni verificación acústica.
    """
    s=normalize(text)
    expected=re.sub(r"\D", "", str(expected or ""))
    found, ambiguous = [], []
    for ctx in CONTEXT.finditer(s):
        sub=s[ctx.end():ctx.end()+420]
        matches=list(TOKEN.finditer(sub))
        if not matches or matches[0].start()>95 or STOP.search(sub[:matches[0].start()]):
            continue
        group=[matches[0]]
        for match in matches[1:]:
            gap=sub[group[-1].end():match.start()]
            if not SEPARATOR.fullmatch(gap):
                break
            group.append(match)
        # No confundir un teléfono, fecha o importe posterior con referencia.
        tail=sub[group[-1].end():group[-1].end()+35]
        if re.match(r"^[\W_]*(?:pesos|telefono|celular|por ciento)\b", tail):
            continue
        parts=[_digits(m.group()) for m in group]
        if any(part is None for part in parts):
            continue
        digits="".join(parts)
        evidence=sub[group[0].start():group[-1].end()]
        record={"digits":digits, "evidence":evidence, "context":ctx.group()}
        if len(digits)==32 and digits[:16]==digits[16:]:
            record["digits"]=digits[:16]  # Repetición completa, no pares adivinados.
            found.append(record)
        elif len(digits)==16:
            found.append(record)
        elif len(digits)>=8:
            record["reason"]="Dictación incompleta, repetida o de longitud distinta de 16; revisar audio."
            ambiguous.append(record)
    unique={v["digits"]:v for v in found}
    wrong=[v for v in unique.values() if len(expected)==16 and v["digits"]!=expected]
    return {"detected":list(unique.values()), "incorrect":wrong,
            "ambiguous":ambiguous, "expected":expected,
            "requires_review":bool(wrong or ambiguous or (found and len(expected)!=16))}
