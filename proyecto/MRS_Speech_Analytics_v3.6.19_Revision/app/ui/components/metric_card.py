"""
============================================================
MRS Speech Analytics Professional
Componente: Metric Card
============================================================
"""

from __future__ import annotations

import customtkinter as ctk

from app.ui.components.icon_factory import IconFactory
from app.ui.themes import Theme


class MetricCard(ctk.CTkFrame):
    """
    Tarjeta visual para mostrar indicadores y métricas.

    Ejemplos:
    - Número de audios
    - Tamaño total
    - Archivos vacíos
    - Formatos encontrados
    """

    def __init__(
        self,
        parent,
        icon_name: str = "",
        value: str = "0",
        title: str = "",
        subtitle: str = "",
        bg=None,
        icon_color=None,
        **kwargs,
    ):
        # =====================================================
        # COLORES
        # =====================================================

        if bg is None:
            bg = Theme.colors.SURFACE

        if icon_color is None:
            icon_color = Theme.colors.PRIMARY

        # =====================================================
        # FRAME PRINCIPAL
        # =====================================================

        super().__init__(
            parent,
            fg_color=bg,
            corner_radius=16,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
            **kwargs,
        )

        self.icon_name = icon_name
        self.value = str(value)
        self.title = str(title)
        self.subtitle = str(subtitle)
        self.icon_color = icon_color

        self.icon_image = None

        self.grid_columnconfigure(
            0,
            weight=0,
        )

        self.grid_columnconfigure(
            1,
            weight=1,
        )

        self.grid_rowconfigure(
            0,
            weight=1,
        )

        self._build_ui()

    # =========================================================
    # CONSTRUCCIÓN
    # =========================================================

    def _build_ui(self):
        """Construye los elementos internos de la tarjeta."""

        self._build_icon()

        self._build_content()

    # =========================================================
    # ICONO
    # =========================================================

    def _build_icon(self):
        """Construye el contenedor del icono."""

        self.icon_frame = ctk.CTkFrame(
            self,
            width=58,
            height=58,
            fg_color=Theme.colors.SURFACE,
            corner_radius=14,
        )

        self.icon_frame.grid(
            row=0,
            column=0,
            padx=(16, 12),
            pady=16,
            sticky="w",
        )

        self.icon_frame.grid_propagate(
            False
        )

        try:
            self.icon_image = IconFactory.create(
                self.icon_name,
                size=26,
                color=self.icon_color,
            )

            self.icon_label = ctk.CTkLabel(
                self.icon_frame,
                text="",
                image=self.icon_image,
            )

        except Exception:
            # Si un icono no existe, la tarjeta seguirá funcionando.
            self.icon_label = ctk.CTkLabel(
                self.icon_frame,
                text="●",
                text_color=self.icon_color,
                font=ctk.CTkFont(
                    family=Theme.fonts.FAMILY,
                    size=22,
                    weight="bold",
                ),
            )

        self.icon_label.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
        )

    # =========================================================
    # CONTENIDO
    # =========================================================

    def _build_content(self):
        """Construye valor, título y subtítulo."""

        self.content_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        self.content_frame.grid(
            row=0,
            column=1,
            padx=(0, 14),
            pady=13,
            sticky="nsew",
        )

        self.content_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        # =====================================================
        # VALOR
        # =====================================================

        self.value_label = ctk.CTkLabel(
            self.content_frame,
            text=self.value,
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=24,
                weight="bold",
            ),
            anchor="w",
        )

        self.value_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        # =====================================================
        # TÍTULO
        # =====================================================

        self.title_label = ctk.CTkLabel(
            self.content_frame,
            text=self.title,
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=12,
                weight="normal",
            ),
            anchor="w",
        )

        self.title_label.grid(
            row=1,
            column=0,
            pady=(2, 0),
            sticky="w",
        )

        # =====================================================
        # SUBTÍTULO
        # =====================================================

        self.subtitle_label = ctk.CTkLabel(
            self.content_frame,
            text=self.subtitle,
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=10,
            ),
            anchor="w",
        )

        self.subtitle_label.grid(
            row=2,
            column=0,
            pady=(6, 0),
            sticky="w",
        )

    # =========================================================
    # ACTUALIZACIÓN DE VALORES
    # =========================================================

    def set_value(
        self,
        value,
    ):
        """
        Actualiza el valor principal de la tarjeta.
        """

        self.value = str(
            value
        )

        self.value_label.configure(
            text=self.value
        )

    def set_title(
        self,
        title,
    ):
        """Actualiza el título."""

        self.title = str(
            title
        )

        self.title_label.configure(
            text=self.title
        )

    def set_subtitle(
        self,
        subtitle,
    ):
        """Actualiza el subtítulo."""

        self.subtitle = str(
            subtitle
        )

        self.subtitle_label.configure(
            text=self.subtitle
        )

    # =========================================================
    # MÉTODO GENERAL
    # =========================================================

    def update_metric(
        self,
        value=None,
        title=None,
        subtitle=None,
    ):
        """
        Actualiza uno o varios valores de la tarjeta.
        """

        if value is not None:
            self.set_value(
                value
            )

        if title is not None:
            self.set_title(
                title
            )

        if subtitle is not None:
            self.set_subtitle(
                subtitle
            )