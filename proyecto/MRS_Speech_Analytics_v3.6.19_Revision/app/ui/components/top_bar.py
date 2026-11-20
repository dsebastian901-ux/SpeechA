import customtkinter as ctk
from app.config import app_info
from app.services.access_service import allowed, require


class TopBar(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, height=48, corner_radius=0, fg_color="#321755")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self, text=f"◉  {app_info.APP_NAME}",
            text_color="white", font=ctk.CTkFont("Segoe UI", 16, "bold")
        ).grid(row=0, column=0, padx=15, pady=10, sticky="w")

        # Keep administration visible even when the automatic sidebar collapses.
        # Permission is enforced again inside WorkArea.show_users.
        if allowed("users"):
            ctk.CTkButton(
                self, text="Usuarios y permisos",
                width=166, height=30, corner_radius=8,
                fg_color="#76529D", hover_color="#9067B9",
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                command=lambda: parent.work_area.show_users(),
            ).grid(row=0, column=1, padx=(3, 13), pady=8, sticky="e")
        ctk.CTkLabel(
            self, text=require("batch")["username"], text_color="#DFF6E8",
            font=ctk.CTkFont("Segoe UI", 11, "bold")
        ).grid(row=0, column=2, padx=(0, 18), pady=10, sticky="e")
