"""Local user administration view (administrator only)."""
import customtkinter as ctk
from tkinter import messagebox
from app.services.auth_service import ROLES

class UsersView(ctk.CTkFrame):
    def __init__(self,parent,auth):
        auth.require("users")
        super().__init__(parent,fg_color="#F6F3FA")
        self.auth=auth
        self.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self,text="Administración de usuarios",font=ctk.CTkFont(size=25,weight="bold"),text_color="#321755").grid(row=0,column=0,padx=24,pady=(22,12),sticky="w")
        form=ctk.CTkFrame(self,fg_color="white")
        form.grid(row=1,column=0,padx=22,pady=8,sticky="ew")
        self.username=ctk.CTkEntry(form,placeholder_text="Usuario",width=180)
        self.username.pack(side="left",padx=8,pady=12)
        self.password=ctk.CTkEntry(form,placeholder_text="Contraseña temporal",show="*",width=190)
        self.password.pack(side="left",padx=8)
        self.role=ctk.CTkOptionMenu(form,values=list(ROLES),width=135)
        self.role.pack(side="left",padx=8)
        ctk.CTkButton(form,text="Crear",command=self._create,width=90).pack(side="left",padx=8)
        actions=ctk.CTkFrame(self,fg_color="white")
        actions.grid(row=2,column=0,padx=22,pady=8,sticky="ew")
        self.target=ctk.CTkEntry(actions,placeholder_text="Usuario a modificar",width=180)
        self.target.pack(side="left",padx=8,pady=12)
        ctk.CTkButton(actions,text="Cambiar rol",command=self._role,width=98).pack(side="left",padx=5)
        ctk.CTkButton(actions,text="Activar",command=lambda:self._active(True),width=75).pack(side="left",padx=5)
        ctk.CTkButton(actions,text="Desactivar",command=lambda:self._active(False),width=90).pack(side="left",padx=5)
        ctk.CTkButton(actions,text="Restablecer clave",command=self._reset,width=130).pack(side="left",padx=5)
        ctk.CTkButton(actions,text="Emitir código de recuperación",
            command=self._issue_recovery,width=192).pack(side="left",padx=5)
        self.list=ctk.CTkTextbox(self,font=ctk.CTkFont(family="Consolas",size=12))
        self.list.grid(row=3,column=0,padx=22,pady=10,sticky="nsew")
        self.grid_rowconfigure(3,weight=1)
        self.refresh()
    def _execute(self,callback):
        try:
            callback()
            self.password.delete(0,"end")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Usuarios",str(exc),parent=self)
    def _create(self):
        self._execute(lambda:self.auth.create_user(self.username.get().strip(),self.password.get(),self.role.get()))
    def _role(self):
        self._execute(lambda:self.auth.set_role(self.target.get().strip(),self.role.get()))
    def _active(self,state):
        self._execute(lambda:self.auth.set_active(self.target.get().strip(),state))
    def _reset(self):
        if not self.password.get():
            messagebox.showinfo("Usuarios","Escriba la nueva contraseña temporal en el campo superior.",parent=self)
            return
        self._execute(lambda:self.auth.reset_password(self.target.get().strip(),self.password.get()))
    def _issue_recovery(self):
        username=self.target.get().strip() or self.auth.current_user["username"]
        if not messagebox.askyesno("Código de recuperación",
                f"¿Emitir un código de recuperación para {username}?\n"
                "El código anterior dejará de funcionar.",parent=self):
            return
        try:
            code=self.auth.issue_recovery_code(username)
            messagebox.showinfo("Código de recuperación (una sola vez)",
                f"Usuario: {username}\n\nCódigo: {code}\n\n"
                "Guárdelo en un lugar seguro. Se muestra una sola vez.",
                parent=self)
        except Exception as exc:
            messagebox.showerror("Código de recuperación",str(exc),parent=self)

    def refresh(self):
        self.list.configure(state="normal")
        self.list.delete("1.0","end")
        self.list.insert("end","USUARIO                          ROL              ACTIVO   CAMBIO CLAVE\n")
        self.list.insert("end","-"*80+"\n")
        for name,role,active,must_change in self.auth.users():
            self.list.insert("end",f"{name[:30]:30}   {role:15}  {'Sí' if active else 'No':6}   {'Sí' if must_change else 'No'}\n")
        self.list.configure(state="disabled")
