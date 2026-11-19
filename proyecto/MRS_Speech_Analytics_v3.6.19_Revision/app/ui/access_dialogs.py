"""Inicio de sesión y administración sin conexión."""
import tkinter as tk
from tkinter import ttk,messagebox,filedialog,simpledialog
from app.services.access_service import AccessStore,ADMIN_NAME,activate,current,require


def authenticate_gui(store=None):
 store=store or AccessStore();root=tk.Tk();root.title('MRS · Iniciar sesión');root.geometry('500x450');root.resizable(False,False)
 accepted=[False]
 def draw():
  for w in root.winfo_children():w.destroy()
  tk.Label(root,text='MRS Speech Analytics',font=('Segoe UI',20,'bold')).pack(pady=(22,8))
  tk.Label(root,text='Acceso local · sin internet',font=('Segoe UI',11)).pack(pady=(0,14))
  initial=not store.configured
  tk.Label(root,text='Usuario').pack();name=tk.Entry(root,width=43);name.pack(pady=(2,9))
  if initial:name.insert(0,ADMIN_NAME);name.configure(state='readonly')
  tk.Label(root,text='Contraseña').pack();password=tk.Entry(root,width=43,show='•');password.pack(pady=(2,9))
  repeat=None
  if initial:
   tk.Label(root,text='Confirmar contraseña (mínimo 12 caracteres)').pack();repeat=tk.Entry(root,width=43,show='•');repeat.pack(pady=(2,9))
  def enter():
   try:
    if initial:
     if password.get()!=repeat.get():raise ValueError('Las contraseñas no coinciden.')
     store.initialize(password.get())
    else:store.login(name.get(),password.get())
    activate(store);accepted[0]=True;root.destroy()
   except Exception as e:messagebox.showerror('Acceso',str(e),parent=root);password.delete(0,'end')
  tk.Button(root,text='Configurar mi cuenta de administradora'if initial else'Ingresar',width=39,command=enter).pack(pady=8)
  def import_usb():
   path=filedialog.askopenfilename(parent=root,title='Catálogo entregado por la administradora',filetypes=[('Cuentas MRS','*.mrsusuarios'),('ZIP','*.zip')])
   if not path:return
   try:
    if not store.configured and not messagebox.askyesno('Configurar equipo operador','Importe únicamente el catálogo USB recibido de DANIELA SEBASTIAN. ¿Confirma su procedencia?',parent=root):return
    store.import_usb(path);draw();messagebox.showinfo('Usuarios','Catálogo actualizado. Inicie sesión con su usuario y contraseña.',parent=root)
   except Exception as e:messagebox.showerror('Usuarios',str(e),parent=root)
  tk.Button(root,text='Importar / actualizar cuentas por USB',width=39,command=import_usb).pack(pady=4)
  tk.Label(root,text='En equipos operadores, importe el catálogo por USB.\nLas bajas se aplican al importar la actualización.',font=('Segoe UI',9)).pack(pady=10)
  root.bind('<Return>',lambda e:enter());password.focus_set()if initial else name.focus_set()
 draw();root.mainloop();return accepted[0]


def users_window(parent):
 require('users');store=current();window=tk.Toplevel(parent);window.title('Usuarios · Administración');window.geometry('740x450');window.transient(parent)
 columns=('usuario','rol','activo');tree=ttk.Treeview(window,columns=columns,show='headings',height=12)
 for name,label in zip(columns,['Usuario','Permiso','Estado']):tree.heading(name,text=label);tree.column(name,width=235 if name=='usuario'else 175)
 tree.pack(fill='both',expand=True,padx=12,pady=12)
 def refresh():
  tree.delete(*tree.get_children())
  for u in store.users():tree.insert('', 'end',values=[u['username'],u['role'],'ACTIVO'if u['active']else'INACTIVO'])
 def perform(action):
  try:action();refresh()
  except Exception as e:messagebox.showerror('Usuarios',str(e),parent=window)
 def create():
  name=simpledialog.askstring('Nuevo operador','Nombre de usuario:',parent=window)
  if not name:return
  password=simpledialog.askstring('Contraseña local','Contraseña inicial (mínimo 12 caracteres):',show='•',parent=window)
  if password is None:return
  confirm=simpledialog.askstring('Confirmar contraseña','Repita la contraseña:',show='•',parent=window)
  if password!=confirm:raise ValueError('Las contraseñas no coinciden.')
  store.change_user('create',name,password)
 def selected():
  rows=tree.selection()
  if not rows:raise ValueError('Seleccione un usuario.')
  return tree.item(rows[0],'values')
 def state():
  name,_,active=selected();store.change_user('active',name,active!='ACTIVO')
 def password():
  name,_,_=selected();value=simpledialog.askstring('Restablecer contraseña',f'Nueva contraseña de {name} (mínimo 12 caracteres):',show='•',parent=window)
  if value is not None:store.change_user('password',name,value)
 def export():
  name=filedialog.asksaveasfilename(parent=window,title='Exportar cuentas para los equipos operadores',defaultextension='.mrsusuarios',initialfile='Cuentas_MRS.mrsusuarios')
  if name:
   store.export_usb(name);messagebox.showinfo('USB','Paquete firmado generado. Cópielo por USB e impórtelo en cada equipo para aplicar altas y bajas.',parent=window)
 buttons=tk.Frame(window);buttons.pack(pady=7)
 for text,fn in [('Nuevo operador',create),('Activar / desactivar',state),('Contraseña',password),('Exportar USB',export)]:tk.Button(buttons,text=text,command=lambda f=fn:perform(f)).pack(side='left',padx=4)
 tk.Label(window,text='Operadores: lotes, dashboard y reportes. Revisiones y configuración: solo administradora.').pack(pady=(4,12));refresh()
