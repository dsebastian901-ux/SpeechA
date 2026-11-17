from types import SimpleNamespace
import queue
from app.ui.views.consolidated_reports_dialog import ConsolidatedReportsDialog as D
from app.ui.views import consolidated_reports_dialog as module


class Value:
    def __init__(self,value):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value


class Control:
    def __init__(self):self.config={}
    def configure(self,**kwargs):self.config.update(kwargs)


def test_word_choices_follow_grave_report_not_other_report_types():
    view=SimpleNamespace(format=Value('Word'),format_menu=Control())
    D._family_changed(view,'Motivos de no pago')
    assert view.format.get()=='Excel'
    D._family_changed(view,'Fallas graves')
    assert view.format_menu.config['values']==['Excel','Word','Excel y Word']


def test_add_batches_preserves_count_each_batch_policy(monkeypatch):
    captured={}
    monkeypatch.setattr(module.filedialog,'askopenfilenames',lambda **kwargs:('new.json',))
    monkeypatch.setattr(module.Reports,'load',lambda paths,**kwargs:captured.update(paths=paths,options=kwargs))
    view=SimpleNamespace(busy=False,paths=['old.json'],_work=lambda operation,run:run())
    D._add(view)
    assert captured=={'paths':['old.json','new.json'],'options':{'deduplicate':False}}


def test_export_captures_filters_and_format_before_background_work(monkeypatch):
    captured={}
    monkeypatch.setattr(module.filedialog,'askdirectory',lambda **kwargs:'out')
    monkeypatch.setattr(module.Reports,'generate',lambda data,directory,**kwargs:captured.update(data=data,directory=directory,options=kwargs))
    view=SimpleNamespace(busy=False,dataset={'calls':[]},_work=lambda operation,run:run(),
        level=Value('Detallado'),family=Value('Fallas graves'),group=Value('Por supervisor'),
        gestor=Value('Ana'),supervisor=Value('Sup'),date_from=Value('01/11/2026'),date_to=Value('02/11/2026'),format=Value('Excel y Word'))
    D._generate(view)
    assert captured['options']=={'level':'DETALLADO','family':'GRAVES','group_by':'SUPERVISOR',
        'gestor':'Ana','supervisor':'Sup','date_from':'01/11/2026','date_to':'02/11/2026','formats':('xlsx','docx')}


def test_failed_load_keeps_previous_dataset_and_restores_controls(monkeypatch):
    original={'calls':[{'file':'previous'}]}
    messages=queue.Queue();messages.put(('load',None,'archivo inválido'))
    monkeypatch.setattr(module.messagebox,'showerror',lambda *a,**k:None)
    view=SimpleNamespace(messages=messages,busy=True,dataset=original,
        load_button=Control(),clear_button=Control(),generate_button=Control(),status=Control())
    D._poll(view)
    assert view.dataset is original and not view.busy
    assert view.generate_button.config['state']=='normal'
