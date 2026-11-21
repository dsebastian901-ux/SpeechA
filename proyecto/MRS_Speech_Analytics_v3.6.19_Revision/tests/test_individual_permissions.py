"""Permisos firmados por operador, compatibles con cuentas locales existentes."""
from copy import deepcopy
import itertools
import json
import secrets
import zipfile

import pytest
from app.security.offline_accounts import AccountRegistry,CatalogueAuthority,PERMISSIONS,_canonical,_encode
from app.services.access_service import AccessStore,ADMIN_NAME


@pytest.fixture
def password():
    return secrets.token_urlsafe(24)


SUBSETS=[list(selection) for count in range(4)
         for selection in itertools.combinations(['batch','dashboard','reports'],count)]


@pytest.mark.parametrize('selection',SUBSETS)
def test_signed_individual_permissions_allow_only_the_selected_functions(password,selection):
    authority=CatalogueAuthority.create(ADMIN_NAME,password)
    authority.create_operator('Operador sintético',password,permissions=selection)
    registry=AccountRegistry(authority.public_key)
    registry.import_bundle(authority.export_bundle())
    token=registry.login('Operador sintético',password)
    assert registry.identity(token)['role']=='OPERADOR'
    for permission in PERMISSIONS['ADMIN']:
        if permission in selection:assert registry.require(token,permission)
        else:
            with pytest.raises(PermissionError):registry.require(token,permission)
    admin=registry.login(ADMIN_NAME,password)
    for permission in PERMISSIONS['ADMIN']:assert registry.require(admin,permission)


@pytest.mark.parametrize('selection',[['users'],['reviews'],['projects'],['settings'],['batch','batch'],['unknown'],'reports',[True]])
def test_operator_cannot_be_granted_admin_unknown_duplicate_or_malformed_permissions(password,selection):
    a=CatalogueAuthority.create(ADMIN_NAME,password);a.create_operator('Ejemplo',password)
    before=a.export_bundle()
    with pytest.raises(ValueError):a.set_permissions('Ejemplo',selection)
    assert a.export_bundle()==before


def test_legacy_schema_keeps_ids_credentials_key_and_roles_during_permission_upgrade(password):
    a=CatalogueAuthority.create(ADMIN_NAME,password);a.create_operator('Ejemplo',password)
    original=deepcopy(a._catalog);public=a.public_key
    r=AccountRegistry(public);r.import_bundle(a.export_bundle())
    assert r.require(r.login('Ejemplo',password),'batch')
    a.set_permissions('Ejemplo',['reports'])
    assert a._catalog['schema']==2 and a.public_key==public
    for old,new in zip(original['users'],a._catalog['users']):
        for key in ['id','username','credential','role','active']:assert old[key]==new[key]
    r.import_bundle(a.export_bundle());t=r.login('Ejemplo',password)
    assert r.require(t,'reports')
    with pytest.raises(PermissionError):r.require(t,'batch')
    with pytest.raises(ValueError):a.set_permissions(ADMIN_NAME,[])


def test_signed_schema_downgrade_cannot_restore_permissions(password):
    a=CatalogueAuthority.create(ADMIN_NAME,password);a.create_operator('Ejemplo',password)
    old=deepcopy(a._catalog);a.set_permissions('Ejemplo',['dashboard'])
    r=AccountRegistry(a.public_key);r.import_bundle(a.export_bundle())
    old['version']=a._catalog['version']+10
    envelope=_canonical({'catalog':old,'signature':_encode(a._key.sign(_canonical(old)))})
    with pytest.raises(ValueError):r.import_bundle(envelope)
    assert r.require(r.login('Ejemplo',password),'dashboard')
    with pytest.raises(PermissionError):r.require(r.login('Ejemplo',password),'batch')


def test_even_signed_admin_restriction_and_unsigned_permission_change_are_rejected(password):
    a=CatalogueAuthority.create(ADMIN_NAME,password);a.create_operator('Ejemplo',password,permissions=['reports'])
    envelope=json.loads(a.export_bundle());envelope['catalog']['users'][1]['permissions']=['users']
    with pytest.raises(ValueError):AccountRegistry(a.public_key).import_bundle(_canonical(envelope))
    data=deepcopy(a._catalog);data['users'][0]['permissions']=['batch']
    signed=_canonical({'catalog':data,'signature':_encode(a._key.sign(_canonical(data)))})
    with pytest.raises(ValueError):AccountRegistry(a.public_key).import_bundle(signed)


def test_store_logins_work_without_batch_and_usb_preserves_individual_permissions(tmp_path,password):
    admin=AccessStore(tmp_path/'admin');admin.initialize(password)
    admin.create_operator('Reportes',password,permissions=['reports'])
    package=tmp_path/'catalog.mrsusuarios';admin.export_usb(package)
    operator=AccessStore(tmp_path/'operator');operator.import_usb(package)
    assert operator.login('Reportes',password)['username']=='Reportes'
    assert operator.current_user()['username']=='Reportes'
    assert operator.allowed('reports')and not operator.allowed('batch')
    with zipfile.ZipFile(package)as z:assert set(z.namelist())=={'administradora.pub','cuentas.json'}
    admin.change_user('permissions','Reportes',['dashboard'])
    admin.export_usb(package);operator.import_usb(package)
    with pytest.raises(PermissionError):operator.require('reports')
    operator.login('Reportes',password)
    assert operator.allowed('dashboard')and not operator.allowed('reports')
    assert 'credential'not in admin.users()[1]
    assert admin.users()[1]['permissions']==['dashboard']


def test_permission_write_failure_does_not_advance_authority_or_destroy_existing_session(tmp_path,password,monkeypatch):
    admin=AccessStore(tmp_path/'admin');admin.initialize(password)
    admin.change_user('create','Ejemplo',password)
    before=admin.catalog.read_bytes();version=admin.authority._catalog['version']
    original=admin.registry.import_bundle
    monkeypatch.setattr(admin.registry,'import_bundle',lambda *a,**kw:(_ for _ in ()).throw(OSError('disco de prueba')))
    with pytest.raises(OSError):admin.change_user('permissions','Ejemplo',['reports'])
    assert admin.catalog.read_bytes()==before
    assert admin.authority._catalog['version']==version
    monkeypatch.setattr(admin.registry,'import_bundle',original)
    assert admin.allowed('users')
    admin.change_user('permissions','Ejemplo',['reports'])
    assert admin.users()[1]['permissions']==['reports']


def test_catalog_update_revokes_sessions_in_another_store_on_same_computer(tmp_path,password):
    a=AccessStore(tmp_path/'accounts');a.initialize(password);a.change_user('create','Ejemplo',password)
    b=AccessStore(a.directory);b.login('Ejemplo',password);assert b.allowed('reports')
    a.change_user('permissions','Ejemplo',['batch'])
    with pytest.raises(PermissionError):b.require('reports')
    b.login('Ejemplo',password);assert b.allowed('batch')and not b.allowed('reports')


def test_password_and_active_changes_keep_permissions_and_revoke_prior_login(tmp_path,password):
    a=AccessStore(tmp_path/'accounts');a.initialize(password)
    a.create_operator('Ejemplo',password,permissions=['reports'])
    new=secrets.token_urlsafe(24);a.change_user('password','Ejemplo',new)
    with pytest.raises(PermissionError):a.login('Ejemplo',password)
    a.login('Ejemplo',new);assert a.allowed('reports')and not a.allowed('batch')
    a.login(ADMIN_NAME,password);a.change_user('active','Ejemplo',False)
    with pytest.raises(PermissionError):a.login('Ejemplo',new)
    a.login(ADMIN_NAME,password);a.change_user('active','Ejemplo',True)
    a.login('Ejemplo',new);assert a.allowed('reports')and not a.allowed('batch')


def test_default_profile_copies_legacy_accounts_without_modifying_r57_catalog(tmp_path,password,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    legacy=AccessStore(tmp_path/'MRS_Speech_Analytics/acceso');legacy.initialize(password)
    legacy.change_user('create','Ejemplo',password)
    before={p.name:p.read_bytes()for p in legacy.directory.iterdir()if p.is_file()}
    upgraded=AccessStore()
    assert upgraded.directory!=legacy.directory
    assert upgraded.login(ADMIN_NAME,password)['username']==ADMIN_NAME
    upgraded.change_user('permissions','Ejemplo',['reports'])
    assert {p.name:p.read_bytes()for p in legacy.directory.iterdir()if p.is_file()}==before
    assert upgraded.public.read_bytes()==legacy.public.read_bytes()
    assert upgraded.private.read_bytes()==legacy.private.read_bytes()
    legacy_again=AccessStore(legacy.directory);legacy_again.login('Ejemplo',password)
    assert legacy_again.allowed('batch')and legacy_again.allowed('dashboard')and legacy_again.allowed('reports')
    upgraded.login('Ejemplo',password);assert upgraded.allowed('reports')and not upgraded.allowed('batch')


def test_failed_first_setup_leaves_no_half_configured_account_directory(tmp_path,password,monkeypatch):
    import app.services.access_service as module
    a=AccessStore(tmp_path/'new');original=module._atomic;calls=[]
    def fail_second(path,data):
        calls.append(path)
        if len(calls)==2:raise OSError('disco de prueba')
        return original(path,data)
    monkeypatch.setattr(module,'_atomic',fail_second)
    with pytest.raises(OSError):a.initialize(password)
    assert not a.public.exists()and not a.catalog.exists()and not a.private.exists()
    monkeypatch.setattr(module,'_atomic',original)
    a.initialize(password);assert a.allowed('users')
