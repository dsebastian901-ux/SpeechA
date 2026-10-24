"""
============================================================
MRS Speech Analytics Professional
Vista: Reportes
============================================================
"""


from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox

from app.core import project_manager
from app.services.report_service import ReportService
from app.ui.themes import Theme


class ReportsView(ctk.CTkFrame):
    """
    Vista de generación y exportación de reportes.

    Utiliza exclusivamente los Analytics previamente guardados.
    No vuelve a transcribir ni analizar llamadas.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        self.report_data = {}

        self.grid_columnconfigure(
            0,
            weight=1,
        )

        self.grid_rowconfigure(
            1,
            weight=1,
        )

        self._build_header()
        self._build_content()

        self.load_report()

    # =========================================================
    # HEADER
    # =========================================================

    def _build_header(self):
        self.header = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        self.header.grid(
            row=0,
            column=0,
            padx=20,
            pady=(20, 10),
            sticky="ew",
        )

        self.header.grid_columnconfigure(
            0,
            weight=1,
        )

        # -----------------------------------------------------
        # TÍTULO
        # -----------------------------------------------------

        ctk.CTkLabel(
            self.header,
            text="REPORTES",
            text_color=Theme.colors.PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=26,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=0,
            column=0,
            padx=24,
            pady=(18, 4),
            sticky="w",
        )

        # -----------------------------------------------------
        # PROYECTO
        # -----------------------------------------------------

        self.project_label = ctk.CTkLabel(
            self.header,
            text="Proyecto: Sin proyecto abierto",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
            anchor="w",
        )

        self.project_label.grid(
            row=1,
            column=0,
            padx=24,
            pady=(0, 18),
            sticky="w",
        )

        # -----------------------------------------------------
        # ACTUALIZAR
        # -----------------------------------------------------

        self.refresh_button = ctk.CTkButton(
            self.header,
            text="Actualizar",
            width=110,
            height=36,
            fg_color=Theme.colors.PRIMARY,
            hover_color="#6652A8",
            corner_radius=9,
            command=self.load_report,
        )

        self.refresh_button.grid(
            row=0,
            column=1,
            rowspan=2,
            padx=24,
            pady=18,
            sticky="e",
        )

    # =========================================================
    # CONTENIDO
    # =========================================================

    def _build_content(self):
        self.content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )

        self.content.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 20),
            sticky="nsew",
        )

        self.content.grid_columnconfigure(
            0,
            weight=1,
        )

        self._build_summary_section()
        self._build_export_section()
        self._build_calls_section()

        # -----------------------------------------------------
        # ESTADO
        # -----------------------------------------------------

        self.status_label = ctk.CTkLabel(
            self.content,
            text="",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        )

        self.status_label.grid(
            row=3,
            column=0,
            padx=4,
            pady=(12, 4),
            sticky="ew",
        )

    # =========================================================
    # RESUMEN
    # =========================================================

    def _build_summary_section(self):
        self.summary_frame = ctk.CTkFrame(
            self.content,
            fg_color="transparent",
        )

        self.summary_frame.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        for column in range(4):
            self.summary_frame.grid_columnconfigure(
                column,
                weight=1,
                uniform="report_kpi",
            )

        self.total_value = self._create_summary_card(
            column=0,
            title="Llamadas analizadas",
            value="0",
            background="#EEF5FF",
        )

        self.compliance_value = self._create_summary_card(
            column=1,
            title="Cumplimiento promedio",
            value="0%",
            background="#EEF9F2",
        )

        self.positive_value = self._create_summary_card(
            column=2,
            title="Sentimiento positivo",
            value="0",
            background="#F2EEFF",
        )

        self.negative_value = self._create_summary_card(
            column=3,
            title="Sentimiento negativo",
            value="0",
            background="#FFF5E9",
        )

    # =========================================================
    # TARJETA RESUMEN
    # =========================================================

    def _create_summary_card(
        self,
        column: int,
        title: str,
        value: str,
        background: str,
    ):
        card = ctk.CTkFrame(
            self.summary_frame,
            fg_color=background,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        card.grid(
            row=0,
            column=column,
            padx=5,
            sticky="nsew",
        )

        ctk.CTkLabel(
            card,
            text=title,
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold",
            ),
            anchor="w",
        ).pack(
            anchor="w",
            padx=18,
            pady=(16, 5),
        )

        value_label = ctk.CTkLabel(
            card,
            text=value,
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=22,
                weight="bold",
            ),
            anchor="w",
        )

        value_label.pack(
            anchor="w",
            padx=18,
            pady=(0, 17),
        )

        return value_label

    # =========================================================
    # EXPORTACIONES
    # =========================================================

    def _build_export_section(self):
        self.export_panel = ctk.CTkFrame(
            self.content,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        self.export_panel.grid(
            row=1,
            column=0,
            pady=(12, 0),
            sticky="ew",
        )

        self.export_panel.grid_columnconfigure(
            0,
            weight=1,
        )

        # -----------------------------------------------------
        # TEXTO
        # -----------------------------------------------------

        text_frame = ctk.CTkFrame(
            self.export_panel,
            fg_color="transparent",
        )

        text_frame.grid(
            row=0,
            column=0,
            padx=20,
            pady=18,
            sticky="w",
        )

        ctk.CTkLabel(
            text_frame,
            text="Exportar reporte",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold",
            ),
            anchor="w",
        ).pack(
            anchor="w",
        )

        ctk.CTkLabel(
            text_frame,
            text=(
                "Los archivos se guardarán en "
                "04_Reportes\\Exportados."
            ),
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        ).pack(
            anchor="w",
            pady=(3, 0),
        )

        # -----------------------------------------------------
        # BOTONES
        # -----------------------------------------------------

        buttons_frame = ctk.CTkFrame(
            self.export_panel,
            fg_color="transparent",
        )

        buttons_frame.grid(
            row=0,
            column=1,
            padx=20,
            pady=18,
            sticky="e",
        )

        self.json_button = ctk.CTkButton(
            buttons_frame,
            text="Exportar JSON",
            width=130,
            height=38,
            fg_color="#7667D9",
            hover_color="#6657C8",
            corner_radius=9,
            command=self.export_json,
        )

        self.json_button.grid(
            row=0,
            column=0,
            padx=(0, 8),
        )

        self.csv_button = ctk.CTkButton(
            buttons_frame,
            text="Exportar CSV",
            width=130,
            height=38,
            fg_color="#5B8DEF",
            hover_color="#4A7CDE",
            corner_radius=9,
            command=self.export_csv,
        )

        self.csv_button.grid(
            row=0,
            column=1,
        )

    # =========================================================
    # LISTADO DE LLAMADAS
    # =========================================================

    def _build_calls_section(self):
        self.calls_panel = ctk.CTkFrame(
            self.content,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        self.calls_panel.grid(
            row=2,
            column=0,
            pady=(12, 0),
            sticky="ew",
        )

        self.calls_panel.grid_columnconfigure(
            0,
            weight=1,
        )

        ctk.CTkLabel(
            self.calls_panel,
            text="Detalle de llamadas analizadas",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=0,
            column=0,
            padx=20,
            pady=(18, 4),
            sticky="ew",
        )

        self.calls_count_label = ctk.CTkLabel(
            self.calls_panel,
            text="0 registros",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        )

        self.calls_count_label.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 12),
            sticky="ew",
        )

        self.calls_container = ctk.CTkFrame(
            self.calls_panel,
            fg_color="transparent",
        )

        self.calls_container.grid(
            row=2,
            column=0,
            padx=20,
            pady=(0, 20),
            sticky="ew",
        )

        self.calls_container.grid_columnconfigure(
            0,
            weight=1,
        )

    # =========================================================
    # CARGAR REPORTE
    # =========================================================

    def load_report(self):
        project_path = self._get_active_project_path()

        if project_path is None:
            self.project_label.configure(
                text="Proyecto: Sin proyecto abierto"
            )

            self._clear_report()

            self.status_label.configure(
                text="Abra un proyecto para consultar los reportes."
            )

            return

        self.project_label.configure(
            text=f"Proyecto: {self._get_active_project_name()}"
        )

        try:
            self.refresh_button.configure(
                state="disabled",
                text="Actualizando...",
            )

            self.update_idletasks()

            data = ReportService.get_report_data(
                project_path
            )

            self.report_data = data

            self._display_report(
                data
            )

            total = self._safe_int(
                data.get(
                    "total_calls",
                    0,
                )
            )

            if total == 0:
                self.status_label.configure(
                    text=(
                        "No existen Analytics guardados "
                        "para generar reportes."
                    )
                )
            else:
                self.status_label.configure(
                    text=(
                        f"Reporte cargado correctamente · "
                        f"{total} llamada"
                        f"{'' if total == 1 else 's'}."
                    )
                )

        except Exception as error:
            self._clear_report()

            self.status_label.configure(
                text="No fue posible cargar el reporte."
            )

            messagebox.showerror(
                "Reportes",
                "No fue posible cargar los datos.\n\n"
                f"Detalle: {error}",
            )

        finally:
            self.refresh_button.configure(
                state="normal",
                text="Actualizar",
            )

    # =========================================================
    # MOSTRAR REPORTE
    # =========================================================

    def _display_report(
        self,
        data,
    ):
        total = self._safe_int(
            data.get(
                "total_calls",
                0,
            )
        )

        compliance = self._safe_float(
            data.get(
                "average_compliance",
                0.0,
            )
        )

        sentiments = data.get(
            "sentiment_distribution",
            {},
        ) or {}

        positive = self._safe_int(
            sentiments.get(
                "positivo",
                0,
            )
        )

        negative = self._safe_int(
            sentiments.get(
                "negativo",
                0,
            )
        )

        self.total_value.configure(
            text=str(total)
        )

        self.compliance_value.configure(
            text=f"{compliance:.0f}%"
        )

        self.positive_value.configure(
            text=str(positive)
        )

        self.negative_value.configure(
            text=str(negative)
        )

        calls = data.get(
            "calls",
            [],
        ) or []

        self._render_calls(
            calls
        )

    # =========================================================
    # RENDER DE LLAMADAS
    # =========================================================

    def _render_calls(
        self,
        calls,
    ):
        for widget in self.calls_container.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        total = len(
            calls
        )

        self.calls_count_label.configure(
            text=(
                f"{total} registro"
                f"{'' if total == 1 else 's'}"
            )
        )

        if not calls:
            ctk.CTkLabel(
                self.calls_container,
                text="Sin llamadas analizadas.",
                text_color=Theme.colors.TEXT_SECONDARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=12,
                ),
                anchor="w",
            ).grid(
                row=0,
                column=0,
                padx=10,
                pady=18,
                sticky="w",
            )

            return

        # -----------------------------------------------------
        # CABECERA
        # -----------------------------------------------------

        header = ctk.CTkFrame(
            self.calls_container,
            fg_color="#F0F1F7",
            corner_radius=8,
        )

        header.grid(
            row=0,
            column=0,
            pady=(0, 5),
            sticky="ew",
        )

        header.grid_columnconfigure(
            0,
            weight=3,
        )

        header.grid_columnconfigure(
            1,
            weight=2,
        )

        header.grid_columnconfigure(
            2,
            weight=1,
        )

        header.grid_columnconfigure(
            3,
            weight=1,
        )

        header.grid_columnconfigure(
            4,
            weight=1,
        )

        self._create_header_label(
            header,
            0,
            "Archivo",
        )

        self._create_header_label(
            header,
            1,
            "Motivo",
        )

        self._create_header_label(
            header,
            2,
            "Sentimiento",
        )

        self._create_header_label(
            header,
            3,
            "Cumplimiento",
        )

        self._create_header_label(
            header,
            4,
            "Puntaje",
        )

        # -----------------------------------------------------
        # FILAS
        # -----------------------------------------------------

        for index, call in enumerate(
            calls,
            start=1,
        ):
            self._create_call_row(
                index,
                call,
            )

    # =========================================================
    # CABECERA DE COLUMNA
    # =========================================================

    @staticmethod
    def _create_header_label(
        parent,
        column,
        text,
    ):
        ctk.CTkLabel(
            parent,
            text=text,
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=0,
            column=column,
            padx=10,
            pady=9,
            sticky="ew",
        )

    # =========================================================
    # FILA DE LLAMADA
    # =========================================================

    def _create_call_row(
        self,
        row,
        call,
    ):
        item = ctk.CTkFrame(
            self.calls_container,
            fg_color="#FAFAFD",
            corner_radius=8,
            border_width=1,
            border_color="#EEEEF4",
        )

        item.grid(
            row=row,
            column=0,
            pady=3,
            sticky="ew",
        )

        item.grid_columnconfigure(
            0,
            weight=3,
        )

        item.grid_columnconfigure(
            1,
            weight=2,
        )

        item.grid_columnconfigure(
            2,
            weight=1,
        )

        item.grid_columnconfigure(
            3,
            weight=1,
        )

        item.grid_columnconfigure(
            4,
            weight=1,
        )

        audio_file = str(
            call.get(
                "audio_file",
                "",
            )
            or ""
        )

        if audio_file:
            audio_file = Path(
                audio_file
            ).name

        reason = str(
            call.get(
                "call_reason",
                "",
            )
            or "No identificado"
        )

        sentiment = str(
            call.get(
                "sentiment",
                "",
            )
            or "neutral"
        ).capitalize()

        compliance_status = str(
            call.get(
                "compliance_status",
                "",
            )
            or "Sin dato"
        ).replace(
            "_",
            " ",
        ).capitalize()

        score = self._safe_float(
            call.get(
                "compliance_score",
                0,
            )
        )

        values = [
            audio_file or "Sin archivo",
            reason,
            sentiment,
            compliance_status,
            f"{score:.0f}%",
        ]

        for column, value in enumerate(
            values
        ):
            ctk.CTkLabel(
                item,
                text=value,
                text_color=Theme.colors.TEXT_SECONDARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=11,
                ),
                anchor="w",
            ).grid(
                row=0,
                column=column,
                padx=10,
                pady=10,
                sticky="ew",
            )

    # =========================================================
    # EXPORTAR JSON
    # =========================================================

    def export_json(self):
        project_path = self._get_active_project_path()

        if project_path is None:
            messagebox.showwarning(
                "Reportes",
                "No hay un proyecto abierto.",
            )
            return

        try:
            self._set_export_buttons(
                False
            )

            output = ReportService.export_json(
                project_path
            )

            self.status_label.configure(
                text=f"✓ JSON exportado: {output.name}"
            )

            messagebox.showinfo(
                "Reportes",
                "Reporte JSON generado correctamente.\n\n"
                f"{output}",
            )

        except Exception as error:
            messagebox.showerror(
                "Reportes",
                "No fue posible exportar el JSON.\n\n"
                f"Detalle: {error}",
            )

        finally:
            self._set_export_buttons(
                True
            )

    # =========================================================
    # EXPORTAR CSV
    # =========================================================

    def export_csv(self):
        project_path = self._get_active_project_path()

        if project_path is None:
            messagebox.showwarning(
                "Reportes",
                "No hay un proyecto abierto.",
            )
            return

        try:
            self._set_export_buttons(
                False
            )

            output = ReportService.export_csv(
                project_path
            )

            self.status_label.configure(
                text=f"✓ CSV exportado: {output.name}"
            )

            messagebox.showinfo(
                "Reportes",
                "Reporte CSV generado correctamente.\n\n"
                f"{output}",
            )

        except Exception as error:
            messagebox.showerror(
                "Reportes",
                "No fue posible exportar el CSV.\n\n"
                f"Detalle: {error}",
            )

        finally:
            self._set_export_buttons(
                True
            )

    # =========================================================
    # BOTONES EXPORTACIÓN
    # =========================================================

    def _set_export_buttons(
        self,
        enabled: bool,
    ):
        state = (
            "normal"
            if enabled
            else "disabled"
        )

        self.json_button.configure(
            state=state
        )

        self.csv_button.configure(
            state=state
        )

    # =========================================================
    # LIMPIAR
    # =========================================================

    def _clear_report(self):
        self.report_data = {}

        self.total_value.configure(
            text="0"
        )

        self.compliance_value.configure(
            text="0%"
        )

        self.positive_value.configure(
            text="0"
        )

        self.negative_value.configure(
            text="0"
        )

        self._render_calls(
            []
        )

    # =========================================================
    # UTILIDADES
    # =========================================================

    @staticmethod
    def _safe_int(
        value,
    ) -> int:
        try:
            return max(
                int(
                    value
                    or 0
                ),
                0,
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0

    @staticmethod
    def _safe_float(
        value,
    ) -> float:
        try:
            return float(
                value
                or 0.0
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0.0

    # =========================================================
    # PROYECTO ACTIVO
    # =========================================================

    def _get_active_project_path(
        self,
    ) -> Optional[Path]:
        try:
            get_path = getattr(
                project_manager,
                "get_project_path",
                None,
            )

            if callable(get_path):
                path = get_path()

                if path:
                    return (
                        Path(path)
                        .expanduser()
                        .resolve()
                    )

            get_current = getattr(
                project_manager,
                "get_current_project",
                None,
            )

            if callable(get_current):
                project = get_current()

                if isinstance(
                    project,
                    dict,
                ):
                    raw_path = project.get(
                        "ruta"
                    )

                    if raw_path:
                        return (
                            Path(raw_path)
                            .expanduser()
                            .resolve()
                        )

        except Exception:
            return None

        return None

    def _get_active_project_name(
        self,
    ) -> str:
        try:
            get_name = getattr(
                project_manager,
                "get_project_name",
                None,
            )

            if callable(get_name):
                name = get_name()

                if name:
                    return str(name)

        except Exception:
            pass

        return "Proyecto activo"