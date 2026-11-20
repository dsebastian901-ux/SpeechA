"""El dashboard y sus copias deben respetar el resultado, no solo el puntaje."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.ui.views.dashboard_view import DashboardView as D


def project(tmp_path, category, *, mismatch=False):
    path=tmp_path/'05_Datos/batch_state/batch_checkpoint.json'
    path.parent.mkdir(parents=True)
    item={'status':'completado','file_name':'sintetico.ogg',
        'classification':{'clasificacion':category},
        'analytics':{'compliance_score':100,'compliance_status':'cumple','metadata':{
            'status_validation':{'valid':not mismatch}}}}
    path.write_text(json.dumps({'items':[item]}),encoding='utf-8')
    return D._load_operational_dashboard(tmp_path)


@pytest.mark.parametrize('category,label',[
    ('NO_APROBADO','NO APROBADO'),('ERROR','ERROR DE PROCESAMIENTO'),
    ('SIN_RELACION_EXCEL','SIN RELACIÓN EXCEL'),
])
def test_known_outcomes_do_not_fall_back_to_review(tmp_path,category,label):
    row=project(tmp_path,category)['records'][0]
    assert row['operational_class']==label
    assert row['final_status']==category


@pytest.mark.parametrize('category',['REVISAR','FALLA_GRAVE','APROBADO_ETIQUETA_CORREGIDA'])
def test_status_discrepancy_and_high_score_do_not_replace_saved_outcome(tmp_path,category):
    row=project(tmp_path,category,mismatch=True)['records'][0]
    assert row['final_status']==category


def test_old_standalone_score_does_not_invent_an_approval(tmp_path):
    directory=tmp_path/'04_Reportes/Analytics';directory.mkdir(parents=True)
    (directory/'synthetic_analytics.json').write_text(json.dumps({
        'audio_file':'sintetico.ogg','compliance_score':100,'metadata':{}}))
    row=D._load_standalone_analytics(tmp_path)['records'][0]
    assert row['final_status']=='SIN_DICTAMEN'
    assert row['operational_class']=='SIN DICTAMEN'


def test_audit_folder_selection_uses_saved_result_instead_of_score_band(tmp_path,monkeypatch):
    import app.ui.views.dashboard_view as module
    monkeypatch.setattr(module.messagebox,'showinfo',lambda *a,**k:None)
    monkeypatch.setattr(module.messagebox,'showerror',lambda *a,**k:pytest.fail(str(a)))
    rows=[{'file_name':c+'.ogg','final_status':c,'score':100}
          for c in ['APROBADO','REVISAR','NO_APROBADO','FALLA_GRAVE']]
    selected=[]
    def copies(batch,out,**kwargs):
        selected.append((Path(out).name,[r['final_status']for r in batch]))
        return {'copied':len(batch),'missing':0,'errors':[]}
    fake=SimpleNamespace(_audit_records=lambda:rows,_audit_output_root=lambda:tmp_path,
                         _copy_rows_and_index=copies)
    D._generate_final_folders(fake)
    assert sorted(c for _,group in selected for c in group)==sorted(r['final_status']for r in rows)
    assert all(len(group)==1 for _,group in selected if group)
