"""Acceso local MRS: sin contraseñas predeterminadas."""
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

DATABASE = Path(os.getenv("LOCALAPPDATA",str(Path.home()))) / "MRS_Speech_Analytics" / "usuarios.sqlite3"
ROLES = ("administrador","supervisor","gestor","consulta")

def connect():
    DATABASE.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DATABASE,timeout=15)
    db.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY COLLATE NOCASE, salt TEXT NOT NULL, hash TEXT NOT NULL, rol TEXT NOT NULL, activo INTEGER NOT NULL DEFAULT 1)")
    return db

def hashed(password,salt):
    return hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),bytes.fromhex(salt),400000).hex()

def check_data(username,password):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}",username):
        raise ValueError("Usuario: 3-40 caracteres alfanuméricos, punto, guion o guion bajo.")
    if len(password)<12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres.")

def first_user():
    with connect() as db:
        return db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]==0

def create_admin(username,password):
    check_data(username,password)
    salt=secrets.token_hex(16)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]:
            raise ValueError("La cuenta inicial ya fue creada.")
        db.execute("INSERT INTO usuarios(usuario,salt,hash,rol) VALUES(?,?,?,?)",(username,salt,hashed(password,salt),"administrador"))

def authenticate(username,password):
    with connect() as db:
        row=db.execute("SELECT usuario,salt,hash,rol FROM usuarios WHERE usuario=? AND activo=1",(username,)).fetchone()
    if row and hmac.compare_digest(hashed(password,row[1]),row[2]):
        return {"usuario":row[0],"rol":row[3]}
    return None

def users():
    with connect() as db:
        return db.execute("SELECT usuario,rol,activo FROM usuarios ORDER BY usuario").fetchall()

def create_user(actor,username,password,role):
    if actor["rol"]!="administrador":raise PermissionError("Requiere administrador.")
    check_data(username,password)
    if role not in ROLES:raise ValueError("Rol no válido.")
    salt=secrets.token_hex(16)
    with connect() as db:
        db.execute("INSERT INTO usuarios(usuario,salt,hash,rol) VALUES(?,?,?,?)",(username,salt,hashed(password,salt),role))

def edit_user(actor,username,role=None,active=None,password=None):
    if actor["rol"]!="administrador":raise PermissionError("Requiere administrador.")
    if role is not None and role not in ROLES:raise ValueError("Rol no válido.")
    if password is not None:check_data(username,password)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("SELECT rol,activo FROM usuarios WHERE usuario=?",(username,)).fetchone()
        if not row:raise ValueError("Usuario inexistente.")
        removing=(role is not None and role!="administrador") or active is False
        if username.lower()==actor["usuario"].lower() and removing:
            raise ValueError("No se permite quitar el acceso al administrador actual.")
        if row[0]=="administrador" and row[1] and removing:
            count=db.execute("SELECT COUNT(*) FROM usuarios WHERE rol='administrador' AND activo=1").fetchone()[0]
            if count<=1:raise ValueError("Debe permanecer un administrador activo.")
        if role is not None:db.execute("UPDATE usuarios SET rol=? WHERE usuario=?",(role,username))
        if active is not None:db.execute("UPDATE usuarios SET activo=? WHERE usuario=?",(int(active),username))
        if password is not None:
            salt=secrets.token_hex(16)
            db.execute("UPDATE usuarios SET salt=?,hash=? WHERE usuario=?",(salt,hashed(password,salt),username))

def ask(root,title,text,secret=False):
    window=tk.Toplevel(root)
    window.title(title)
    window.resizable(False,False)
    window.grab_set()
    ttk.Label(window,text=text).pack(padx=16,pady=9)
    entry=ttk.Entry(window,width=40,show="*" if secret else "")
    entry.pack(padx=16,pady=8)
    result=[None]
    def accept(event=None):
        result[0]=entry.get()
        window.destroy()
    ttk.Button(window,text="Aceptar",command=accept).pack(pady=12)
    window.bind("<Return>",accept)
    window.bind("<Escape>",lambda e:window.destroy())
    entry.focus_set()
    root.wait_window(window)
    return result[0]

def administer(root,actor):
    if actor["rol"]!="administrador":return
    popup=tk.Toplevel(root)
    popup.title("Administración de usuarios MRS")
    popup.geometry("610x380")
    popup.grab_set()
    tree=ttk.Treeview(popup,columns=("usuario","rol","activo"),show="headings")
    for key,heading in (("usuario","Usuario"),("rol","Rol"),("activo","Activo")):tree.heading(key,text=heading)
    tree.pack(fill="both",expand=True,padx=12,pady=12)
    def refresh():
        for item in tree.get_children():tree.delete(item)
        for name,role,active in users():tree.insert("","end",values=(name,role,"Sí" if active else "No"))
    def selection():
        picked=tree.selection()
        if not picked:
            messagebox.showwarning("Selecciona usuario","Selecciona un usuario.",parent=popup)
            return None
        return tree.item(picked[0])["values"][0]
    def execute(fn):
        try:fn();refresh()
        except (ValueError,PermissionError,sqlite3.Error) as exc:messagebox.showerror("Error",str(exc),parent=popup)
    def add():
        name=ask(popup,"Nuevo usuario","Nombre:")
        if not name:return
        role=ask(popup,"Rol","administrador / supervisor / gestor / consulta")
        if role is None:return
        pwd=ask(popup,"Contraseña","Contraseña inicial (mín. 12 caracteres):",True)
        if pwd is not None:execute(lambda:create_user(actor,name,pwd,role.strip().lower()))
    def update_role():
        name=selection()
        if not name:return
        role=ask(popup,"Cambiar rol","administrador / supervisor / gestor / consulta")
        if role is not None:execute(lambda:edit_user(actor,name,role=role.strip().lower()))
    def reset():
        name=selection()
        if not name:return
        pwd=ask(popup,"Restablecer contraseña","Contraseña nueva (mín. 12 caracteres):",True)
        if pwd is not None:execute(lambda:edit_user(actor,name,password=pwd))
    def toggle():
        name=selection()
        if not name:return
        row=next(x for x in users() if x[0].lower()==name.lower())
        execute(lambda:edit_user(actor,name,active=not bool(row[2])))
    buttons=ttk.Frame(popup)
    buttons.pack(pady=(0,12))
    for label,fn in (("Agregar",add),("Cambiar rol",update_role),("Nueva contraseña",reset),("Activar/Desactivar",toggle)):
        ttk.Button(buttons,text=label,command=fn).pack(side="left",padx=4)
    refresh()
    root.wait_window(popup)

def login():
    root=tk.Tk()
    root.title("MRS Speech Analytics - Acceso")
    root.geometry("440x310")
    root.resizable(False,False)
    root.withdraw()
    try:initial=first_user()
    except (OSError,sqlite3.Error) as exc:
        messagebox.showerror("Acceso","No se puede abrir la base de usuarios: "+str(exc),parent=root)
        root.destroy()
        return None
    root.deiconify()
    ttk.Label(root,text="MRS Speech Analytics",font=("Segoe UI",18,"bold")).pack(pady=(20,6))
    ttk.Label(root,text="Crear administrador inicial" if initial else "Iniciar sesión").pack(pady=7)
    panel=ttk.Frame(root);panel.pack()
    ttk.Label(panel,text="Usuario:").grid(row=0,column=0,padx=7,pady=6)
    username=ttk.Entry(panel,width=31);username.grid(row=0,column=1,padx=7,pady=6)
    ttk.Label(panel,text="Contraseña:").grid(row=1,column=0,padx=7,pady=6)
    password=ttk.Entry(panel,width=31,show="*");password.grid(row=1,column=1,padx=7,pady=6)
    confirmation=None
    if initial:
        ttk.Label(panel,text="Confirmar:").grid(row=2,column=0,padx=7,pady=6)
        confirmation=ttk.Entry(panel,width=31,show="*")
        confirmation.grid(row=2,column=1,padx=7,pady=6)
    result=[None];attempts=[0]
    def submit(event=None):
        try:
            if initial:
                if password.get()!=confirmation.get():raise ValueError("Las contraseñas no coinciden.")
                create_admin(username.get().strip(),password.get())
            account=authenticate(username.get().strip(),password.get())
            if not account:
                attempts[0]+=1
                if attempts[0]>=5:root.quit()
                raise ValueError("Usuario o contraseña incorrectos.")
            result[0]=account
            root.quit()
        except (ValueError,sqlite3.Error,OSError) as exc:
            messagebox.showerror("Acceso",str(exc),parent=root)
    ttk.Button(root,text="Crear administrador" if initial else "Entrar",command=submit).pack(pady=15)
    root.bind("<Return>",submit)
    root.protocol("WM_DELETE_WINDOW",root.quit)
    username.focus_set()
    root.mainloop()
    if result[0] and result[0]["rol"]=="administrador":
        if messagebox.askyesno("Usuarios","¿Administrar usuarios antes de entrar?",parent=root):
            administer(root,result[0])
    root.destroy()
    return result[0]
