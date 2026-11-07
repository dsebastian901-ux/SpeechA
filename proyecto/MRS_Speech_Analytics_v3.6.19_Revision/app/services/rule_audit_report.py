"""Detalle y resumen de los trece grupos, con una fila por llamada y grupo."""
from collections import Counter
from app.services.quality_decision import RULES


def add_rule_audit_sheets(workbook, items):
    detail = workbook.create_sheet('EVALUACION_13_REGLAS')
    detail.append(['Llamada','Archivo original','Gestor','Supervisor','Fecha llamada',
                   'Tarjeta (últimos 4)','Grupo','Regla','Resultado','Motivos','Evidencia'])
    counts = Counter()
    for number, item in enumerate(items,1):
        relation = item.get('relation') or {}
        metadata = item.get('analytics_metadata') or (item.get('analytics') or {}).get('metadata') or {}
        decision = item.get('classification') or {}
        if not decision.get('rule_evaluation'):
            decision = metadata.get('shared_classification') or {}
        evaluations = {row['id']:row for row in decision.get('rule_evaluation',[])}
        findings = decision.get('decision_findings') or []
        for group, label in RULES:
            evaluation = evaluations.get(group) or {'state':'NO_EVALUADO'}
            matching = [f for f in findings if f['rule_group']==group]
            reasons = list(dict.fromkeys(r for f in matching for r in f['reasons']))
            evidence = []
            for finding in matching:
                value = metadata.get(finding['source_field']) or {}
                if isinstance(value,dict):
                    text = value.get('evidence') or value.get('reason')
                    if isinstance(text,str) and text:
                        evidence.append(text)
            if group==4:
                evidence.append((metadata.get('contact_validation') or {}).get('evidence') or '')
            if group==12:
                n=metadata.get('negotiation_validation') or {}
                evidence.extend([n.get('evidencia_monto') or '',n.get('promise_date_evidence') or ''])
            row = [number,item.get('file_name') or item.get('path') or '',relation.get('gestor') or '',
                   relation.get('supervisor') or '',str(relation.get('fecha') or ''),
                   str(relation.get('numero_de_tarjeta') or '')[-4:],group,label,evaluation['state'],
                   ' | '.join(reasons),' | '.join(dict.fromkeys(t for t in evidence if t))]
            detail.append(row)
            counts[group,evaluation['state']] += 1
    summary = workbook.create_sheet('RESUMEN_13_REGLAS')
    states = ['SIN_HALLAZGOS','DESCUENTO_APLICADO','REQUIERE_REVISION','INCUMPLIMIENTO_CRITICO',
              'EXCEPCION_VALIDADA','ETIQUETA_CORREGIDA','NO_APLICA','NO_EVALUADO']
    summary.append(['Grupo','Regla','Total llamadas',*states])
    for group,label in RULES:
        summary.append([group,label,len(items),*[counts[group,state] for state in states]])
    for sheet in (detail,summary):
        sheet.freeze_panes='C2';sheet.auto_filter.ref=sheet.dimensions
        for row in sheet:
            for cell in row:
                if isinstance(cell.value,str):
                    cell.data_type='s'
        for column,width in [('A',12),('B',64),('C',25),('D',25),('E',22),('F',21),('H',32),('I',30),('J',85),('K',95)]:
            sheet.column_dimensions[column].width=width
    return detail,summary
