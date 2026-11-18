"""
============================================================
MRS Speech Analytics Professional
Punto de entrada principal
============================================================
"""

import customtkinter as ctk
from auth_local import login

from app.core.application import SpeechAnalyticsApplication
from app.services.settings_service import SettingsService


def main():
    """
    Inicia la aplicación.
    """

    # =========================================================
    # CARGAR CONFIGURACIÓN GUARDADA
    # =========================================================

    settings = SettingsService.load()

    appearance = settings.get(
        "appearance",
        "System",
    )

    ctk.set_appearance_mode(
        appearance
    )

    # =========================================================
    # INICIAR APLICACIÓN
    # =========================================================

    # El programa no se crea ni se inicia sin credenciales válidas.
    account = login()
    if account is None:
        return
    app = SpeechAnalyticsApplication()

    app.run()


if __name__ == "__main__":
    main()