import json
import pytest
from offline_accounts import AccountRegistry, CatalogueAuthority, _canonical, _encode

PASSWORD = 'Contraseña de prueba 123'

@pytest.fixture
def authority():
    a = CatalogueAuthority.create('Administradora ejemplo', PASSWORD)
    a.create_operator('Operador ejemplo', PASSWORD)
    return a


def test_roles_reviews_and_offline_import(authority, tmp_path):
    file = tmp_path/'cuentas.json'
    r = AccountRegistry(authority.public_key, file)
    r.import_bundle(authority.export_bundle())
    operator = r.login('OPERADOR EJEMPLO', PASSWORD)
    for area in ['batch', 'dashboard', 'reports']:
        assert r.require(operator, area)['role'] == 'OPERADOR'
    for area in ['reviews', 'settings', 'projects', 'users', 'missing']:
        with pytest.raises(PermissionError): r.require(operator, area)
    admin = r.login('Administradora ejemplo', PASSWORD)
    assert r.require(admin, 'reviews')['role'] == 'ADMIN'
    assert r.require(admin, 'users')['role'] == 'ADMIN'
    assert PASSWORD.encode() not in file.read_bytes()
    restarted = AccountRegistry(authority.public_key, file)
    with pytest.raises(PermissionError): restarted.require(admin, 'users')
    assert restarted.login('Operador ejemplo', PASSWORD)


def test_usb_disable_and_rollback(authority):
    r = AccountRegistry(authority.public_key)
    old = authority.export_bundle();r.import_bundle(old)
    token = r.login('Operador ejemplo', PASSWORD)
    authority.set_active('Operador ejemplo', False)
    # Equipos desconectados no conocen una baja hasta importar la actualización.
    assert r.require(token, 'batch')
    r.import_bundle(authority.export_bundle())
    with pytest.raises(PermissionError): r.require(token, 'batch')
    with pytest.raises(PermissionError): r.login('Operador ejemplo', PASSWORD)
    with pytest.raises(ValueError, match='anterior'):r.import_bundle(old)


def test_operator_cannot_edit_role_or_replace_trusted_key(authority):
    r = AccountRegistry(authority.public_key)
    bundle = json.loads(authority.export_bundle())
    bundle['catalog']['users'][1]['role'] = 'ADMIN'
    with pytest.raises(ValueError, match='firma'):r.import_bundle(_canonical(bundle))
    outsider = CatalogueAuthority.create('Otra persona', PASSWORD)
    with pytest.raises(ValueError, match='firma'):r.import_bundle(outsider.export_bundle())


def test_owner_cannot_be_disabled_and_duplicate_names_rejected(authority):
    with pytest.raises(ValueError):authority.set_active('Administradora ejemplo', False)
    with pytest.raises(ValueError):authority.create_operator('  OPERADOR   EJEMPLO ', PASSWORD)


def test_even_signed_second_admin_is_rejected(authority):
    data = json.loads(authority.export_bundle())['catalog']
    data['users'][1]['role'] = 'ADMIN'
    envelope = _canonical({'catalog':data,'signature':_encode(authority._key.sign(_canonical(data)))})
    with pytest.raises(ValueError,match='exactamente una'):AccountRegistry(authority.public_key).import_bundle(envelope)


def test_password_update_and_encrypted_key_backup(authority):
    old = authority.export_bundle()
    private = authority.export_private_key('Clave de respaldo de prueba')
    assert b'ENCRYPTED' in private and PASSWORD.encode() not in private
    restored = CatalogueAuthority.restore(private, 'Clave de respaldo de prueba', old)
    assert restored.public_key == authority.public_key
    restored.reset_password('Operador ejemplo','Nueva contraseña de prueba')
    r = AccountRegistry(authority.public_key);r.import_bundle(restored.export_bundle())
    with pytest.raises(PermissionError):r.login('Operador ejemplo',PASSWORD)
    assert r.login('Operador ejemplo','Nueva contraseña de prueba')


def test_failure_limit_and_expiry(authority):
    now = [0.0];r=AccountRegistry(authority.public_key,clock=lambda:now[0]);r.import_bundle(authority.export_bundle())
    for _ in range(5):
        with pytest.raises(PermissionError):r.login('Operador ejemplo','Incorrecta')
    with pytest.raises(PermissionError):r.login('Operador ejemplo',PASSWORD)
    now[0]=301;token=r.login('Operador ejemplo',PASSWORD)
    now[0]+=8*3600
    with pytest.raises(PermissionError):r.require(token,'batch')
