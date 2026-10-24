"""
============================================================
MRS Speech Analytics Professional
Punto de entrada principal
============================================================
"""

import customtkinter as ctk

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

    app = SpeechAnalyticsApplication()

    app.run()


if __name__ == "__main__":
    main()