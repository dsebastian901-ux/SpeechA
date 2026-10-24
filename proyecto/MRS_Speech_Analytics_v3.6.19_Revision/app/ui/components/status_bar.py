"""
============================================================
MRS Speech Analytics Professional
Componente: Barra de estado
============================================================
"""

import customtkinter as ctk

from app.config import app_info


class StatusBar(ctk.CTkFrame):
    """Barra inferior con información del sistema."""

    def __init__(self, parent):
        super().__init__(
            parent,
            height=35,
            corner_radius=0
        )

        self.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self,
            text="Estado: Listo",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            )
        )

        self.status_label.grid(
            row=0,
            column=0,
            padx=15,
            pady=7,
            sticky="w"
        )

        self.version_label = ctk.CTkLabel(
            self,
            text=f"Versión {app_info.APP_VERSION}",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            )
        )

        self.version_label.grid(
            row=0,
            column=1,
            padx=15,
            pady=7,
            sticky="e"
        )

    def update_status(self, message):
        """Actualiza el mensaje visible en la barra de estado."""

        self.status_label.configure(
            text=f"Estado: {message}"
        )