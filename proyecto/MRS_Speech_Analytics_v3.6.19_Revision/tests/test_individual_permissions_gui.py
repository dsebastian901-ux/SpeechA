"""Pruebas Tk de permisos con usuarios y proyectos sintéticos, sin datos reales."""
import itertools
import os
import secrets
import sys
import tkinter as tk
from tkinter import ttk
import pytest
from app.services.access_service import AccessStore,activate,ADMIN_NAME

pytestmark=pytest.mark.skipif(sys.platform!='win32'and not os.environ.get('DISPLAY'),reason='Necesita pantalla Tk (Xvfb o Windows).')


def descendants(parent):
    for widget in parent.winfo_children():
        yield widget
        yield from descendants(widget)


@pytest.fixture
def gui(tmp_path,monkeypatch):
    import customtkinter as ctk
    from tkinter import messagebox
    errors=[]
    monkeypatch.setattr(messagebox,'showerror',lambda *a,**kw:errors.append(a))
    store=AccessStore(tmp_path/'accounts');password=secrets.token_urlsafe(24)
    store.initialize(password);activate(store)
    root=ctk.CTk();root.geometry('1100x700');root.update()
    yield root,store,password,errors
    activate(None)
    root.destroy()


def test_users_window_creates_and_edits_a_restricted_operator(gui):
    from app.ui.access_dialogs import users_window,OperatorAccessDialog
    root,store,password,errors=gui
    window=users_window(root);root.update()
    tree=next(w for w in descendants(window)if isinstance(w,ttk.Treeview))
    assert len(tree['columns'])==4
    create=OperatorAccessDialog(window,store,lambda:None)
    create.username.insert(0,'Operador sintético');create.password.insert(0,password);create.confirm.insert(0,password)
    for name,var in create.permissions.items():var.set(name=='reports')
    create.save_button.invoke();root.update()
    assert not errors and not create.winfo_exists()
    edit=OperatorAccessDialog(window,store,lambda:None,'Operador sintético')
    assert edit.permissions['reports'].get()and not edit.permissions['batch'].get()
    for name,var in edit.permissions.items():var.set(name=='dashboard')
    edit.save_button.invoke();root.update()
    assert not errors and store.users()[1]['permissions']==['dashboard']
    with pytest.raises(ValueError):OperatorAccessDialog(window,store,lambda:None,ADMIN_NAME)
    store.login('Operador sintético',password)
    with pytest.raises(PermissionError):users_window(root)
    with pytest.raises(PermissionError):OperatorAccessDialog(root,store,lambda:None)


def test_all_eight_permission_subsets_have_a_valid_landing_and_no_admin_button(gui,monkeypatch):
    from app.ui.components.work_area import WorkArea
    from app.ui.components.top_bar import TopBar
    root,store,password,errors=gui
    calls=[]
    for permission,method in [('projects','show_home'),('batch','show_batch'),('dashboard','show_dashboard'),('reports','show_reports')]:
        monkeypatch.setattr(WorkArea,method,lambda self,p=permission:calls.append(p))
    for n in range(4):
        for subset in itertools.combinations(['batch','dashboard','reports'],n):
            store.login(ADMIN_NAME,password)
            if len(store.users())==1:store.create_operator('Operador',password,permissions=list(subset))
            else:store.change_user('permissions','Operador',list(subset))
            store.login('Operador',password);calls.clear()
            area=WorkArea(root);root.work_area=area
            assert calls==([subset[0]]if subset else[])
            bar=TopBar(root);root.update()
            texts=[str(w.cget('text'))for w in descendants(bar)if hasattr(w,'cget')and 'text'in w.keys()]
            assert 'Usuarios y permisos'not in texts
            assert ('Consultar proyecto'in texts)==bool(subset and 'batch'not in subset)
            if not subset:
                assert any('No tienes funciones'in str(w.cget('text')) for w in descendants(area)if isinstance(w,tk.Label))
            area.destroy();bar.destroy()
    assert not errors


@pytest.mark.parametrize('scaling',[1.0,1.5,2.0])
def test_admin_controls_remain_inside_resizable_window_at_different_tk_scaling(gui,scaling):
    from app.ui.access_dialogs import users_window,OperatorAccessDialog
    root,store,password,errors=gui
    old=root.tk.call('tk','scaling');root.tk.call('tk','scaling',scaling)
    try:
        window=users_window(root);root.update()
        buttons=[w for w in descendants(window)if isinstance(w,ttk.Button)]
        assert len(buttons)==5
        for button in buttons:
            assert button.winfo_rooty()+button.winfo_height()<=window.winfo_rooty()+window.winfo_height()
            assert button.winfo_rootx()+button.winfo_width()<=window.winfo_rootx()+window.winfo_width()
        create=OperatorAccessDialog(window,store,lambda:None);root.update()
        assert create.save_button.winfo_rooty()+create.save_button.winfo_height()<=create.winfo_rooty()+create.winfo_height()
        assert len(create.permissions)==3
        create.destroy();window.destroy()
    finally:root.tk.call('tk','scaling',old)
