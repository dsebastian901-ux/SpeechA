"""Detalle local de lecturas: audio/huellas y hechos, sin duplicar ficha personal."""
import json

HEADERS = ['Archivo', 'Huella audio SHA256', 'Motor de lectura', 'Validador', 'Modelo',
           'Motivo de relectura', 'Objetivo', 'Lectura', 'Inicio', 'Fin', 'Texto',
           'Error técnico', 'Calidad acústica', 'Regla', 'Estado de evidencia',
           'Motivo de consenso', 'Atribución', 'Evidencia coincidente',
           'Evidencia contradictoria', 'Bloqueo', 'Códigos resueltos',
           'Bloqueos conservados', 'Clasificación anterior', 'Clasificación nueva',
           'Justificación', 'Fuentes independientes']


def trace_rows(item):
    metadata=item.get('analytics_metadata')or{}
    context=metadata.get('context_audio_validation')or{}
    record=item.get('context_asr_recovery')or{}
    classification=item.get('classification')or{}
    if not context.get('present'):return []
    rows=[]
    groups=record.get('groups')or[{}]
    for group in groups:
        purpose=group.get('purpose','')
        semantic=next((g for g in context.get('fact_validations',[])if g['purpose']==purpose),{})
        rules=semantic.get('rules')or[{}]
        for index,attempt in enumerate(group.get('attempts')or[{}],1):
            for rule in rules:
                quality=semantic.get('acoustic_quality')or[]
                rows.append(dict(zip(HEADERS,[
                    record.get('audio_file')or item.get('file_name',''), record.get('audio_sha256',''),
                    record.get('engine_revision','NO_REGISTRADO'),context.get('validator_revision',''),
                    record.get('model',''), ', '.join(record.get('recovery_reasons')or[]),
                    purpose,index,attempt.get('start'),attempt.get('end'),attempt.get('text',''),
                    attempt.get('error',''),quality[index-1]if len(quality)>=index else 'NO_VERIFICADA',
                    rule.get('rule',''),rule.get('state','EVIDENCIA_INSUFICIENTE'),
                    rule.get('reason_code')or context.get('reason',''),
                    rule.get('speaker_attribution','NO_ACREDITADA'),
                    json.dumps(rule.get('matching_evidence',[]),ensure_ascii=False),
                    json.dumps(rule.get('contradictory_evidence',[]),ensure_ascii=False),
                    rule.get('blocking_effect','CONSERVADO'if not context.get('valid')else ''),
                    ', '.join(rule.get('resolves_codes',[])),
                    ', '.join(context.get('remaining_blocking_codes',[])),
                    record.get('classification_before')or context.get('classification_before','NO_REGISTRADA'),
                    classification.get('clasificacion')or context.get('classification_after',''),
                    classification.get('motivo')or context.get('decision_justification',''),1,
                ])))
    return rows


def add_context_recovery_sheet(workbook,items):
    sheet=workbook.create_sheet('EVIDENCIA_RELECTURAS')
    sheet.append(HEADERS)
    for item in items:
        for row in trace_rows(item):
            sheet.append([row.get(header,'')for header in HEADERS])
            for cell in sheet[sheet.max_row]:
                if isinstance(cell.value,str):cell.data_type='s'
    return sheet


def display_trace(item):
    """Misma fuente que Excel; textos completos, sin truncar tres lecturas."""
    return '\n\n'.join('\n'.join(f'{key}: {row[key]}'for key in HEADERS)
                       for row in trace_rows(item))or 'No hay relecturas registradas.'
