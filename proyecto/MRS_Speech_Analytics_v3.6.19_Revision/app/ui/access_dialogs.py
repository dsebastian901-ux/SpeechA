"""Inicio de sesión y administración sin conexión."""
import tkinter as tk
from tkinter import ttk,messagebox,filedialog,simpledialog
from app.services.access_service import AccessStore,ADMIN_NAME,activate,current,require


def _login_watermark(parent):
    """Use the existing MRS owl as a subtle login watermark, without new assets."""
    from pathlib import Path
    from PIL import Image, ImageTk

    file = Path(__file__).resolve().parent / "assets" / "mrs_logo_round.png"
    if not file.is_file():
        return None
    try:
        with Image.open(file) as original:
            logo = original.convert("RGBA")
        logo.thumbnail((235, 190), Image.Resampling.LANCZOS)
        # Precompose against the canvas background for predictable Tk rendering.
        logo.putalpha(logo.getchannel("A").point(lambda alpha: round(alpha * 0.20)))
        background = Image.new("RGBA", logo.size, "#FFFFFF")
        background.alpha_composite(logo, ((background.width - logo.width) // 2, 0))
        return ImageTk.PhotoImage(background.convert("RGB"), master=parent)
    except (OSError, ValueError):
        # Missing/corrupt artwork must never block authentication.
        return None


def authenticate_gui(store=None):
    """Branded sign-in; existing password, local catalog and USB logic unchanged."""
    store = store or AccessStore()
    initial = not store.configured
    root = tk.Tk()
    root.title("MRS Speech Analytics · Acceso seguro")
    root.geometry("630x650" if initial else "630x565")
    root.resizable(False, False)
    root.configure(bg="#F5F1FA")
    accepted = [False]

    def draw():
        for child in root.winfo_children():
            child.destroy()
        first_setup = not store.configured
        root.geometry("630x650" if first_setup else "630x565")

        surface = tk.Frame(root, bg="#FFFFFF", highlightthickness=1,
                           highlightbackground="#E8DFEE")
        surface.pack(fill="both", expand=True, padx=18, pady=15)

        # Logo watermark goes BEHIND the heading, directly ABOVE user/password.
        # The same MRS owl used by the main app is bundled in app/ui/assets/.
        header = tk.Canvas(surface, width=580, height=223, bg="#FFFFFF",
                           highlightthickness=0, borderwidth=0)
        header.pack(pady=(6, 0))
        watermark = _login_watermark(header)
        if watermark is not None:
            header._mrs_logo = watermark  # keep Tk reference alive
            header.create_image(290, 137, image=watermark, anchor="center")
        else:
            header.create_text(290, 136, text="MRS", fill="#E6DDEF",
                               font=("Segoe UI", 51, "bold"))
        header.create_text(290, 36, text="MRS Speech Analytics",
                           fill="#321755", font=("Segoe UI", 24, "bold"))
        header.create_text(290, 75, text="PLATAFORMA DE MONITOREO Y CALIDAD",
                           fill="#765F86", font=("Segoe UI", 10, "bold"))
        header.create_text(290, 206, text="Acceso local seguro  ·  Uso interno",
                           fill="#6A5680", font=("Segoe UI", 10))

        form = tk.Frame(surface, bg="#FFFFFF")
        form.pack(fill="x", padx=90)

        def field(label, *, secret=False):
            tk.Label(form, text=label, font=("Segoe UI", 10, "bold"),
                     bg="#FFFFFF", fg="#321755", anchor="w").pack(fill="x", pady=(3, 4))
            entry = tk.Entry(form, width=40, font=("Segoe UI", 11),
                             show="●" if secret else "", relief="solid", bd=1,
                             highlightthickness=1, highlightcolor="#7854AC",
                             highlightbackground="#DAD1E4")
            entry.pack(fill="x", ipady=6, pady=(0, 9))
            return entry

        name = field("Usuario")
        if first_setup:
            name.insert(0, ADMIN_NAME)
            name.configure(state="readonly", readonlybackground="#F6F2FA")
        password = field("Contraseña", secret=True)
        repeat = field("Confirmar contraseña (mínimo 12 caracteres)", secret=True) if first_setup else None

        def enter():
            try:
                if first_setup:
                    if password.get() != repeat.get():
                        raise ValueError("Las contraseñas no coinciden.")
                    store.initialize(password.get())
                else:
                    store.login(name.get(), password.get())
                activate(store)
                accepted[0] = True
                root.destroy()
            except Exception as error:
                messagebox.showerror("Acceso", str(error), parent=root)
                password.delete(0, "end")

        tk.Button(form,
                  text="Configurar cuenta administradora" if first_setup else "Iniciar sesión",
                  command=enter, font=("Segoe UI", 11, "bold"), cursor="hand2",
                  bg="#4A246C", fg="#FFFFFF", activebackground="#60368A",
                  activeforeground="#FFFFFF", relief="flat", bd=0,
                  padx=12, pady=9).pack(fill="x", pady=(5, 6))

        def import_usb():
            selected = filedialog.askopenfilename(
                parent=root, title="Catálogo entregado por la administradora",
                filetypes=[("Cuentas MRS", "*.mrsusuarios"), ("ZIP", "*.zip")])
            if not selected:
                return
            try:
                if not store.configured and not messagebox.askyesno(
                    "Configurar equipo operador",
                    "Importe únicamente el catálogo USB recibido de la administradora. "
                    "¿Confirma su procedencia?", parent=root
                ):
                    return
                store.import_usb(selected)
                draw()
                messagebox.showinfo("Usuarios",
                    "Catálogo actualizado. Inicie sesión con su usuario y contraseña.",
                    parent=root)
            except Exception as error:
                messagebox.showerror("Usuarios", str(error), parent=root)

        tk.Button(form, text="Importar / actualizar cuentas por USB",
                  command=import_usb, font=("Segoe UI", 10),
                  bg="#F0E9F7", fg="#4A246C", activebackground="#E7DAF1",
                  relief="flat", bd=0, cursor="hand2", padx=10, pady=8).pack(fill="x", pady=(0, 7))
        tk.Label(surface, text="En otros equipos, importa el catálogo firmado por USB.",
                 bg="#FFFFFF", fg="#82738C", font=("Segoe UI", 9)).pack(pady=(2, 7))

        root.bind("<Return>", lambda event: enter())
        (password if first_setup else name).focus_set()

    draw()
    root.mainloop()
    return accepted[0]


OPERATOR_FUNCTIONS = (('batch','Procesamiento por lotes'),('dashboard','Dashboard'),('reports','Reportes'))


class OperatorAccessDialog(tk.Toplevel):
    """Alta y permisos de operador: no expone credenciales ni funciones de admin."""
    def __init__(self,parent,store,on_saved,username=None):
        store.require('users')
        selected=next((u for u in store.users()if u['username']==username),None)if username else None
        if username and (selected is None or selected['role']!='OPERADOR'):
            raise ValueError('Seleccione un operador; la administradora conserva acceso total.')
        super().__init__(parent)
        self.store=store;self.on_saved=on_saved;self.editing=username
        self.title('Permisos individuales'if username else'Nuevo operador')
        self.transient(parent.winfo_toplevel())
        width=min(560,self.winfo_screenwidth()-60);height=min(540,self.winfo_screenheight()-100)
        self.geometry(f'{width}x{height}');self.minsize(min(470,width),min(430,height))
        self.grid_columnconfigure(0,weight=1)
        self.grid_rowconfigure(1,weight=1)
        tk.Label(self,text='Permisos del operador'if username else'Alta de operador',
            font=('Segoe UI',14,'bold'),anchor='w').grid(row=0,column=0,sticky='ew',padx=22,pady=(16,8))
        form=tk.Frame(self);form.grid(row=1,column=0,sticky='nsew',padx=22,pady=6);form.grid_columnconfigure(0,weight=1)
        tk.Label(form,text='Nombre de usuario',anchor='w').grid(row=0,column=0,sticky='ew')
        self.username=tk.Entry(form);self.username.grid(row=1,column=0,sticky='ew',ipady=4,pady=(3,10))
        if username:
            self.username.insert(0,username);self.username.configure(state='readonly')
        self.password=None;self.confirm=None
        row=2
        if not username:
            for key,label in [('password','Contraseña inicial (mínimo 12 caracteres)'),('confirm','Confirmar contraseña')]:
                tk.Label(form,text=label,anchor='w').grid(row=row,column=0,sticky='ew')
                entry=tk.Entry(form,show='●');entry.grid(row=row+1,column=0,sticky='ew',ipady=4,pady=(3,10))
                setattr(self,key,entry);row+=2
        tk.Label(form,text='Funciones permitidas',font=('Segoe UI',10,'bold'),anchor='w').grid(row=row,column=0,sticky='ew',pady=(3,5));row+=1
        initial=selected['permissions']if selected else [p for p,_ in OPERATOR_FUNCTIONS]
        self.permissions={}
        for permission,label in OPERATOR_FUNCTIONS:
            value=tk.BooleanVar(self,value=permission in initial);self.permissions[permission]=value
            ttk.Checkbutton(form,text=label,variable=value).grid(row=row,column=0,sticky='w',pady=3);row+=1
        tk.Label(form,text='Sin funciones seleccionadas, podrá iniciar sesión pero no utilizar módulos.',
            anchor='w',justify='left',wraplength=max(390,width-50)).grid(row=row,column=0,sticky='ew',pady=(10,5))
        buttons=tk.Frame(self);buttons.grid(row=2,column=0,sticky='ew',padx=22,pady=(8,16))
        ttk.Button(buttons,text='Cancelar',command=self.destroy).pack(side='right',padx=(8,0))
        self.save_button=ttk.Button(buttons,text='Guardar permisos'if username else'Crear operador',command=self.save)
        self.save_button.pack(side='right')
        self.grab_set();self.username.focus_set()

    def save(self):
        try:
            selected=[p for p,_ in OPERATOR_FUNCTIONS if self.permissions[p].get()]
            if self.editing:
                self.store.change_user('permissions',self.editing,selected)
            else:
                if self.password.get()!=self.confirm.get():raise ValueError('Las contraseñas no coinciden.')
                self.store.create_operator(self.username.get(),self.password.get(),permissions=selected)
            self.on_saved();self.destroy()
        except (ValueError,PermissionError,OSError) as error:
            messagebox.showerror('Usuarios',str(error),parent=self)


def users_window(parent):
    require('users');store=current()
    window=tk.Toplevel(parent);window.title('Usuarios y permisos · Administración');window.transient(parent.winfo_toplevel())
    width=min(1040,window.winfo_screenwidth()-70);height=min(600,window.winfo_screenheight()-100)
    window.geometry(f'{width}x{height}');window.minsize(min(860,width),min(480,height))
    window.grid_columnconfigure(0,weight=1);window.grid_rowconfigure(1,weight=1)
    tk.Label(window,text='Usuarios y permisos individuales',font=('Segoe UI',15,'bold'),anchor='w').grid(
        row=0,column=0,sticky='ew',padx=16,pady=(14,8))
    table=tk.Frame(window);table.grid(row=1,column=0,sticky='nsew',padx=16,pady=8)
    table.grid_columnconfigure(0,weight=1);table.grid_rowconfigure(0,weight=1)
    columns=('usuario','rol','activo','permisos')
    tree=ttk.Treeview(table,columns=columns,show='headings',height=9)
    for name,label,size in zip(columns,['Usuario','Rol','Estado','Funciones permitidas'],[210,120,95,460]):
        tree.heading(name,text=label);tree.column(name,width=size,minwidth=75,stretch=name in {'usuario','permisos'})
    tree.grid(row=0,column=0,sticky='nsew')
    scroll=ttk.Scrollbar(table,orient='vertical',command=tree.yview);scroll.grid(row=0,column=1,sticky='ns')
    horizontal=ttk.Scrollbar(table,orient='horizontal',command=tree.xview);horizontal.grid(row=1,column=0,sticky='ew')
    tree.configure(yscrollcommand=scroll.set,xscrollcommand=horizontal.set)
    def refresh():
        tree.delete(*tree.get_children())
        labels=dict(OPERATOR_FUNCTIONS)
        for user in store.users():
            functions='Acceso total (administradora)'if user['role']=='ADMIN'else ', '.join(labels[p]for p in user['permissions'])or'Sin funciones'
            tree.insert('','end',values=[user['username'],user['role'],'ACTIVO'if user['active']else'INACTIVO',functions])
    def selected():
        rows=tree.selection()
        if not rows:raise ValueError('Seleccione un operador.')
        return tree.item(rows[0],'values')
    def perform(action):
        try:store.require('users');action()
        except (ValueError,PermissionError,OSError) as error:messagebox.showerror('Usuarios',str(error),parent=window)
    def create():return OperatorAccessDialog(window,store,refresh)
    def permissions():return OperatorAccessDialog(window,store,refresh,selected()[0])
    def state():
        name,_,active,_=selected();store.change_user('active',name,active!='ACTIVO');refresh()
    def password():
        name=selected()[0]
        value=simpledialog.askstring('Restablecer contraseña',f'Nueva contraseña de {name} (mínimo 12 caracteres):',show='●',parent=window)
        if value is not None:store.change_user('password',name,value);refresh()
    def export():
        name=filedialog.asksaveasfilename(parent=window,title='Exportar cuentas y permisos para los operadores',
            defaultextension='.mrsusuarios',initialfile='Cuentas_MRS.mrsusuarios')
        if name:
            store.export_usb(name);messagebox.showinfo('USB','Importe este catálogo firmado en cada equipo para aplicar las cuentas y sus permisos. No incluye la clave privada.',parent=window)
    buttons=tk.Frame(window);buttons.grid(row=2,column=0,sticky='ew',padx=12,pady=8)
    actions=[('Nuevo operador',create),('Permisos individuales',permissions),('Activar / desactivar',state),('Contraseña',password),('Exportar USB',export)]
    for i,(label,fn) in enumerate(actions):
        buttons.grid_columnconfigure(i%3,weight=1)
        ttk.Button(buttons,text=label,command=lambda f=fn:perform(f)).grid(row=i//3,column=i%3,sticky='ew',padx=4,pady=4)
    footer=tk.Label(window,text='La administradora conserva acceso total. Los cambios se aplican aquí; exporte e importe el catálogo por USB en los demás equipos.',justify='left',anchor='w',wraplength=width-40)
    footer.grid(row=3,column=0,sticky='ew',padx=16,pady=(2,12))
    window.bind('<Configure>',lambda event:footer.configure(wraplength=max(350,window.winfo_width()-40))if event.widget is window else None)
    refresh()
    return window
