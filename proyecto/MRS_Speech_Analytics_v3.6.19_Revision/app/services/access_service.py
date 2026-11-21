"""Acceso local, permisos individuales firmados e intercambio manual por USB."""
from functools import wraps
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from app.security.offline_accounts import AccountRegistry, CatalogueAuthority, effective_permissions

ADMIN_NAME = 'DANIELA SEBASTIAN'
_ACTIVE = None


def _atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.mrs-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _install_directory(directory, files):
    """Publicar el catálogo y la clave juntos, sin dejar un alta a medias."""
    directory = Path(directory)
    directory.parent.mkdir(parents=True, exist_ok=True)
    AccountRegistry(files['administradora.pub']).import_bundle(files['cuentas.json'])
    if directory.exists() and any(directory.iterdir()):
        raise ValueError('La carpeta de acceso ya contiene archivos; se conservan intactos.')
    stage = Path(tempfile.mkdtemp(prefix='.acceso-', dir=directory.parent))
    try:
        for name, data in files.items():
            _atomic(stage / name, data)
        if directory.exists():
            directory.rmdir()  # Solo puede quitar la carpeta reservada si sigue vacía.
        stage.rename(directory)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _profile_directory():
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.local/share') / 'MRS_Speech_Analytics'
    target, legacy = base / 'acceso_r58', base / 'acceso'
    if (not target.exists() or not any(target.iterdir())) and (legacy / 'administradora.pub').is_file() and (legacy / 'cuentas.json').is_file():
        files = {name: (legacy / name).read_bytes() for name in ('administradora.pub', 'cuentas.json')}
        if (legacy / 'administradora.pem').is_file():
            files['administradora.pem'] = (legacy / 'administradora.pem').read_bytes()
        # Verifica la firma antes de copiar. No convierte identidades, claves,
        # contraseñas ni permisos, ni escribe sobre el perfil usado por R57.
        _install_directory(target, files)
    return target


class AccessStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else _profile_directory()
        self.public = self.directory / 'administradora.pub'
        self.catalog = self.directory / 'cuentas.json'
        self.private = self.directory / 'administradora.pem'
        self._trusted_public = self.public.read_bytes() if self.public.exists() else None
        self.registry = AccountRegistry(self._trusted_public, self.catalog) if self._trusted_public else None
        self.token = None
        self.authority = None

    @property
    def configured(self):
        return self.registry is not None and self.catalog.exists()

    def initialize(self, password):
        if self.public.exists() or self.catalog.exists() or self.private.exists():
            raise ValueError('Este equipo ya está configurado; importe la actualización correspondiente.')
        authority = CatalogueAuthority.create(ADMIN_NAME, password)
        files = {'administradora.pem': authority.export_private_key(password),
                 'administradora.pub': authority.public_key, 'cuentas.json': authority.export_bundle()}
        _install_directory(self.directory, files)
        self._trusted_public = authority.public_key
        self.registry = AccountRegistry(self._trusted_public, self.catalog)
        self.login(ADMIN_NAME, password)

    def _refresh_catalog(self):
        if self.registry is None:
            raise PermissionError('Inicie sesión.')
        try:
            if self.public.read_bytes() != self._trusted_public:
                raise ValueError('La clave de confianza instalada cambió.')
            raw = self.catalog.read_bytes()
            if hashlib.sha256(raw).hexdigest() != self.registry._bundle_digest:
                if self.registry.import_bundle(raw, persist=False):
                    self.token = None
                    self.authority = None
        except (OSError, ValueError, TypeError) as error:
            self.registry._sessions.clear()
            self.token = None
            self.authority = None
            raise PermissionError('El catálogo local no está disponible o no es válido. Importe el catálogo firmado de la administradora.') from error

    def login(self, username, password):
        if self.registry is not None:
            self.registry.logout(self.token)
        self.token = None
        self.authority = None
        if not self.configured:
            raise PermissionError('Configure el equipo o importe el catálogo por USB.')
        self._refresh_catalog()
        self.token = self.registry.login(username, password)
        user = self.registry.identity(self.token)
        if user['role'] == 'ADMIN' and self.private.exists():
            try:
                self.authority = CatalogueAuthority.restore(self.private.read_bytes(), password, self.catalog.read_bytes())
            except Exception as error:
                self.registry.logout(self.token)
                self.token = None
                raise PermissionError('No se pudo desbloquear la administración con esta contraseña.') from error
        return user

    def current_user(self):
        self._refresh_catalog()
        return self.registry.identity(self.token)

    def require(self, permission):
        self._refresh_catalog()
        return self.registry.require(self.token, permission)

    def allowed(self, permission):
        try:
            self.require(permission)
            return True
        except PermissionError:
            return False

    def users(self):
        self.require('users')
        return [{**{key: user[key] for key in ('username', 'role', 'active')},
                 'permissions': sorted(effective_permissions(user))} for user in self.registry._catalog['users']]

    def _change(self, operation, username, value):
        self.require('users')
        if self.authority is None:
            raise PermissionError('El archivo de administración permanece únicamente en el equipo de la administradora.')
        if operation != 'create' and self.authority._find(username)['role'] == 'ADMIN':
            raise ValueError('Esta opción administra operadores; no modifica a la única administradora.')
        old_session = self.registry._sessions[self.token]
        future = self.authority.fork()
        if operation == 'create':
            password, permissions = value
            future.create_operator(username, password, permissions=permissions)
        elif operation == 'active':
            future.set_active(username, value)
        elif operation == 'password':
            future.reset_password(username, value)
        elif operation == 'permissions':
            future.set_permissions(username, value)
        else:
            raise ValueError('Operación no válida.')
        # La autoridad y versión previas siguen vigentes si falla el guardado.
        self.registry.import_bundle(future.export_bundle())
        self.authority = future
        self.registry._sessions[self.token] = old_session

    def create_operator(self, username, password, permissions=None):
        return self._change('create', username, (password, permissions))

    def change_user(self, operation, username, value):
        return self._change(operation, username, (value, None) if operation == 'create' else value)

    def export_usb(self, path):
        self.require('users')
        target = Path(path).expanduser().resolve()
        if target in {p.resolve() for p in (self.public, self.catalog, self.private)}:
            raise ValueError('El paquete USB no puede sustituir los archivos locales de acceso.')
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.cuentas-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
            with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('administradora.pub', self._trusted_public)
                archive.writestr('cuentas.json', self.catalog.read_bytes())
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def import_usb(self, path):
        with zipfile.ZipFile(path) as archive:
            if (len(archive.namelist()) != 2 or set(archive.namelist()) != {'administradora.pub', 'cuentas.json'}
                    or sum(i.file_size for i in archive.infolist()) > 5 * 1024 * 1024):
                raise ValueError('Paquete de cuentas no válido.')
            public, bundle = archive.read('administradora.pub'), archive.read('cuentas.json')
        pinned = self._trusted_public or (self.public.read_bytes() if self.public.exists() else None)
        if pinned is not None and pinned != public:
            raise ValueError('La firma pertenece a otra administradora; se conserva la clave de confianza instalada.')
        if not self.directory.exists() or not any(self.directory.iterdir()):
            _install_directory(self.directory, {'administradora.pub': public, 'cuentas.json': bundle})
        else:
            candidate = AccountRegistry(public, self.catalog)
            candidate.import_bundle(bundle)
            if not self.public.exists():
                _atomic(self.public, public)
        self._trusted_public = public
        self.registry = AccountRegistry(public, self.catalog)
        self.token = None
        self.authority = None


def activate(store):
    global _ACTIVE
    _ACTIVE = store


def current():
    return _ACTIVE


def current_user():
    if _ACTIVE is None:
        raise PermissionError('Inicie sesión.')
    return _ACTIVE.current_user()


def allowed(permission):
    return _ACTIVE is not None and _ACTIVE.allowed(permission)


def require(permission):
    if _ACTIVE is None:
        raise PermissionError('Inicie sesión para usar esta función.')
    return _ACTIVE.require(permission)


def require_any(permissions):
    for permission in permissions:
        if allowed(permission):
            return require(permission)
    raise PermissionError('No tiene permiso para consultar proyectos.')


def view_permission(permission):
    def decorate(fn):
        @wraps(fn)
        def checked(self, *args, **kwargs):
            try:
                require(permission)
            except PermissionError as error:
                from tkinter import messagebox
                messagebox.showerror('Acceso', str(error), parent=self)
                return None
            return fn(self, *args, **kwargs)
        return checked
    return decorate


def require_admin_tool():
    if _ACTIVE is None:
        from app.ui.access_dialogs import authenticate_gui
        if not authenticate_gui():
            raise SystemExit(1)
    try:
        require('reviews')
    except PermissionError:
        from tkinter import messagebox
        messagebox.showerror('Acceso', 'Las revisiones alternas están reservadas a la administradora.')
        raise SystemExit(1)
