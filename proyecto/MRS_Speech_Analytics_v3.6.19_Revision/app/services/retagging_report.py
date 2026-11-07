"""Cuentas y acciones para corregir el dictamen en la base del gestor."""
from collections import defaultdict
import json
from pathlib import Path

from openpyxl import load_workbook

HEADERS=['Llamada','Cuenta / tarjeta','Archivo original','Gestor','Supervisor','Fecha llamada',
         'Estatus Excel anterior','Estatus correcto','Código anterior','Código correcto',
         'Nombre antes de reetiquetar','Nombre de salida correcto','Puntaje','Motivo de corrección',
         'Corrección a realizar por el gestor','Estado de copia','Ruta de copia']


def add_retagging_sheets(workbook,items):
    sheet=workbook.create_sheet('CUENTAS_REETIQUETADAS');sheet.append(HEADERS)
    groups=defaultdict(list)
    for number,item in enumerate(items,1):
        decision=item.get('classification') or {}
        correction=decision.get('output_label_correction') or {}
        if decision.get('clasificacion')!='APROBADO_ETIQUETA_CORREGIDA' or not correction.get('valid'):
            continue
        r=item.get('relation') or {}
        path=str(item.get('classified_audio_path') or '')
        copied=bool(path and item.get('copy_status')=='copiado')
        sheet.append([number,str(r.get('numero_de_tarjeta') or ''),item.get('file_name') or '',
            r.get('gestor') or '',r.get('supervisor') or '',str(r.get('fecha') or ''),
            correction['original_status'],correction['corrected_status'],correction['original_code'],correction['corrected_code'],
            correction['original_name'],correction['corrected_name'],decision.get('score'),
            (item.get('analytics_metadata') or {}).get('status_validation',{}).get('evidence') or correction['reason'],
            'Corregir estatus_grabacion a '+correction['corrected_status']+' y usar código '+correction['corrected_code']+'.',
            'COPIA GENERADA' if copied else 'ETIQUETA CALCULADA; COPIA PENDIENTE',path if copied else ''])
        groups[r.get('gestor') or '',r.get('supervisor') or '',correction['original_status'],correction['corrected_status']].append(str(r.get('numero_de_tarjeta') or ''))
    summary=workbook.create_sheet('RESUMEN_REETIQUETADO')
    summary.append(['Gestor','Supervisor','Estatus anterior','Estatus correcto','Llamadas reetiquetadas','Cuentas distintas'])
    for key,cards in sorted(groups.items()):
        summary.append([*key,len(cards),len(set(cards))])
    for ws in (sheet,summary):
        ws.freeze_panes='D2';ws.auto_filter.ref=ws.dimensions
        for row in ws:
            for cell in row:
                if isinstance(cell.value,str):cell.data_type='s'
        for column,width in [('A',12),('B',25),('C',65),('D',25),('E',25),('F',24),('G',32),('H',32),
                             ('K',75),('L',75),('N',90),('O',80),('P',42),('Q',95)]:
            ws.column_dimensions[column].width=width
    return sheet,summary


def record_label_export(report_path,manifest_path):
    """Marcar copias reales solo después de comprobar el registro y sus archivos."""
    from app.services.corrected_label_export import file_digest
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))
    if manifest.get('completed') is not True or manifest.get('copied')!=len(manifest.get('calls',[])):
        raise ValueError('La copia de etiquetas no terminó; no se registra como completa.')
    calls={}
    for row in manifest['calls']:
        if row['file_name'] in calls:
            raise ValueError('Hay llamadas duplicadas en el registro de copias.')
        path=Path(row['destination'])
        if not path.is_file() or file_digest(path)!=row['audio_sha256']:
            raise ValueError('Falta una copia o cambió su contenido; no se marca como generada.')
        calls[row['file_name']]=row
    book=load_workbook(report_path)
    try:
        ws=book['CUENTAS_REETIQUETADAS']
        headers=[c.value for c in ws[1]]
        seen=set()
        for row in ws.iter_rows(min_row=2):
            name=row[headers.index('Archivo original')].value
            if name not in calls:continue
            record=calls[name]
            if row[headers.index('Nombre de salida correcto')].value!=record['label']['corrected_name']:
                raise ValueError('La etiqueta del reporte difiere de la copia generada.')
            row[headers.index('Estado de copia')].value='COPIA GENERADA'
            row[headers.index('Ruta de copia')].value=record['destination']
            seen.add(name)
        if seen!=set(calls):
            raise ValueError('El reporte no contiene todas las llamadas copiadas.')
        p=Path(report_path);temporary=p.with_name(p.stem+'_copias_nuevo.xlsx')
        book.save(temporary);temporary.replace(p)
    finally:
        book.close()
