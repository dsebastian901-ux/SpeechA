"""
============================================================
MRS Speech Analytics Professional
Vista: Historial
============================================================
"""

from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox

from app.core import project_manager
from app.services.history_service import HistoryService
from app.ui.themes import Theme


class HistoryView(ctk.CTkFrame):
    """
    Vista del historial del proyecto.

    Muestra:
    - Transcripciones
    - Analytics
    - Reportes exportados
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        self.history_data = {}
        self.all_items = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_content()

        self.load_history()

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

        self.header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.header,
            text="HISTORIAL",
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

        self.refresh_button = ctk.CTkButton(
            self.header,
            text="Actualizar",
            width=110,
            height=36,
            fg_color=Theme.colors.PRIMARY,
            hover_color="#6652A8",
            corner_radius=9,
            command=self.load_history,
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

        self.content.grid_columnconfigure(0, weight=1)

        self._build_summary()
        self._build_filters()
        self._build_history_panel()

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

    def _build_summary(self):
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
                uniform="history_kpi",
            )

        self.total_value = self._create_summary_card(
            0,
            "Total registros",
            "0",
            "#EEF5FF",
        )

        self.transcriptions_value = self._create_summary_card(
            1,
            "Transcripciones",
            "0",
            "#F2EEFF",
        )

        self.analytics_value = self._create_summary_card(
            2,
            "Analytics",
            "0",
            "#EEF9F2",
        )

        self.reports_value = self._create_summary_card(
            3,
            "Reportes",
            "0",
            "#FFF5E9",
        )

    def _create_summary_card(
        self,
        column,
        title,
        value,
        background,
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
    # FILTROS
    # =========================================================

    def _build_filters(self):
        self.filters_panel = ctk.CTkFrame(
            self.content,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        self.filters_panel.grid(
            row=1,
            column=0,
            pady=(12, 0),
            sticky="ew",
        )

        self.filters_panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.filters_panel,
            text="Filtrar:",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            padx=(20, 8),
            pady=16,
        )

        self.type_combo = ctk.CTkComboBox(
            self.filters_panel,
            values=[
                "Todos",
                "Transcripciones",
                "Analytics",
                "Reportes",
            ],
            width=170,
            height=36,
            state="readonly",
            command=self._on_filter_changed,
        )

        self.type_combo.grid(
            row=0,
            column=1,
            padx=(0, 12),
            pady=16,
            sticky="w",
        )

        self.type_combo.set("Todos")

        self.search_entry = ctk.CTkEntry(
            self.filters_panel,
            placeholder_text="Buscar por nombre de archivo...",
            height=36,
        )

        self.search_entry.grid(
            row=0,
            column=2,
            padx=(0, 8),
            pady=16,
            sticky="ew",
        )

        self.filters_panel.grid_columnconfigure(2, weight=1)

        self.search_entry.bind(
            "<KeyRelease>",
            self._on_search_changed,
        )

        self.clear_button = ctk.CTkButton(
            self.filters_panel,
            text="Limpiar",
            width=90,
            height=36,
            fg_color="#EDEDF4",
            hover_color="#DEDEE9",
            text_color=Theme.colors.TEXT_PRIMARY,
            corner_radius=9,
            command=self.clear_filters,
        )

        self.clear_button.grid(
            row=0,
            column=3,
            padx=(0, 20),
            pady=16,
        )

    # =========================================================
    # PANEL HISTORIAL
    # =========================================================

    def _build_history_panel(self):
        self.history_panel = ctk.CTkFrame(
            self.content,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        self.history_panel.grid(
            row=2,
            column=0,
            pady=(12, 0),
            sticky="ew",
        )

        self.history_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.history_panel,
            text="Actividad del proyecto",
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

        self.count_label = ctk.CTkLabel(
            self.history_panel,
            text="0 registros",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        )

        self.count_label.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 12),
            sticky="ew",
        )

        self.items_container = ctk.CTkFrame(
            self.history_panel,
            fg_color="transparent",
        )

        self.items_container.grid(
            row=2,
            column=0,
            padx=20,
            pady=(0, 20),
            sticky="ew",
        )

        self.items_container.grid_columnconfigure(0, weight=1)

    # =========================================================
    # CARGAR HISTORIAL
    # =========================================================

    def load_history(self):
        project_path = self._get_active_project_path()

        if project_path is None:
            self.project_label.configure(
                text="Proyecto: Sin proyecto abierto"
            )

            self._clear_history()

            self.status_label.configure(
                text="Abra un proyecto para consultar el historial."
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

            data = HistoryService.get_history_data(
                project_path
            )

            self.history_data = data

            self.all_items = data.get(
                "items",
                [],
            ) or []

            counts = data.get(
                "counts",
                {},
            ) or {}

            self.total_value.configure(
                text=str(
                    data.get(
                        "total_items",
                        0,
                    )
                )
            )

            self.transcriptions_value.configure(
                text=str(
                    counts.get(
                        "transcriptions",
                        0,
                    )
                )
            )

            self.analytics_value.configure(
                text=str(
                    counts.get(
                        "analytics",
                        0,
                    )
                )
            )

            self.reports_value.configure(
                text=str(
                    counts.get(
                        "reports",
                        0,
                    )
                )
            )

            self.apply_filters()

            total = len(self.all_items)

            self.status_label.configure(
                text=(
                    f"Historial actualizado · "
                    f"{total} registro"
                    f"{'' if total == 1 else 's'}."
                )
            )

        except Exception as error:
            self._clear_history()

            self.status_label.configure(
                text="No fue posible cargar el historial."
            )

            messagebox.showerror(
                "Historial",
                "No fue posible cargar el historial.\n\n"
                f"Detalle: {error}",
            )

        finally:
            self.refresh_button.configure(
                state="normal",
                text="Actualizar",
            )

    # =========================================================
    # FILTRAR
    # =========================================================

    def apply_filters(self):
        selected = self.type_combo.get()

        type_map = {
            "Todos": "all",
            "Transcripciones": "transcription",
            "Analytics": "analytics",
            "Reportes": "report",
        }

        item_type = type_map.get(
            selected,
            "all",
        )

        search_text = self.search_entry.get()

        filtered = HistoryService.filter_items(
            self.all_items,
            item_type=item_type,
            search_text=search_text,
        )

        self._render_items(
            filtered
        )

    def _on_filter_changed(
        self,
        _value=None,
    ):
        self.apply_filters()

    def _on_search_changed(
        self,
        _event=None,
    ):
        self.apply_filters()

    def clear_filters(self):
        self.type_combo.set(
            "Todos"
        )

        self.search_entry.delete(
            0,
            "end",
        )

        self.apply_filters()

    # =========================================================
    # RENDER
    # =========================================================

    def _render_items(
        self,
        items,
    ):
        for widget in self.items_container.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        total = len(items)

        self.count_label.configure(
            text=(
                f"{total} registro"
                f"{'' if total == 1 else 's'}"
            )
        )

        if not items:
            ctk.CTkLabel(
                self.items_container,
                text="No hay registros para mostrar.",
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

        self._create_table_header()

        for row, item in enumerate(
            items,
            start=1,
        ):
            self._create_item_row(
                row,
                item,
            )

    # =========================================================
    # CABECERA
    # =========================================================

    def _create_table_header(self):
        header = ctk.CTkFrame(
            self.items_container,
            fg_color="#F0F1F7",
            corner_radius=8,
        )

        header.grid(
            row=0,
            column=0,
            pady=(0, 5),
            sticky="ew",
        )

        header.grid_columnconfigure(0, weight=2)
        header.grid_columnconfigure(1, weight=5)
        header.grid_columnconfigure(2, weight=2)
        header.grid_columnconfigure(3, weight=1)

        headers = [
            "Tipo",
            "Archivo",
            "Fecha",
            "Tamaño",
        ]

        for column, text in enumerate(headers):
            ctk.CTkLabel(
                header,
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
    # FILA
    # =========================================================

    def _create_item_row(
        self,
        row,
        item,
    ):
        item_frame = ctk.CTkFrame(
            self.items_container,
            fg_color="#FAFAFD",
            corner_radius=8,
            border_width=1,
            border_color="#EEEEF4",
        )

        item_frame.grid(
            row=row,
            column=0,
            pady=3,
            sticky="ew",
        )

        item_frame.grid_columnconfigure(0, weight=2)
        item_frame.grid_columnconfigure(1, weight=5)
        item_frame.grid_columnconfigure(2, weight=2)
        item_frame.grid_columnconfigure(3, weight=1)

        values = [
            str(
                item.get(
                    "type_label",
                    "",
                )
            ),
            str(
                item.get(
                    "file_name",
                    "",
                )
            ),
            str(
                item.get(
                    "modified_display",
                    "",
                )
            ),
            str(
                item.get(
                    "size_display",
                    "",
                )
            ),
        ]

        for column, value in enumerate(values):
            ctk.CTkLabel(
                item_frame,
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
    # LIMPIAR
    # =========================================================

    def _clear_history(self):
        self.history_data = {}
        self.all_items = []

        self.total_value.configure(
            text="0"
        )

        self.transcriptions_value.configure(
            text="0"
        )

        self.analytics_value.configure(
            text="0"
        )

        self.reports_value.configure(
            text="0"
        )

        self._render_items(
            []
        )

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