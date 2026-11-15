"""Una definición compartida para copias, estadísticas y reportes."""
APPROVED_RESULTS=frozenset({'APROBADO','APROBADOS','APROBADO_ETIQUETA_CORREGIDA','APROBADO_DURACION_MENOR'})
SHORT_APPROVAL_FOLDER='APROBADAS_DURACION_MENOR'


def corrected_approval(decision):
    return (decision.get('clasificacion')in{'APROBADO_ETIQUETA_CORREGIDA','APROBADO_DURACION_MENOR'}
            and decision.get('aprobado')is True and (decision.get('output_label_correction')or{}).get('valid')is True)
