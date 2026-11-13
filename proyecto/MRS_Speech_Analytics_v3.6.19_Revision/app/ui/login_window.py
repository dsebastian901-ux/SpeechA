"""Login / first-run administrator / forced password change."""
import customtkinter as ctk
from tkinter import messagebox

class LoginWindow(ctk.CTk):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth
        self.authenticated = False
        self.title("MRS Speech Analytics | Acceso")
        self.geometry("470x430")
        self.resizable(False,False)
        self.configure(fg_color="#F6F3FA")
        self.protocol("WM_DELETE_WINDOW",self.destroy)
        self._screen()

    def _screen(self):
        for child in self.winfo_children():
            child.destroy()
        setup = self.auth.needs_setup()
        card = ctk.CTkFrame(self,fg_color="white",corner_radius=18)
        card.pack(padx=28,pady=25,fill="both",expand=True)
        ctk.CTkLabel(card,text="MRS | SPEECH ANALYTICS",font=ctk.CTkFont("Segoe UI",22,"bold"),text_color="#321755").pack(pady=(24,9))
        ctk.CTkLabel(card,text="Crear administrador inicial" if setup else "Iniciar sesión",font=ctk.CTkFont(size=15),text_color="#674A80").pack(pady=(0,15))
        self.username=ctk.CTkEntry(card,placeholder_text="Usuario",width=310)
        self.username.pack(pady=7)
        self.password=ctk.CTkEntry(card,placeholder_text="Contraseña",show="*",width=310)
        self.password.pack(pady=7)
        if setup:
            self.confirm=ctk.CTkEntry(card,placeholder_text="Confirmar contraseña",show="*",width=310)
            self.confirm.pack(pady=7)
        self.message=ctk.CTkLabel(card,text="Mínimo 12 caracteres" if setup else "",text_color="#9A3456")
        self.message.pack(pady=6)
        ctk.CTkButton(card,text="Crear administrador" if setup else "Entrar",fg_color="#4B276B",width=310,command=self._submit).pack(pady=(6,16))
        if not setup:
            ctk.CTkButton(card,text="¿Olvidaste tu contraseña?",fg_color="transparent",
                text_color="#4B276B",hover_color="#EDE4F4",width=310,
                command=self._recovery_screen).pack(pady=(0,10))
        self.password.bind("<Return>",lambda _event:self._submit())

    def _submit(self):
        name=self.username.get().strip()
        password=self.password.get()
        try:
            if self.auth.needs_setup():
                if password != self.confirm.get():
                    raise ValueError("Las contraseñas no coinciden.")
                recovery_code = self.auth.initial_admin(name,password)
                messagebox.showinfo("Código de recuperación (guardar en lugar seguro)",
                    "Guarde este código en un lugar seguro; se muestra una sola vez. "
                    "Sirve para recuperar la contraseña sin borrar su cuenta.\n\n"
                    + recovery_code + "\n\nNo comparta este código.",parent=self)
            self.auth.login(name,password)
            if self.auth.current_user["must_change"]:
                self._change_required(password)
                return
            self.authenticated=True
            self.destroy()
        except (ValueError,PermissionError,Exception) as exc:
            self.message.configure(text=str(exc) if isinstance(exc,(ValueError,PermissionError)) else "No se pudo abrir la base local.")

    def _recovery_screen(self):
        for child in self.winfo_children():
            child.destroy()
        frame=ctk.CTkFrame(self,fg_color="white",corner_radius=18)
        frame.pack(padx=28,pady=20,fill="both",expand=True)
        ctk.CTkLabel(frame,text="Restablecer contraseña",
            font=ctk.CTkFont("Segoe UI",20,"bold"),text_color="#321755").pack(pady=(20,8))
        ctk.CTkLabel(frame,text="Se requiere un código de recuperación emitido previamente.",
            wraplength=365,text_color="#674A80").pack(pady=(0,10))
        name=ctk.CTkEntry(frame,placeholder_text="Usuario",width=315)
        name.pack(pady=5)
        code=ctk.CTkEntry(frame,placeholder_text="Código de recuperación",width=315)
        code.pack(pady=5)
        new=ctk.CTkEntry(frame,placeholder_text="Nueva contraseña (mín. 12 caracteres)",
                          show="*",width=315)
        new.pack(pady=5)
        confirm=ctk.CTkEntry(frame,placeholder_text="Confirmar nueva contraseña",
                              show="*",width=315)
        confirm.pack(pady=5)
        message=ctk.CTkLabel(frame,text="",wraplength=365,text_color="#9A3456")
        message.pack(pady=5)
        def reset():
            try:
                if new.get()!=confirm.get():
                    raise ValueError("Las contraseñas no coinciden.")
                self.auth.recover_password(name.get(),code.get(),new.get())
                messagebox.showinfo("Contraseña restablecida",
                    "Ya puede iniciar sesión con su nueva contraseña.",parent=self)
                self._screen()
            except (ValueError,PermissionError) as exc:
                message.configure(text=str(exc))
            except Exception:
                message.configure(text="No fue posible completar la recuperación.")
        ctk.CTkButton(frame,text="Restablecer contraseña",width=315,
            fg_color="#4B276B",command=reset).pack(pady=6)
        ctk.CTkButton(frame,text="Volver al inicio de sesión",width=315,
            fg_color="transparent",text_color="#4B276B",command=self._screen).pack(pady=4)

    def _change_required(self,old):
        for child in self.winfo_children():
            child.destroy()
        frame=ctk.CTkFrame(self,fg_color="white",corner_radius=18)
        frame.pack(padx=28,pady=40,fill="both",expand=True)
        ctk.CTkLabel(frame,text="Cambiar contraseña inicial",font=ctk.CTkFont(size=20,weight="bold")).pack(pady=25)
        new=ctk.CTkEntry(frame,show="*",placeholder_text="Nueva contraseña (mín. 12 caracteres)",width=320)
        new.pack(pady=6)
        confirm=ctk.CTkEntry(frame,show="*",placeholder_text="Confirmar nueva contraseña",width=320)
        confirm.pack(pady=6)
        msg=ctk.CTkLabel(frame,text="")
        msg.pack(pady=8)
        def save():
            try:
                if new.get()!=confirm.get():
                    raise ValueError("Las contraseñas no coinciden.")
                self.auth.change_password(old,new.get())
                self.authenticated=True
                self.destroy()
            except (ValueError,PermissionError) as exc:
                msg.configure(text=str(exc))
        ctk.CTkButton(frame,text="Guardar e ingresar",command=save).pack(pady=10)
