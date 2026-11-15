"""Alertas que permanecen abiertas en una llamada rechazada por otro motivo."""
from pathlib import Path
import json
import re
from xml.sax.saxutils import escape
from zipfile import ZipFile,ZIP_DEFLATED
from app.services.pending_review_report import _evidence,ACTIONS


def pending_alert_rows(items):
    rows=[]
    for n,item in enumerate(items,1):
        decision=item.get('classification')or{};m=item.get('analytics_metadata')or{};rel=item.get('relation')or{}
        for alert in decision.get('pending_alerts')or[]:
            rows.append({'call':n,'audio':item.get('file_name',''),'date':str(rel.get('fecha')or''),
                'card':str(rel.get('numero_de_tarjeta')or''),'agent':rel.get('gestor')or'',
                'supervisor':rel.get('supervisor')or'','result':decision.get('clasificacion')or'',
                'code':alert['code'],'priority':'PRIORITARIA'if alert['rule_group']in{3,5,8,9,11,12}else'VALIDAR CONTEXTO',
                'reason':' | '.join(alert.get('reasons')or[]),'evidence':_evidence(m.get(alert.get('source_field'),{})),
                'action':ACTIONS.get(alert['code'],('','Cotejar el hecho y conservar el rechazo hasta resolver la alerta.'))[1]})
    return rows


def add_pending_alert_sheet(workbook,items):
    sheet=workbook.create_sheet('ALERTAS_PENDIENTES')
    sheet.append(['Llamada','Audio','Fecha','Tarjeta Excel','Gestor','Supervisor','Resultado de calidad',
                  'Alerta sin confirmar','Prioridad','Motivo','Fragmentos y tiempos','Acción'])
    for r in pending_alert_rows(items):
        sheet.append([r['call'],r['audio'],r['date'],r['card'],r['agent'],r['supervisor'],r['result'],
            r['code'],r['priority'],r['reason'],json.dumps(r['evidence'],ensure_ascii=False),r['action']])
    for row in sheet:
        for cell in row:
            if isinstance(cell.value,str):cell.data_type='s'
    return sheet


def write_pending_alerts_word(items,quality_report):
    rows=pending_alert_rows(items)
    if not rows:return None
    path=Path(quality_report);target=path.with_name('Alertas_Pendientes_'+path.stem+'.docx')
    paragraphs=[]
    def p(value,bold=False):
        clean=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',str(value))
        paragraphs.append('<w:p><w:r>'+('<w:rPr><w:b/></w:rPr>'if bold else'')+
            '<w:t xml:space="preserve">'+escape(clean)+'</w:t></w:r></w:p>')
    p('Alertas pendientes en llamadas no aprobadas',True)
    p('El incumplimiento comprobado determina el rechazo de calidad. Las alertas siguientes siguen sin confirmar y requieren seguimiento; no se registran como faltas graves confirmadas.')
    for r in rows:
        p(f"Llamada {r['call']}: {r['audio']}",True)
        p(f"Fecha: {r['date']}; tarjeta: {r['card']}; gestor: {r['agent']}; supervisor: {r['supervisor']}.")
        p(r['result']+' — '+r['priority']+' — '+r['code'])
        p(r['reason']);p('Acción: '+r['action'])
        for evidence in r['evidence']:
            timing=(f"[{evidence.get('start')}–{evidence.get('end')} s] "if evidence.get('start')is not None else'[Sin tiempo exacto] ')
            p(timing+evidence['text'])
    document=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+
        ''.join(paragraphs)+'<w:sectPr/></w:body></w:document>')
    content_types=('<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    relationships=('<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    temporary=target.with_name(target.stem+'_nuevo.docx')
    with ZipFile(temporary,'w',ZIP_DEFLATED)as z:
        z.writestr('[Content_Types].xml',content_types);z.writestr('_rels/.rels',relationships);z.writestr('word/document.xml',document)
    temporary.replace(target)
    return str(target)
