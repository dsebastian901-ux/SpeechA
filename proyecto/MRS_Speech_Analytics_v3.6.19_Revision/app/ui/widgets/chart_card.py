"""
============================================================
MRS Speech Analytics Professional
Widget: Chart Card
============================================================
"""

from __future__ import annotations

from typing import Dict, Optional

import customtkinter as ctk

from app.ui.themes import Theme


class ChartCard(ctk.CTkFrame):
    """
    Tarjeta reutilizable para visualizar distribuciones
    mediante barras horizontales.

    Puede utilizarse para:
    - Sentimientos
    - Cumplimiento
    - Motivos de llamada
    - Otras distribuciones del Dashboard
    """

    def __init__(
        self,
        parent,
        title: str,
        data: Optional[Dict[str, int]] = None,
        height: int = 240,
        bar_color: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
            height=height,
            **kwargs,
        )

        self.title = str(title or "")
        self.data = dict(data or {})

        self.bar_color = (
            bar_color
            if bar_color
            else Theme.colors.PRIMARY
        )

        self.grid_columnconfigure(
            0,
            weight=1,
        )

        self.grid_rowconfigure(
            1,
            weight=1,
        )

        self._build_ui()

    # =========================================================
    # CONSTRUCCIÓN
    # =========================================================

    def _build_ui(self):
        self._build_header()
        self._build_chart_area()

    # =========================================================
    # HEADER
    # =========================================================

    def _build_header(self):
        self.header = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        self.header.grid(
            row=0,
            column=0,
            padx=16,
            pady=(14, 7),
            sticky="ew",
        )

        self.header.grid_columnconfigure(
            0,
            weight=1,
        )

        self.title_label = ctk.CTkLabel(
            self.header,
            text=self.title,
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold",
            ),
            anchor="w",
        )

        self.title_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.total_label = ctk.CTkLabel(
            self.header,
            text="Total: 0",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="e",
        )

        self.total_label.grid(
            row=0,
            column=1,
            padx=(10, 0),
            sticky="e",
        )

    # =========================================================
    # ÁREA DE GRÁFICA
    # =========================================================

    def _build_chart_area(self):
        self.chart_area = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        self.chart_area.grid(
            row=1,
            column=0,
            padx=16,
            pady=(0, 14),
            sticky="nsew",
        )

        self.chart_area.grid_columnconfigure(
            0,
            weight=1,
        )

        self.render()

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        """
        Redibuja completamente las barras.
        """

        self._clear_chart()

        normalized_data = self._normalize_data(
            self.data
        )

        total = sum(
            normalized_data.values()
        )

        self.total_label.configure(
            text=f"Total: {total}"
        )

        if not normalized_data or total <= 0:
            self._show_empty_state()
            return

        maximum = max(
            normalized_data.values()
        )

        for row, (label, value) in enumerate(
            normalized_data.items()
        ):
            self._create_bar_row(
                row=row,
                label=label,
                value=value,
                total=total,
                maximum=maximum,
            )

    # =========================================================
    # BARRA
    # =========================================================

    def _create_bar_row(
        self,
        row: int,
        label: str,
        value: int,
        total: int,
        maximum: int,
    ):
        container = ctk.CTkFrame(
            self.chart_area,
            fg_color="transparent",
        )

        container.grid(
            row=row,
            column=0,
            pady=6,
            sticky="ew",
        )

        container.grid_columnconfigure(
            0,
            weight=1,
        )

        # -----------------------------------------------------
        # TEXTO SUPERIOR
        # -----------------------------------------------------

        info_frame = ctk.CTkFrame(
            container,
            fg_color="transparent",
        )

        info_frame.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        info_frame.grid_columnconfigure(
            0,
            weight=1,
        )

        ctk.CTkLabel(
            info_frame,
            text=self._format_label(label),
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        percentage = (
            (value / total) * 100
            if total > 0
            else 0
        )

        ctk.CTkLabel(
            info_frame,
            text=f"{value} · {percentage:.0f}%",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold",
            ),
            anchor="e",
        ).grid(
            row=0,
            column=1,
            padx=(10, 0),
            sticky="e",
        )

        # -----------------------------------------------------
        # FONDO DE BARRA
        # -----------------------------------------------------

        bar_background = ctk.CTkFrame(
            container,
            height=12,
            fg_color=Theme.colors.PROGRESS_BACKGROUND,
            corner_radius=6,
        )

        bar_background.grid(
            row=1,
            column=0,
            pady=(5, 0),
            sticky="ew",
        )

        bar_background.grid_propagate(
            False
        )

        ratio = (
            value / maximum
            if maximum > 0
            else 0
        )

        ratio = max(
            0.0,
            min(
                float(ratio),
                1.0,
            ),
        )

        if ratio > 0:
            bar = ctk.CTkFrame(
                bar_background,
                fg_color=self.bar_color,
                corner_radius=6,
            )

            bar.place(
                relx=0,
                rely=0,
                relwidth=ratio,
                relheight=1,
            )

    # =========================================================
    # SIN DATOS
    # =========================================================

    def _show_empty_state(self):
        ctk.CTkLabel(
            self.chart_area,
            text="Sin datos disponibles",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=30,
        )

    # =========================================================
    # LIMPIAR
    # =========================================================

    def _clear_chart(self):
        for widget in self.chart_area.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

    # =========================================================
    # ACTUALIZAR DATOS
    # =========================================================

    def set_data(
        self,
        data: Optional[Dict[str, int]],
    ):
        self.data = dict(
            data or {}
        )

        self.render()

    # =========================================================
    # ACTUALIZAR TÍTULO
    # =========================================================

    def set_title(
        self,
        title: str,
    ):
        self.title = str(
            title or ""
        )

        self.title_label.configure(
            text=self.title
        )

    # =========================================================
    # ACTUALIZAR COLOR
    # =========================================================

    def set_bar_color(
        self,
        color: str,
    ):
        if not color:
            return

        self.bar_color = color
        self.render()

    # =========================================================
    # NORMALIZAR DATOS
    # =========================================================

    @staticmethod
    def _normalize_data(
        data,
    ) -> Dict[str, int]:
        if not isinstance(
            data,
            dict,
        ):
            return {}

        result: Dict[str, int] = {}

        for key, value in data.items():
            label = str(
                key
                or ""
            ).strip()

            if not label:
                continue

            try:
                numeric_value = int(
                    value
                    or 0
                )

            except (
                TypeError,
                ValueError,
            ):
                numeric_value = 0

            result[label] = max(
                numeric_value,
                0,
            )

        return result

    # =========================================================
    # FORMATO DE ETIQUETA
    # =========================================================

    @staticmethod
    def _format_label(
        label: str,
    ) -> str:
        clean = str(
            label
            or ""
        ).strip()

        clean = clean.replace(
            "_",
            " ",
        )

        if not clean:
            return "Sin categoría"

        return clean.capitalize()