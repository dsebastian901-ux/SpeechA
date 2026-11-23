"""Controles de importación en GUI, con un trabajo simulado y cuentas sintéticas."""
import os,sys,time
import pytest
from test_individual_permissions_gui import gui,descendants
@pytest.fixture(autouse=True)
def supported_tk(gui):
    root=gui[0]
    if float(root.tk.call('info','tclversion'))>=9:
        pytest.skip('Python 3.10 Menu es incompatible con Tcl/Tk 9; controles comprobados adicionalmente en runtime Windows Tk 8.6 bajo Wine.')

pytestmark=pytest.mark.skipif(sys.platform!='win32'and not os.environ.get('DISPLAY'),reason='Requiere pantalla Tk.')


def test_admin_imports_selected_medium_without_changing_saved_settings(gui,monkeypatch):
    from app.ui.views.settings_view import SettingsView
    from app.services import local_model_catalog as M
    import tkinter.filedialog
    root,store,password,errors=gui;calls=[]
    monkeypatch.setattr(tkinter.filedialog,'askdirectory',lambda **kw:'/synthetic/medium')
    monkeypatch.setattr(M,'install_local_model',lambda source,name:calls.append((source,name))or{'path':'synthetic'})
    view=SettingsView(root);view.pack();view.whisper_model_combo.set('medium')
    before=dict(view.current_settings);view.model_import_button.invoke()
    deadline=time.monotonic()+3
    while view._model_import_running and time.monotonic()<deadline:root.update();time.sleep(.01)
    assert not view._model_import_running and not errors
    assert calls==[('/synthetic/medium','medium')]
    assert view.current_settings==before
    assert 'Guardar'in view.model_import_status.cget('text')


def test_expired_permission_after_folder_dialog_prevents_background_import(gui,monkeypatch):
    from app.ui.views.settings_view import SettingsView
    from app.services import local_model_catalog as M
    import tkinter.filedialog
    root,store,password,errors=gui
    def dialog(**kw):store.registry._clock=lambda:float('inf');return '/synthetic/medium'
    monkeypatch.setattr(tkinter.filedialog,'askdirectory',dialog)
    monkeypatch.setattr(M,'install_local_model',lambda *a:pytest.fail('Sesión caducada'))
    view=SettingsView(root);view.import_local_model()
    assert errors and not getattr(view,'_model_import_running',False)
