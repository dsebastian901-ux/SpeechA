"""
============================================================
MRS Speech Analytics Professional
Clase principal de la aplicación
============================================================
"""

import customtkinter as ctk

from app.config import settings
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow
from app.ui.login_window import LoginWindow
from app.services.auth_service import AuthService


class SpeechAnalyticsApplication:
    """
    Clase principal de la aplicación.
    """

    def __init__(self):

        # ---------------------------------------------------
        # Cargar configuración guardada
        # ---------------------------------------------------
        saved_settings = SettingsService.load()

        # ---------------------------------------------------
        # Configuración general de apariencia
        # ---------------------------------------------------
        appearance = saved_settings.get(
            "appearance",
            settings.THEME,
        )

        ctk.set_appearance_mode(appearance)
        ctk.set_default_color_theme(settings.COLOR_THEME)

        # ---------------------------------------------------
        # Crear la ventana principal
        # ---------------------------------------------------
        self.auth = AuthService()
        self.window = None

    def run(self):
        """
        Inicia el ciclo principal de la aplicación.
        """
        while True:
            login = LoginWindow(self.auth)
            login.mainloop()
            if not login.authenticated:
                break
            self.window = MainWindow(auth=self.auth)
            self.window.mainloop()
            if not getattr(self.window, 'logout_requested', False):
                break
            self.auth.logout()