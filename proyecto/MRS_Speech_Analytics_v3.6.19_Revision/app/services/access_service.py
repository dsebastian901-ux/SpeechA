"""Acceso local y catálogo firmado para intercambio manual por USB."""
from pathlib import Path
from functools import wraps
import os,tempfile,zipfile
from app.security.offline_accounts import AccountRegistry,CatalogueAuthority
ADMIN_NAME='DANIELA SEBASTIAN'
_ACTIVE=None

def _atomic(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.mrs-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb')as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

class AccessStore:
 def __init__(self,directory=None):
  self.directory=Path(directory)if directory else Path(os.environ.get('LOCALAPPDATA')or Path.home()/'.local/share')/'MRS_Speech_Analytics'/'acceso'
  self.public=self.directory/'administradora.pub';self.catalog=self.directory/'cuentas.json';self.private=self.directory/'administradora.pem'
  self.registry=AccountRegistry(self.public.read_bytes(),self.catalog)if self.public.exists()else None
  self.token=None;self.authority=None
 @property
 def configured(self):return self.registry is not None and self.catalog.exists()
 def initialize(self,password):
  if self.public.exists()or self.catalog.exists():raise ValueError('Este equipo ya está configurado; importe la actualización correspondiente.')
  a=CatalogueAuthority.create(ADMIN_NAME,password)
  # Preparar todos los bytes antes de persistir; nunca contraseña en claro.
  key=a.export_private_key(password);bundle=a.export_bundle()
  _atomic(self.private,key);_atomic(self.public,a.public_key)
  self.registry=AccountRegistry(a.public_key,self.catalog);self.registry.import_bundle(bundle)
  self.login(ADMIN_NAME,password)
 def login(self,username,password):
  # Un intento nuevo sustituye la sesión previa incluso si falla. No dejar
  # desbloqueada la capacidad de administración de un acceso anterior.
  if self.registry is not None:self.registry.logout(self.token)
  self.token=None;self.authority=None
  if not self.configured:raise PermissionError('Configure el equipo o importe el catálogo por USB.')
  self.token=self.registry.login(username,password)
  user=self.registry.require(self.token,'batch')
  if user['role']=='ADMIN'and self.private.exists():
   try:self.authority=CatalogueAuthority.restore(self.private.read_bytes(),password,self.catalog.read_bytes())
   except Exception:
    self.registry.logout(self.token);self.token=None
    raise PermissionError('No se pudo desbloquear la administración con esta contraseña.')
  return user
 def require(self,permission):
  if self.registry is None:raise PermissionError('Inicie sesión.')
  return self.registry.require(self.token,permission)
 def allowed(self,permission):
  try:self.require(permission);return True
  except PermissionError:return False
 def users(self):
  self.require('users');return [{k:u[k]for k in('username','role','active')}for u in self.registry._catalog['users']]
 def change_user(self,operation,username,value):
  self.require('users')
  if self.authority is None:raise PermissionError('El archivo de administración permanece únicamente en el equipo de la administradora.')
  if username.strip().casefold()==ADMIN_NAME.casefold():raise ValueError('Esta opción administra operadores; no modifica a la única administradora.')
  old_session=self.registry._sessions[self.token]
  if operation=='create':self.authority.create_operator(username,value)
  elif operation=='active':self.authority.set_active(username,value)
  elif operation=='password':self.authority.reset_password(username,value)
  else:raise ValueError('Operación no válida.')
  self.registry.import_bundle(self.authority.export_bundle())
  # La capacidad privada fue desbloqueada al iniciar esta sesión de admin.
  self.registry._sessions[self.token]=old_session
 def export_usb(self,path):
  self.require('users')
  with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)as z:
   z.writestr('administradora.pub',self.public.read_bytes());z.writestr('cuentas.json',self.catalog.read_bytes())
 def import_usb(self,path):
  with zipfile.ZipFile(path)as z:
   if set(z.namelist())!={'administradora.pub','cuentas.json'}or sum(i.file_size for i in z.infolist())>5*1024*1024:raise ValueError('Paquete de cuentas no válido.')
   public=z.read('administradora.pub');bundle=z.read('cuentas.json')
  if self.public.exists()and self.public.read_bytes()!=public:raise ValueError('La firma pertenece a otra administradora; se conserva la clave de confianza instalada.')
  candidate=AccountRegistry(public,self.catalog);candidate.import_bundle(bundle)
  if not self.public.exists():_atomic(self.public,public)
  self.registry=candidate;self.token=None;self.authority=None

def activate(store):
 global _ACTIVE
 _ACTIVE=store

def current():return _ACTIVE

def allowed(permission):return _ACTIVE is not None and _ACTIVE.allowed(permission)

def require(permission):
 if _ACTIVE is None:raise PermissionError('Inicie sesión para usar esta función.')
 return _ACTIVE.require(permission)

def view_permission(permission):
 def decorate(fn):
  @wraps(fn)
  def checked(self,*args,**kwargs):
   try:require(permission)
   except PermissionError as error:
    from tkinter import messagebox
    messagebox.showerror('Acceso',str(error),parent=self);return None
   return fn(self,*args,**kwargs)
  return checked
 return decorate

def require_admin_tool():
 if _ACTIVE is None:
  from app.ui.access_dialogs import authenticate_gui
  if not authenticate_gui():raise SystemExit(1)
 try:require('reviews')
 except PermissionError:
  from tkinter import messagebox
  messagebox.showerror('Acceso','Las revisiones alternas están reservadas a la administradora.')
  raise SystemExit(1)
