"""Una definición compartida para copias, estadísticas y reportes."""
APPROVED_RESULTS=frozenset({'APROBADO','APROBADOS','APROBADO_ETIQUETA_CORREGIDA','APROBADO_DURACION_MENOR','APROBADO_CON_ALERTA'})
SHORT_APPROVAL_FOLDER='APROBADAS_DURACION_MENOR'
OPERATIONAL_FOLDERS = {
    'APROBADO_DURACION_MENOR':SHORT_APPROVAL_FOLDER,
    'APROBADO':'APROBADOS','APROBADOS':'APROBADOS',
    'APROBADO_ETIQUETA_CORREGIDA':'APROBADOS_ETIQUETA_CORREGIDA',
    'NO_APROBADO':'NO_APROBADOS','NO_APROBADO_MENOR_80':'NO_APROBADOS_MENOR_80',
    **{code:code for code in ['SIN_RELACION_EXCEL',
        'APROBADO_SIN_ETIQUETAR','APROBADO_CON_EXCEPCION','APROBADO_CON_ALERTA',
        'MAL_DICTAMINADO','NEGOCIACION_INVALIDA','FALLA_GRAVE','FALLA_MINIMA','SIN_VOZ','REVISAR']},
}


def operational_folder_name(classification):
    from app.services.grave_date_policy import grave_date_folder
    return grave_date_folder(classification)or OPERATIONAL_FOLDERS.get(
        str((classification or{}).get('clasificacion')or'').strip().upper(),'REVISAR')

# Son resultados guardados de calidad, distintos de las bandas del puntaje y
# del estatus de gestión del Excel. No deducir una aprobación a partir de 80.
OPERATIONAL_LABELS = {
    'APROBADO':'APROBADO','APROBADOS':'APROBADO',
    'APROBADO_ETIQUETA_CORREGIDA':'APROBADO CON ETIQUETA CORREGIDA',
    'APROBADO_DURACION_MENOR':'APROBADO - DURACIÓN MENOR',
    'APROBADO_SIN_ETIQUETAR':'APROBADO SIN ETIQUETAR',
    'APROBADO_CON_EXCEPCION':'APROBADO CON EXCEPCIÓN',
    'APROBADO_CON_ALERTA':'APROBADO CON ALERTA',
    'NO_APROBADO':'NO APROBADO','NO_APROBADO_MENOR_80':'MENOR A 80%',
    'FALLA_GRAVE':'FALLA GRAVE','REVISAR':'REVISAR',
    'FALLA_MINIMA':'FALLA MÍNIMA',
    'SIN_VOZ':'SIN VOZ',
    'ERROR':'ERROR DE PROCESAMIENTO','SIN_RELACION_EXCEL':'SIN RELACIÓN EXCEL',
    'MAL_DICTAMINADO':'MAL DICTAMINADO','NEGOCIACION_INVALIDA':'NEGOCIACIÓN INVÁLIDA',
    'SIN_DICTAMEN':'SIN DICTAMEN',
}


def saved_result(item):
    analytics = item.get('analytics') or {}
    metadata = item.get('analytics_metadata') or analytics.get('metadata') or {}
    decision = item.get('classification') or metadata.get('shared_classification') or {}
    category = str(decision.get('clasificacion') or metadata.get('final_result') or '').strip().upper()
    if category in OPERATIONAL_LABELS:
        return category
    return 'ERROR' if item.get('status') == 'error' else 'SIN_DICTAMEN'


def corrected_approval(decision):
    return (decision.get('clasificacion')in{'APROBADO_ETIQUETA_CORREGIDA','APROBADO_DURACION_MENOR','APROBADO_CON_ALERTA'}
            and decision.get('aprobado')is True and (decision.get('output_label_correction')or{}).get('valid')is True)


def corrected_label_exportable(decision):
    """Corregir el estatus es independiente de aprobar la calidad.

    Una llamada menor a 80 mantiene su carpeta de rechazo, pero la copia y
    los reportes deben mostrar el estatus realmente acreditado en el audio.
    Nunca usar este permiso de renombrado para revisar, fallas graves ni para
    eludir requisitos de evidencia del corrector de estatus.
    """
    classification=str(decision.get('clasificacion')or'').upper()
    correction=decision.get('output_label_correction')or{}
    if not correction.get('valid') or not correction.get('corrected_name'):
        return False
    return bool(corrected_approval(decision) or (
        classification=='NO_APROBADO_MENOR_80' and decision.get('aprobado')is False
        and float(decision.get('score')or 0)<float(decision.get('puntaje_minimo')or 80)))
