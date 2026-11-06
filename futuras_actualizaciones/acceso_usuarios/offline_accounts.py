"""Base de cuentas sin red. Borrador para integrar en la próxima interfaz.

El catálogo USB está firmado por la administradora; cada equipo verifica una
clave pública de confianza instalada por ella. No contiene contraseñas claras.
No integra aún las pantallas ni protege archivos frente a un administrador del SO.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
import unicodedata
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ITERATIONS = 600_000
PERMISSIONS = {
    'ADMIN': frozenset({'batch', 'dashboard', 'reports', 'reviews', 'settings', 'projects', 'users'}),
    'OPERADOR': frozenset({'batch', 'dashboard', 'reports'}),
}


def _encode(value):
    return base64.b64encode(value).decode('ascii')


def _decode(value, size):
    if not isinstance(value, str):
        raise ValueError('Formato de credencial incorrecto.')
    try:
        result = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError('Formato de credencial incorrecto.') from error
    if len(result) != size:
        raise ValueError('Longitud de credencial incorrecta.')
    return result


def _username(value):
    if not isinstance(value, str):
        raise ValueError('Indique un nombre de usuario.')
    display = ' '.join(unicodedata.normalize('NFKC', value).split())
    if not 1 <= len(display) <= 80 or not all(c.isalnum() or c in ' ._-' for c in display):
        raise ValueError('Nombre de usuario inválido.')
    return display, display.casefold()


def _password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 256:
        raise ValueError('La contraseña debe tener entre 12 y 256 caracteres.')
    return value


def _credential(password):
    password = _password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return {'algorithm': 'PBKDF2-SHA256', 'iterations': ITERATIONS,
            'salt': _encode(salt), 'digest': _encode(digest)}


def _verify(password, credential):
    # Nunca normalizar mayúsculas ni recortar espacios de una contraseña.
    if not isinstance(password, str) or len(password) > 256:
        return False
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                 _decode(credential['salt'], 16), ITERATIONS)
    return hmac.compare_digest(digest, _decode(credential['digest'], 32))


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _validate(catalog):
    if not isinstance(catalog, dict) or set(catalog) != {'schema', 'version', 'users'}:
        raise ValueError('Catálogo de usuarios inválido.')
    if type(catalog['schema']) is not int or catalog['schema'] != 1:
        raise ValueError('Versión de formato no soportada.')
    if type(catalog['version']) is not int or catalog['version'] < 1:
        raise ValueError('Versión de catálogo inválida.')
    users = catalog['users']
    if not isinstance(users, list) or not 1 <= len(users) <= 1000:
        raise ValueError('Catálogo de usuarios vacío o demasiado grande.')
    ids, names, admins = set(), set(), []
    for user in users:
        if not isinstance(user, dict) or set(user) != {'id', 'username', 'role', 'active', 'credential'}:
            raise ValueError('Registro de usuario inválido.')
        if not isinstance(user['id'], str) or str(uuid.UUID(user['id'])) != user['id']:
            raise ValueError('Identificador de usuario inválido.')
        display, key = _username(user['username'])
        if display != user['username'] or key in names or user['id'] in ids:
            raise ValueError('Nombre o identificador duplicado/no canónico.')
        names.add(key); ids.add(user['id'])
        if user['role'] not in PERMISSIONS or type(user['active']) is not bool:
            raise ValueError('Rol o estado inválido.')
        credential = user['credential']
        if not isinstance(credential, dict) or set(credential) != {'algorithm', 'iterations', 'salt', 'digest'}:
            raise ValueError('Credencial inválida.')
        if credential['algorithm'] != 'PBKDF2-SHA256' or type(credential['iterations']) is not int or credential['iterations'] != ITERATIONS:
            raise ValueError('Algoritmo de credenciales no soportado.')
        _decode(credential['salt'], 16); _decode(credential['digest'], 32)
        if user['role'] == 'ADMIN':
            admins.append(user)
    if len(admins) != 1 or not admins[0]['active']:
        raise ValueError('Debe existir exactamente una administradora activa.')
    return admins[0]


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('El archivo contiene claves duplicadas.')
        result[key] = value
    return result


class CatalogueAuthority:
    """Capacidad privada de la administradora; la clave nunca va al paquete operador.

    La futura interfaz debe desbloquearla solo tras autenticar a la administradora.
    El archivo PEM se exporta siempre cifrado con una contraseña privada.
    """
    def __init__(self, private_key, catalog):
        _validate(catalog)
        self._key = private_key
        self._catalog = deepcopy(catalog)

    @classmethod
    def create(cls, admin_username, password):
        name, _ = _username(admin_username)
        owner = {'id': str(uuid.uuid4()), 'username': name, 'role': 'ADMIN',
                 'active': True, 'credential': _credential(password)}
        return cls(Ed25519PrivateKey.generate(), {'schema': 1, 'version': 1, 'users': [owner]})

    @property
    def public_key(self):
        return self._key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    def export_private_key(self, password):
        return self._key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.BestAvailableEncryption(_password(password).encode('utf-8')))

    @classmethod
    def restore(cls, encrypted_private_key, password, signed_bundle):
        key = serialization.load_pem_private_key(encrypted_private_key, password=_password(password).encode('utf-8'))
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError('Clave de administración no soportada.')
        public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        registry = AccountRegistry(public)
        registry.import_bundle(signed_bundle)
        return cls(key, registry._catalog)

    def export_bundle(self):
        catalog = deepcopy(self._catalog)
        _validate(catalog)
        return _canonical({'catalog': catalog, 'signature': _encode(self._key.sign(_canonical(catalog)))})

    def _commit(self, catalog):
        catalog['version'] += 1
        _validate(catalog)
        self._catalog = catalog

    def create_operator(self, username, password):
        name, normalized = _username(username)
        if any(_username(u['username'])[1] == normalized for u in self._catalog['users']):
            raise ValueError('El usuario ya existe.')
        catalog = deepcopy(self._catalog)
        catalog['users'].append({'id': str(uuid.uuid4()), 'username': name, 'role': 'OPERADOR',
                                 'active': True, 'credential': _credential(password)})
        self._commit(catalog)

    def set_active(self, username, active):
        if type(active) is not bool:
            raise ValueError('Estado inválido.')
        user = self._find(username)
        if user['role'] == 'ADMIN':
            raise ValueError('No se puede desactivar a la única administradora.')
        catalog = deepcopy(self._catalog)
        next(u for u in catalog['users'] if u['id'] == user['id'])['active'] = active
        self._commit(catalog)

    def reset_password(self, username, password):
        user = self._find(username)
        credential = _credential(password)
        catalog = deepcopy(self._catalog)
        next(u for u in catalog['users'] if u['id'] == user['id'])['credential'] = credential
        self._commit(catalog)

    def _find(self, username):
        key = _username(username)[1]
        for user in self._catalog['users']:
            if _username(user['username'])[1] == key:
                return user
        raise ValueError('Usuario no encontrado.')


class AccountRegistry:
    """Catálogo local firmado y sesiones en memoria, sin conexión ni telemetría."""
    def __init__(self, trusted_public_key, store_path=None, clock=time.monotonic):
        self._public_key = Ed25519PublicKey.from_public_bytes(trusted_public_key)
        self._catalog = None
        self._sessions = {}
        self._failures = {}
        self._clock = clock
        self._store = Path(store_path) if store_path is not None else None
        self._dummy = _credential(secrets.token_urlsafe(24))
        if self._store is not None and self._store.exists():
            self.import_bundle(self._store.read_bytes(), persist=False)

    def import_bundle(self, data, *, persist=True):
        if not isinstance(data, bytes) or len(data) > 4 * 1024 * 1024:
            raise ValueError('Archivo de cuentas inválido o demasiado grande.')
        try:
            envelope = json.loads(data.decode('utf-8'), object_pairs_hook=_no_duplicate_keys)
            if not isinstance(envelope, dict) or set(envelope) != {'catalog', 'signature'}:
                raise ValueError('Formato de paquete inválido.')
            catalog = envelope['catalog']
            self._public_key.verify(_decode(envelope['signature'], 64), _canonical(catalog))
        except InvalidSignature as error:
            raise ValueError('La firma no corresponde a la administradora de esta instalación.') from error
        owner = _validate(catalog)
        if self._catalog is not None:
            current_owner = _validate(self._catalog)
            if owner['id'] != current_owner['id'] or owner['username'] != current_owner['username']:
                raise ValueError('No se puede sustituir la identidad de la administradora.')
            if catalog['version'] < self._catalog['version']:
                raise ValueError('No se permite importar una versión anterior.')
            if catalog['version'] == self._catalog['version']:
                if catalog != self._catalog:
                    raise ValueError('La versión coincide pero el contenido es distinto.')
                return False
        if persist and self._store is not None:
            self._store.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix='.cuentas-', dir=self._store.parent)
            try:
                with os.fdopen(fd, 'wb') as target:
                    target.write(data); target.flush(); os.fsync(target.fileno())
                os.replace(temporary, self._store)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        self._catalog = deepcopy(catalog)
        self._sessions.clear()
        self._failures.clear()
        return True

    def login(self, username, password):
        try:
            key = _username(username)[1]
        except ValueError:
            key = ''
        now = self._clock()
        failed, until = self._failures.get(key, (0, 0))
        if until > now:
            raise PermissionError('Usuario o contraseña incorrectos; reintente más tarde.')
        if until and until <= now:
            failed = 0
        user = next((u for u in (self._catalog or {}).get('users', []) if _username(u['username'])[1] == key), None)
        password_ok = _verify(password, user['credential'] if user else self._dummy)
        if not user or not user['active'] or not password_ok:
            failed += 1
            self._failures[key] = (failed, now + 300 if failed >= 5 else 0)
            raise PermissionError('Usuario o contraseña incorrectos.')
        self._failures.pop(key, None)
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (user['id'], now + 8 * 3600)
        return token

    def require(self, token, permission):
        session = self._sessions.get(token)
        if session is None or session[1] <= self._clock():
            self._sessions.pop(token, None)
            raise PermissionError('Inicie sesión de nuevo.')
        user = next(u for u in self._catalog['users'] if u['id'] == session[0])
        if not user['active'] or permission not in PERMISSIONS[user['role']]:
            raise PermissionError('Acceso no autorizado.')
        return {key: user[key] for key in ('id', 'username', 'role')}

    def logout(self, token):
        self._sessions.pop(token, None)
