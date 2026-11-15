"""Datos ausentes y cola de procesamiento separados de la calidad de llamadas."""


def add_data_diagnostics(workbook, items):
    sheet = workbook.create_sheet('RELACION_DATOS_ORIGEN')
    sheet.append(['Llamada en lote','Audio','Estado de procesamiento','Relación Excel',
                  'Resultado calculado','Acción'])
    for n,item in enumerate(items,1):
        missing=item.get('relation_status')=='sin_relacion'
        if not missing:
            continue
        sheet.append([n,item.get('file_name',''),item.get('status',''),'SIN RELACIÓN',
            (item.get('classification') or {}).get('clasificacion') or 'PENDIENTE',
            'Cotejar archivo_original e id_llamada con el Excel original. No completar tarjeta, gestor ni estatus desde la transcripción.'])
    sheet.freeze_panes='B2'
    sheet.auto_filter.ref=sheet.dimensions
    for row in sheet:
        for cell in row:
            if isinstance(cell.value,str):cell.data_type='s'
    return [sheet]
