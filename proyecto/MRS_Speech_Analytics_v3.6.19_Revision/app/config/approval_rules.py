"""Reglas configurables de aprobación operativa."""

# Un audio debe durar al menos este número de segundos para poder aprobarse.
MIN_APPROVAL_DURATION_SECONDS = 60.0

# None = sin límite máximo. Puede cambiarse posteriormente, por ejemplo 1200.0.
MAX_APPROVAL_DURATION_SECONDS = None

# Comportamiento si en el futuro se configura un máximo.
# "REVISAR" conserva el audio fuera de APROBADOS sin tratarlo como falla grave.
MAX_DURATION_ACTION = "REVISAR"
