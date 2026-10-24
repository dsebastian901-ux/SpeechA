"""
Estilos reutilizables para CustomTkinter.

Los métodos devuelven diccionarios que pueden enviarse directamente
como argumentos al crear widgets.
"""

from .colors import Colors
from .fonts import Fonts
from .dimensions import Dimensions


class Styles:
    @staticmethod
    def primary_button() -> dict:
        return {
            "fg_color": Colors.PRIMARY,
            "hover_color": Colors.PRIMARY_HOVER,
            "text_color": Colors.TEXT_ON_PRIMARY,
            "corner_radius": Dimensions.RADIUS,
            "height": Dimensions.BUTTON_HEIGHT,
            "font": Fonts.BODY_BOLD,
            "border_width": 0,
        }

    @staticmethod
    def secondary_button() -> dict:
        return {
            "fg_color": Colors.PRIMARY_LIGHT,
            "hover_color": Colors.SIDEBAR_SELECTED,
            "text_color": Colors.PRIMARY_DARK,
            "corner_radius": Dimensions.RADIUS,
            "height": Dimensions.BUTTON_HEIGHT,
            "font": Fonts.BODY_BOLD,
            "border_width": 0,
        }

    @staticmethod
    def outline_button() -> dict:
        return {
            "fg_color": Colors.SURFACE,
            "hover_color": Colors.SURFACE_HOVER,
            "text_color": Colors.TEXT_PRIMARY,
            "border_color": Colors.BORDER,
            "border_width": Dimensions.BORDER_WIDTH,
            "corner_radius": Dimensions.RADIUS,
            "height": Dimensions.BUTTON_HEIGHT,
            "font": Fonts.BODY,
        }

    @staticmethod
    def success_button() -> dict:
        return {
            "fg_color": Colors.SUCCESS,
            "hover_color": Colors.SUCCESS_HOVER,
            "text_color": Colors.TEXT_ON_PRIMARY,
            "corner_radius": Dimensions.RADIUS,
            "height": Dimensions.BUTTON_HEIGHT,
            "font": Fonts.BODY_BOLD,
            "border_width": 0,
        }

    @staticmethod
    def danger_button() -> dict:
        return {
            "fg_color": Colors.ERROR,
            "hover_color": Colors.ERROR_HOVER,
            "text_color": Colors.TEXT_ON_PRIMARY,
            "corner_radius": Dimensions.RADIUS,
            "height": Dimensions.BUTTON_HEIGHT,
            "font": Fonts.BODY_BOLD,
            "border_width": 0,
        }

    @staticmethod
    def icon_button() -> dict:
        return {
            "fg_color": Colors.TRANSPARENT,
            "hover_color": Colors.PRIMARY_LIGHT,
            "text_color": Colors.TEXT_SECONDARY,
            "corner_radius": Dimensions.RADIUS,
            "height": Dimensions.BUTTON_HEIGHT,
            "width": Dimensions.BUTTON_HEIGHT,
            "font": Fonts.BODY_LARGE,
            "border_width": 0,
        }

    @staticmethod
    def entry() -> dict:
        return {
            "fg_color": Colors.SURFACE,
            "text_color": Colors.TEXT_PRIMARY,
            "placeholder_text_color": Colors.TEXT_MUTED,
            "border_color": Colors.BORDER,
            "border_width": Dimensions.BORDER_WIDTH,
            "corner_radius": Dimensions.RADIUS,
            "height": Dimensions.INPUT_HEIGHT,
            "font": Fonts.BODY,
        }

    @staticmethod
    def combobox() -> dict:
        return {
            "fg_color": Colors.SURFACE,
            "button_color": Colors.PRIMARY_LIGHT,
            "button_hover_color": Colors.SIDEBAR_SELECTED,
            "text_color": Colors.TEXT_PRIMARY,
            "dropdown_fg_color": Colors.SURFACE,
            "dropdown_hover_color": Colors.PRIMARY_LIGHT,
            "dropdown_text_color": Colors.TEXT_PRIMARY,
            "border_color": Colors.BORDER,
            "border_width": Dimensions.BORDER_WIDTH,
            "corner_radius": Dimensions.RADIUS,
            "height": Dimensions.COMBOBOX_HEIGHT,
            "font": Fonts.BODY,
            "dropdown_font": Fonts.BODY,
        }

    @staticmethod
    def card() -> dict:
        return {
            "fg_color": Colors.SURFACE,
            "border_color": Colors.BORDER_LIGHT,
            "border_width": Dimensions.BORDER_WIDTH,
            "corner_radius": Dimensions.RADIUS_LARGE,
        }

    @staticmethod
    def sidebar_button(active: bool = False) -> dict:
        if active:
            return {
                "fg_color": Colors.SIDEBAR_SELECTED,
                "hover_color": Colors.SIDEBAR_SELECTED,
                "text_color": Colors.SIDEBAR_TEXT_ACTIVE,
                "corner_radius": Dimensions.RADIUS,
                "height": Dimensions.SIDEBAR_ITEM_HEIGHT,
                "font": Fonts.BODY_BOLD,
                "anchor": "w",
                "border_width": 0,
            }

        return {
            "fg_color": Colors.TRANSPARENT,
            "hover_color": Colors.SIDEBAR_HOVER,
            "text_color": Colors.SIDEBAR_TEXT,
            "corner_radius": Dimensions.RADIUS,
            "height": Dimensions.SIDEBAR_ITEM_HEIGHT,
            "font": Fonts.BODY,
            "anchor": "w",
            "border_width": 0,
        }

    @staticmethod
    def progress_bar() -> dict:
        return {
            "fg_color": Colors.PROGRESS_BACKGROUND,
            "progress_color": Colors.PROGRESS_FILL,
            "corner_radius": Dimensions.RADIUS_PILL,
            "height": Dimensions.PROGRESS_HEIGHT,
        }