"""Integridad de copias e índices del dashboard con datos sintéticos."""
from pathlib import Path
from types import SimpleNamespace

from openpyxl import load_workbook
from app.ui.views.dashboard_view import DashboardView as D


def test_dashboard_copies_do_not_overwrite_equal_names(tmp_path):
    a=tmp_path/'a'/'sintetico.ogg';b=tmp_path/'b'/'sintetico.ogg'
    for file,content in [(a,b'primera llamada'),(b,b'segunda llamada')]:
        file.parent.mkdir();file.write_bytes(content)
    view=SimpleNamespace(_resolve_audio_source=lambda row:Path(row['path']),
                         _write_audit_excel=lambda *a,**kw:None)
    out=tmp_path/'out'
    result=D._copy_rows_and_index(view,[{'path':str(a)},{'path':str(b)}],out,quiet=True)
    assert result['copied']==2 and not result['errors']
    assert sorted(p.read_bytes()for p in out.rglob('*.ogg'))==sorted([a.read_bytes(),b.read_bytes()])


def test_dashboard_index_preserves_formula_like_strings_as_text(tmp_path):
    target=tmp_path/'index.xlsx'
    D._write_audit_excel(SimpleNamespace(_last_word_query=''),[
        {'file_name':'=1+1','gestor':'=2+2','score':100,'final_status':'REVISAR'}],target)
    book=load_workbook(target,data_only=False)
    try:
        assert book.active['A2'].value=='=1+1'
        assert book.active['A2'].data_type=='s'
        assert not any(c.data_type=='f'for sheet in book for row in sheet for c in row)
    finally:book.close()


def test_consolidation_does_not_reopen_an_explicitly_validated_exception(tmp_path):
    from test_consolidated_reports import call,checkpoint
    from app.services.consolidated_report_service import ConsolidatedReportService as C
    item=call(1)
    item['classification']={'clasificacion':'APROBADO_CON_EXCEPCION','decision_findings':[
        {'code':'OFFENSIVE_LANGUAGE','severity':'VALIDATED_EXCEPTION','rule_group':9,'reasons':['Excepción validada']}]}
    item['analytics_metadata']['penalties']=[
        {'id':'PEN_GROSERIA_SIN_ATRIBUCION','points':0,'invalidates':False,'reason':'Código conservado'}]
    row=C.load([checkpoint(tmp_path,'one',[item])])['calls'][0]
    assert not row['errors']
    assert not row.get('pending_observations')
