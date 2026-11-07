from copy import deepcopy
from pathlib import Path
import json

import pytest
from openpyxl import Workbook, load_workbook

from app.services.nonpayment_report_service import NonpaymentReportService as N, detect_nonpayment
from app.services.batch_report_service import BatchReportService as B
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.relation_service import RelationService


def item(text, **extra):
    return {'file_name':'sample.wav','path':'sample.wav','status':'completado',
            'result':{'archivo':'sample.wav','texto':text,'duracion_segundos':120,'segmentos':[]},
            'relation':{'archivo_original':'sample.wav','gestor':'Asesor','supervisor':'Supervisor',
                        'numero_de_tarjeta':'0123456789012345','asignacion':'1PV'}, **extra}


@pytest.mark.parametrize('text,reason',[
    ('Titular: Me quedé sin trabajo.', 'DESEMPLEO'),
    ('Tuve un accidente.', 'SALUD_O_ACCIDENTE'),
    ('No reconozco esa deuda.', 'DESCONOCE_O_DISPUTA_ADEUDO'),
    ('No me recibieron el pago.', 'IMPEDIMENTO_PARA_PAGAR'),
    ('Me pagan hasta el viernes.', 'ESPERA_INGRESO_O_QUINCENA'),
    ('No me alcanza.', 'INGRESOS_INSUFICIENTES'),
    ('No tengo dinero.', 'FALTA_DE_LIQUIDEZ'),
    ('Se me olvidó pagar.', 'OLVIDO_DE_PAGO'),
    ('No voy a pagar.', 'NEGATIVA_EXPRESA'),
    ('Ya pagué.', 'PAGO_YA_REPORTADO'),
    ('Lo realicé desde ayer.', 'PAGO_YA_REPORTADO'),
    ('Voy a pagar mañana.', 'SIN_MOTIVO_IDENTIFICADO'),
    ('Gestor: No tengo dinero.', 'SIN_MOTIVO_IDENTIFICADO'),
    ('¿No tengo dinero?', 'SIN_MOTIVO_IDENTIFICADO'),
    ('No estoy desempleado.', 'SIN_MOTIVO_IDENTIFICADO'),
    ('Nunca me quedé sin trabajo.', 'SIN_MOTIVO_IDENTIFICADO'),
    ('No es cierto que no tengo dinero.', 'SIN_MOTIVO_IDENTIFICADO'),
])
def test_reasons_come_from_declarations_not_questions_or_proposals(text, reason):
    assert detect_nonpayment(item(text))['primary']==reason


def test_multiple_reasons_do_not_double_count_primary_and_preserve_evidence():
    a=detect_nonpayment(item('Tuve un accidente. No tengo dinero. Ya pagué.'))
    assert a['primary']=='SALUD_O_ACCIDENTE'
    assert a['secondary']==['FALTA_DE_LIQUIDEZ','PAGO_YA_REPORTADO']
    assert len(a['evidence'])==3


def test_absent_holder_never_inherits_third_partys_finances():
    a=item('Tercero: Soy su madre. No tengo dinero.',
           analytics_metadata={'quality_contact_type':'TERCERO / FAMILIAR'})
    assert detect_nonpayment(a)['primary']=='CONTACTO_CON_TERCERO_SIN_MOTIVO_DEL_TITULAR'


def test_report_totals_keep_each_call_once_and_preserve_original_text_cards(tmp_path):
    a=item('No tengo dinero.'); b=item('Tuve un accidente. No tengo dinero.')
    b['file_name']='other.wav';b['path']='other.wav'
    a['relation']['datos_excel_original']={'Cliente':'=SAMPLE()','Tarjeta':'0123456789012345','Campo extra':'dato original'}
    original=deepcopy([a,b]); quality=tmp_path/'Reporte_Analisis_Audios_20261105_100000.xlsx'
    path=N.generate_report([a,b],quality)
    assert [a,b]==original
    w=load_workbook(path,data_only=False)
    s=w['RESUMEN_MOTIVOS']; assert s.cell(s.max_row,2).value==2
    d=w['DETALLE_LLAMADAS'];h=[c.value for c in d[1]]
    card=d.cell(2,h.index('Excel: numero_de_tarjeta')+1)
    assert card.value=='0123456789012345' and card.data_type=='s'
    raw=w['DATOS_EXCEL'];headers=[c.value for c in raw[1]]
    assert raw.cell(2,headers.index('Campo extra')+1).value=='dato original'
    formula=raw.cell(2,headers.index('Cliente')+1)
    assert formula.value=='=SAMPLE()' and formula.data_type=='s'
    assert not any(c.data_type=='f' for s in w for row in s for c in row)
    w.close()


def test_reanalysis_generates_both_reports_without_changing_checkpoint(tmp_path):
    p=tmp_path/'source.json';p.write_text(json.dumps({'items':[item('Habla MRS. Soy yo. No tengo dinero.')]}))
    original=p.read_bytes();out=reanalyze_checkpoint(p,tmp_path/'new')
    assert Path(out['report']).exists() and Path(out['nonpayment_report']).exists()
    assert p.read_bytes()==original
    payload=json.loads(Path(out['checkpoint']).read_text())
    assert payload['last_nonpayment_report_path']==out['nonpayment_report']
    assert payload['nonpayment_report_error'] is None


def test_additional_report_failure_keeps_quality_report_with_visible_error(tmp_path,monkeypatch):
    def fail(*a,**kw): raise PermissionError('Archivo abierto')
    monkeypatch.setattr(N,'generate_report',fail)
    path=B.generate_report([item('No tengo dinero.')],tmp_path/'02_Audios/Transcripciones')
    assert Path(path).exists()
    status=N.report_status(path)
    assert not status['path'] and status['error']=='Archivo abierto'


def test_partial_report_does_not_generate_final_nonpayment_report(tmp_path,monkeypatch):
    def fail(*a,**kw): pytest.fail('El reporte adicional solo se genera al final')
    monkeypatch.setattr(N,'generate_report',fail)
    assert Path(B.generate_partial_report([item('No tengo dinero.')],tmp_path/'02_Audios/Transcripciones')).exists()


def test_relation_import_keeps_original_columns_by_same_audio(tmp_path):
    w=Workbook();s=w.active;s.title='Relacion_Audios'
    s.append(['archivo_original','gestor','estatus_grabacion','nombre_final','numero_de_tarjeta','Dato extra'])
    s.append(['sample.wav','Asesor','CONVENIO','sample_final','0123456789012345','dato'])
    p=tmp_path/'relation.xlsx';w.save(p);w.close()
    service=RelationService();result=service.load_excel(p)
    assert result['total_registros']==1
    data=service.records[0].to_dict()
    assert data['datos_excel_original']['Dato extra']=='dato'
    assert data['datos_excel_original']['numero_de_tarjeta']=='0123456789012345'


def test_ui_opens_companion_of_the_selected_report_without_a_display(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from app.ui.views.batch_view import BatchView
    import os
    opened=[]
    monkeypatch.setattr(os,'startfile',lambda p:opened.append(p),raising=False)
    quality=B.generate_report([item('No tengo dinero.')],tmp_path/'02_Audios/Transcripciones')
    BatchView.open_nonpayment_report(SimpleNamespace(last_report_path=quality))
    assert opened==[str(N.companion_path(quality))]


def test_ui_does_not_open_a_stale_companion_for_an_old_quality_report(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from app.ui.views.batch_view import BatchView
    from tkinter import messagebox
    import os
    warnings=[]
    monkeypatch.setattr(os,'startfile',lambda p:pytest.fail('No abrir un archivo no vinculado'),raising=False)
    monkeypatch.setattr(messagebox,'showwarning',lambda *a:warnings.append(a))
    quality=tmp_path/'old.xlsx';w=Workbook();w.save(quality);w.close()
    N.generate_report([item('No tengo dinero.')],quality)
    BatchView.open_nonpayment_report(SimpleNamespace(last_report_path=str(quality)))
    assert warnings
