"""
Punto central de acceso al sistema visual de la aplicación.

Ejemplo de uso:

    from app.ui.themes import Theme

    color = Theme.colors.PRIMARY
    font = Theme.fonts.TITLE
"""

from .colors import Colors
from .fonts import Fonts, FontFamily, FontSize, FontWeight
from .spacing import Spacing
from .dimensions import Dimensions
from .styles import Styles


class Theme:
    colors = Colors
    fonts = Fonts
    font_family = FontFamily
    font_size = FontSize
    font_weight = FontWeight
    spacing = Spacing
    dimensions = Dimensions
    styles = Styles

    APPEARANCE_MODE = "light"
    COLOR_THEME = "blue"

    @classmethod
    def configure_customtkinter(cls) -> None:
        """
        Aplica la configuración global de CustomTkinter.

        Debe ejecutarse una sola vez antes de crear la ventana principal.
        """
        try:
            import customtkinter as ctk

            ctk.set_appearance_mode(cls.APPEARANCE_MODE)
            ctk.set_default_color_theme(cls.COLOR_THEME)
        except ImportError as exc:
            raise ImportError(
                "CustomTkinter no está instalado. "
                "Ejecuta: pip install customtkinter"
            ) from exc