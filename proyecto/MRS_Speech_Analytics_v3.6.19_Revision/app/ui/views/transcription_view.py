"""
============================================================
MRS Speech Analytics Professional
Vista: Transcripciones
============================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import customtkinter as ctk
from tkinter import messagebox

from app.core import project_manager
from app.models.transcriptions import TranscriptionModel

try:
    from app.services.transcription_service import TranscriptionService
except ImportError:
    from app.services.transcription_services import TranscriptionService

from app.ui.themes import Theme


class TranscriptionView(ctk.CTkFrame):
    """Consulta, busca, edita y guarda transcripciones del proyecto activo."""

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        self.transcriptions: List[TranscriptionModel] = []
        self.filtered_transcriptions: List[TranscriptionModel] = []
        self.selected_transcription: Optional[TranscriptionModel] = None
        self.list_buttons: Dict[int, ctk.CTkButton] = {}
        self.transcriptions_directory: Optional[Path] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

        self.search_entry.bind("<KeyRelease>", self._on_search_changed)
        self.after_idle(self.load_transcriptions)

    # =========================================================
    # INTERFAZ
    # =========================================================

    def _build_header(self):
        self.header = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.SURFACE,
            corner_radius=16,
            border_width=1,
            border_color="#E7E7F2",
        )
        self.header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(20, 10),
        )
        self.header.grid_columnconfigure(1, weight=1)

        title_box = ctk.CTkFrame(self.header, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=24, pady=18, sticky="w")

        ctk.CTkLabel(
            title_box,
            text="TRANSCRIPCIONES",
            text_color=Theme.colors.PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=25,
                weight="bold",
            ),
        ).pack(anchor="w")

        self.project_label = ctk.CTkLabel(
            title_box,
            text="Proyecto: --",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.project_label.pack(anchor="w", pady=(3, 0))

        self.search_entry = ctk.CTkEntry(
            self.header,
            width=330,
            height=40,
            placeholder_text="Buscar por archivo o contenido...",
            fg_color="#FFFFFF",
            border_color="#DCDCEC",
            text_color=Theme.colors.TEXT_PRIMARY,
            placeholder_text_color="#8E8EA0",
            corner_radius=10,
        )
        self.search_entry.grid(row=0, column=1, padx=(20, 10), sticky="e")

        self.refresh_button = ctk.CTkButton(
            self.header,
            text="Actualizar",
            width=105,
            height=40,
            fg_color=Theme.colors.PRIMARY,
            hover_color="#6652A8",
            corner_radius=10,
            command=self.load_transcriptions,
        )
        self.refresh_button.grid(row=0, column=2, padx=(0, 20))

    def _build_body(self):
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 20),
        )
        self.body.grid_columnconfigure(0, weight=1, minsize=300)
        self.body.grid_columnconfigure(1, weight=3)
        self.body.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        self.left_panel = ctk.CTkFrame(
            self.body,
            fg_color="#F5F0FF",
            corner_radius=16,
            border_width=1,
            border_color="#E6DDFC",
        )
        self.left_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 10),
        )
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self.left_panel,
            text="Transcripciones",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=18,
                weight="bold",
            ),
        ).grid(row=0, column=0, padx=18, pady=(18, 2), sticky="w")

        self.count_label = ctk.CTkLabel(
            self.left_panel,
            text="0 archivos",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.count_label.grid(row=1, column=0, padx=18, pady=(0, 8), sticky="w")

        self.transcription_list = ctk.CTkScrollableFrame(
            self.left_panel,
            fg_color="transparent",
            corner_radius=0,
        )
        self.transcription_list.grid(
            row=2,
            column=0,
            padx=10,
            pady=(0, 12),
            sticky="nsew",
        )
        self.transcription_list.grid_columnconfigure(0, weight=1)

    def _build_right_panel(self):
        self.right_panel = ctk.CTkFrame(
            self.body,
            fg_color=Theme.colors.SURFACE,
            corner_radius=16,
            border_width=1,
            border_color="#E7E7F2",
        )
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        header.grid(row=0, column=0, padx=22, pady=(18, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Vista previa",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=18,
                weight="bold",
            ),
        ).grid(row=0, column=0, sticky="w")

        self.save_button = ctk.CTkButton(
            header,
            text="Guardar cambios",
            width=135,
            height=36,
            state="disabled",
            fg_color=Theme.colors.PRIMARY,
            hover_color="#6652A8",
            corner_radius=9,
            command=self.save_current_transcription,
        )
        self.save_button.grid(row=0, column=1, sticky="e")

        self.file_name_label = ctk.CTkLabel(
            self.right_panel,
            text="Seleccione una transcripción",
            text_color=Theme.colors.PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold",
            ),
            anchor="w",
        )
        self.file_name_label.grid(
            row=1,
            column=0,
            padx=22,
            pady=(0, 6),
            sticky="ew",
        )

        self.metadata_frame = ctk.CTkFrame(
            self.right_panel,
            fg_color="#EEF5FF",
            corner_radius=12,
        )
        self.metadata_frame.grid(
            row=2,
            column=0,
            padx=22,
            pady=(0, 10),
            sticky="ew",
        )
        for column in range(4):
            self.metadata_frame.grid_columnconfigure(column, weight=1)

        self.duration_value = self._create_metadata_item(0, "Duración")
        self.language_value = self._create_metadata_item(1, "Idioma")
        self.date_value = self._create_metadata_item(2, "Fecha")
        self.model_value = self._create_metadata_item(3, "Modelo")

        self.textbox = ctk.CTkTextbox(
            self.right_panel,
            wrap="word",
            fg_color="#FFFFFF",
            text_color=Theme.colors.TEXT_PRIMARY,
            border_width=1,
            border_color="#E5E5EF",
            corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        self.textbox.grid(
            row=3,
            column=0,
            padx=22,
            pady=(0, 12),
            sticky="nsew",
        )
        self.textbox.insert(
            "1.0",
            "Seleccione una transcripción de la lista para visualizarla.",
        )
        self.textbox.configure(state="disabled")

        self.footer_label = ctk.CTkLabel(
            self.right_panel,
            text="",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="w",
        )
        self.footer_label.grid(
            row=4,
            column=0,
            padx=22,
            pady=(0, 14),
            sticky="ew",
        )

    def _create_metadata_item(self, column: int, title: str) -> ctk.CTkLabel:
        frame = ctk.CTkFrame(self.metadata_frame, fg_color="transparent")
        frame.grid(row=0, column=column, padx=14, pady=10, sticky="ew")

        ctk.CTkLabel(
            frame,
            text=title,
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold",
            ),
        ).pack(anchor="w")

        value = ctk.CTkLabel(
            frame,
            text="--",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
        )
        value.pack(anchor="w", pady=(2, 0))
        return value

    # =========================================================
    # CARGA DE DATOS
    # =========================================================

    def load_transcriptions(self):
        self._clear_list()
        self._clear_preview()

        project_path = self._get_active_project_path()

        if project_path is None:
            self.project_label.configure(text="Proyecto: Sin proyecto abierto")
            self._show_empty_message(
                "Abra un proyecto para consultar sus transcripciones."
            )
            return

        self.project_label.configure(
            text=f"Proyecto: {self._get_active_project_name()}"
        )

        try:
            candidate_directories = self._get_candidate_directories(project_path)
            loaded: List[TranscriptionModel] = []
            seen = set()

            for directory in candidate_directories:
                for transcription in TranscriptionService.scan_directory(directory):
                    unique_key = str(
                        transcription.json_path
                        or transcription.txt_path
                        or transcription.file_name
                    ).lower()

                    if unique_key in seen:
                        continue

                    seen.add(unique_key)
                    loaded.append(transcription)

            self.transcriptions = sorted(
                loaded,
                key=lambda item: item.file_name.lower(),
            )
            self.filtered_transcriptions = list(self.transcriptions)

            if candidate_directories:
                self.transcriptions_directory = candidate_directories[0]

            self._render_list(self.filtered_transcriptions)

            if self.transcriptions:
                self.select_transcription(self.transcriptions[0])

        except Exception as error:
            self.transcriptions = []
            self.filtered_transcriptions = []
            self._show_empty_message("No fue posible cargar las transcripciones.")

            messagebox.showerror(
                "Transcripciones",
                "No fue posible cargar las transcripciones.\n\n"
                f"Detalle: {error}",
            )

    def _get_candidate_directories(self, project_path: Path) -> List[Path]:
        candidates: List[Path] = []

        standard = project_path / "03_Transcripciones"
        alternate = project_path / "transcripciones"

        if standard.exists() and standard.is_dir():
            candidates.append(standard.resolve())

        if alternate.exists() and alternate.is_dir():
            resolved = alternate.resolve()
            if resolved not in candidates:
                candidates.append(resolved)

        try:
            for directory in project_path.rglob("*"):
                if (
                    directory.is_dir()
                    and directory.name.lower() == "transcripciones"
                ):
                    resolved = directory.resolve()
                    if resolved not in candidates:
                        candidates.append(resolved)
        except OSError:
            pass

        try:
            service_directory = (
                TranscriptionService.get_transcriptions_directory(project_path)
                .resolve()
            )
            if service_directory not in candidates:
                candidates.insert(0, service_directory)
        except Exception:
            pass

        return candidates

    def _get_active_project_path(self) -> Optional[Path]:
        try:
            get_path = getattr(project_manager, "get_project_path", None)
            if callable(get_path):
                path = get_path()
                if path:
                    return Path(path).expanduser().resolve()

            get_current = getattr(project_manager, "get_current_project", None)
            if callable(get_current):
                project = get_current()
                if isinstance(project, dict):
                    raw_path = project.get("ruta")
                    if raw_path:
                        return Path(raw_path).expanduser().resolve()
        except Exception:
            return None

        return None

    def _get_active_project_name(self) -> str:
        try:
            get_name = getattr(project_manager, "get_project_name", None)
            if callable(get_name):
                return str(get_name() or "Proyecto activo")

            get_current = getattr(project_manager, "get_current_project", None)
            if callable(get_current):
                project = get_current()
                if isinstance(project, dict):
                    return str(project.get("nombre", "Proyecto activo"))
        except Exception:
            pass

        return "Proyecto activo"

    # =========================================================
    # LISTA Y BÚSQUEDA
    # =========================================================

    def _render_list(self, items: List[TranscriptionModel]):
        self._clear_list()

        self.count_label.configure(
            text=(
                f"{len(items)} archivo"
                if len(items) == 1
                else f"{len(items)} archivos"
            )
        )

        if not items:
            self._show_empty_message("No hay transcripciones para mostrar.")
            return

        for index, transcription in enumerate(items):
            button = ctk.CTkButton(
                self.transcription_list,
                text=self._format_list_name(transcription.file_name),
                height=46,
                anchor="w",
                fg_color="#FFFFFF",
                hover_color="#E8DDFB",
                text_color=Theme.colors.TEXT_PRIMARY,
                border_width=1,
                border_color="#E3DDF0",
                corner_radius=10,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                command=lambda item=transcription: self.select_transcription(item),
            )
            button.grid(
                row=index,
                column=0,
                padx=2,
                pady=4,
                sticky="ew",
            )
            self.list_buttons[id(transcription)] = button

    def _on_search_changed(self, _event=None):
        self.filtered_transcriptions = TranscriptionService.search(
            self.transcriptions,
            self.search_entry.get(),
        )
        self._render_list(self.filtered_transcriptions)

    def _clear_list(self):
        for widget in self.transcription_list.winfo_children():
            widget.destroy()
        self.list_buttons.clear()

    def _show_empty_message(self, message: str):
        ctk.CTkLabel(
            self.transcription_list,
            text=message,
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            wraplength=250,
            justify="left",
        ).grid(
            row=0,
            column=0,
            padx=12,
            pady=20,
            sticky="w",
        )
        self.count_label.configure(text="0 archivos")

    @staticmethod
    def _format_list_name(file_name: str) -> str:
        return Path(str(file_name or "Transcripción")).stem

    # =========================================================
    # VISTA PREVIA
    # =========================================================

    def select_transcription(self, transcription: TranscriptionModel):
        self.selected_transcription = transcription

        for button in self.list_buttons.values():
            button.configure(fg_color="#FFFFFF")

        selected_button = self.list_buttons.get(id(transcription))
        if selected_button is not None:
            selected_button.configure(fg_color="#E8DDFB")

        self.file_name_label.configure(
            text=transcription.file_name or "Transcripción"
        )
        self.duration_value.configure(
            text=transcription.readable_duration or "--"
        )

        language = (
            transcription.detected_language
            or transcription.requested_language
            or "--"
        )
        self.language_value.configure(
            text=language.upper() if len(language) <= 5 else language
        )

        date_text = transcription.transcription_date or "--"
        if "T" in date_text:
            date_text = date_text.replace("T", " ")
        self.date_value.configure(text=date_text)

        self.model_value.configure(
            text=transcription.model_name or "--"
        )

        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", transcription.text or "")

        self.save_button.configure(state="normal")

        source = (
            transcription.json_path
            or transcription.txt_path
            or ""
        )
        self.footer_label.configure(
            text=f"Origen: {source}" if source else ""
        )

    def _clear_preview(self):
        self.selected_transcription = None
        self.file_name_label.configure(text="Seleccione una transcripción")
        self.duration_value.configure(text="--")
        self.language_value.configure(text="--")
        self.date_value.configure(text="--")
        self.model_value.configure(text="--")

        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert(
            "1.0",
            "Seleccione una transcripción de la lista para visualizarla.",
        )
        self.textbox.configure(state="disabled")

        self.save_button.configure(state="disabled")
        self.footer_label.configure(text="")

    # =========================================================
    # GUARDADO
    # =========================================================

    def save_current_transcription(self):
        if self.selected_transcription is None:
            return

        try:
            new_text = self.textbox.get("1.0", "end-1c")
            self.selected_transcription.update_text(new_text)
            TranscriptionService.save(self.selected_transcription)

            messagebox.showinfo(
                "Transcripción",
                "Los cambios se guardaron correctamente.",
            )

        except Exception as error:
            messagebox.showerror(
                "Error al guardar",
                "No fue posible guardar la transcripción.\n\n"
                f"Detalle: {error}",
            )
