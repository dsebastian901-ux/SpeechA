"""Permisos reales, conservación del catálogo USB y ausencia de claves privadas."""
from pathlib import Path
import zipfile
import pytest
from app.services.access_service import AccessStore,ADMIN_NAME,activate,require
PASSWORD='Contraseña local de prueba 123'

def test_operator_usb_does_not_export_authority_and_rejects_admin_functions(tmp_path):
 admin=AccessStore(tmp_path/'admin');admin.initialize(PASSWORD)
 admin.change_user('create','Operador ejemplo',PASSWORD)
 package=tmp_path/'cuentas.mrsusuarios';admin.export_usb(package)
 with zipfile.ZipFile(package)as z:assert set(z.namelist())=={'administradora.pub','cuentas.json'}
 operator=AccessStore(tmp_path/'other');operator.import_usb(package);operator.login('Operador ejemplo',PASSWORD)
 for p in ['batch','dashboard','reports']:assert operator.allowed(p)
 for p in ['users','projects','settings','reviews']:assert not operator.allowed(p)
 assert not operator.private.exists()
 with pytest.raises(PermissionError):operator.change_user('create','Otro operador',PASSWORD)
 with pytest.raises(PermissionError):operator.export_usb(tmp_path/'invalid.zip')
 admin.change_user('active','Operador ejemplo',False);admin.export_usb(package)
 assert operator.allowed('batch')  # La baja aún no llegó a un equipo desconectado.
 operator.import_usb(package)
 with pytest.raises(PermissionError):operator.login('Operador ejemplo',PASSWORD)

def test_pinned_key_and_versions_cannot_be_replaced_by_other_account(tmp_path):
 admin=AccessStore(tmp_path/'admin');admin.initialize(PASSWORD);package=tmp_path/'first.zip';admin.export_usb(package)
 team=AccessStore(tmp_path/'team');team.import_usb(package)
 other=AccessStore(tmp_path/'other');other.initialize(PASSWORD);other.export_usb(tmp_path/'other.zip')
 with pytest.raises(ValueError):team.import_usb(tmp_path/'other.zip')
 admin.change_user('create','Operador ejemplo',PASSWORD);admin.export_usb(tmp_path/'new.zip');team.import_usb(tmp_path/'new.zip')
 with pytest.raises(ValueError):team.import_usb(package)

def test_only_one_admin_can_be_initialized_and_global_session_is_required(tmp_path):
 admin=AccessStore(tmp_path/'admin');admin.initialize(PASSWORD)
 assert admin.require('users')['username']==ADMIN_NAME
 with pytest.raises(ValueError):admin.initialize(PASSWORD)
 with pytest.raises(ValueError):admin.change_user('active',ADMIN_NAME,False)
 activate(None)
 with pytest.raises(PermissionError):require('batch')
 activate(admin);assert require('reviews')['role']=='ADMIN';activate(None)

def test_password_reset_leaves_source_password_invalid_after_usb_update(tmp_path):
 admin=AccessStore(tmp_path/'admin');admin.initialize(PASSWORD);admin.change_user('create','Operador ejemplo',PASSWORD)
 admin.change_user('password','Operador ejemplo','Nueva contraseña local 123')
 package=tmp_path/'cuentas.zip';admin.export_usb(package)
 user=AccessStore(tmp_path/'team');user.import_usb(package)
 with pytest.raises(PermissionError):user.login('Operador ejemplo',PASSWORD)
 assert user.login('Operador ejemplo','Nueva contraseña local 123')['role']=='OPERADOR'


def test_alternate_review_tools_reject_operator_even_if_called_directly(tmp_path,monkeypatch):
 from app.services.access_service import require_admin_tool
 import tkinter.messagebox
 admin=AccessStore(tmp_path/'admin');admin.initialize(PASSWORD);admin.change_user('create','Operador ejemplo',PASSWORD)
 admin.login('Operador ejemplo',PASSWORD);activate(admin)
 monkeypatch.setattr(tkinter.messagebox,'showerror',lambda *a,**kw:None)
 with pytest.raises(SystemExit):require_admin_tool()
 activate(None)
