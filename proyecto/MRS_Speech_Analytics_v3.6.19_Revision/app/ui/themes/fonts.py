"""
Fuentes y tamaños tipográficos de MRS Speech Analytics Professional.

CustomTkinter permite crear fuentes con CTkFont. Para evitar que este
archivo dependa directamente de CustomTkinter, aquí solo definimos
familias, tamaños y pesos.
"""


class FontFamily:
    PRIMARY = "Segoe UI"
    SECONDARY = "Arial"
    MONOSPACE = "Consolas"


class FontSize:
    DISPLAY = 30
    TITLE_LARGE = 24
    TITLE = 20
    SUBTITLE = 17
    BODY_LARGE = 15
    BODY = 14
    BODY_SMALL = 13
    CAPTION = 12
    MINI = 11


class FontWeight:
    NORMAL = "normal"
    MEDIUM = "normal"
    SEMIBOLD = "bold"
    BOLD = "bold"


class Fonts:
    FAMILY = FontFamily.PRIMARY
    FAMILY_SECONDARY = FontFamily.SECONDARY
    FAMILY_MONOSPACE = FontFamily.MONOSPACE

    DISPLAY = (FAMILY, FontSize.DISPLAY, FontWeight.BOLD)
    TITLE_LARGE = (FAMILY, FontSize.TITLE_LARGE, FontWeight.BOLD)
    TITLE = (FAMILY, FontSize.TITLE, FontWeight.BOLD)
    SUBTITLE = (FAMILY, FontSize.SUBTITLE, FontWeight.BOLD)

    BODY_LARGE = (FAMILY, FontSize.BODY_LARGE, FontWeight.NORMAL)
    BODY_LARGE_BOLD = (FAMILY, FontSize.BODY_LARGE, FontWeight.BOLD)

    BODY = (FAMILY, FontSize.BODY, FontWeight.NORMAL)
    BODY_BOLD = (FAMILY, FontSize.BODY, FontWeight.BOLD)

    BODY_SMALL = (FAMILY, FontSize.BODY_SMALL, FontWeight.NORMAL)
    BODY_SMALL_BOLD = (FAMILY, FontSize.BODY_SMALL, FontWeight.BOLD)

    CAPTION = (FAMILY, FontSize.CAPTION, FontWeight.NORMAL)
    CAPTION_BOLD = (FAMILY, FontSize.CAPTION, FontWeight.BOLD)

    MINI = (FAMILY, FontSize.MINI, FontWeight.NORMAL)

    MONOSPACE = (FAMILY_MONOSPACE, FontSize.BODY_SMALL, FontWeight.NORMAL)