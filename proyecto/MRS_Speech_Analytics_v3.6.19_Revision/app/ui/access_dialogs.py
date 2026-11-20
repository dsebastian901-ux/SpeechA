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
