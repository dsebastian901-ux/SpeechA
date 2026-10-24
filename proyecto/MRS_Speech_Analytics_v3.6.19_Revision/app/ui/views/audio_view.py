"""
============================================================
MRS Speech Analytics Professional
Vista: Gestión de audios
============================================================
"""

from __future__ import annotations

import logging
import queue
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinter import ttk

from app.core import project_manager
from app.services.audio_service import AudioService
from app.workers.transcription_worker import TranscriptionWorker
from app.ui.components.icon_factory import IconFactory
from app.ui.components.metric_card import MetricCard
from app.ui.themes import Theme

try:
    from app.services.whisper_service import WhisperServiceError, whisper_service
except Exception:
    WhisperServiceError = Exception
    whisper_service = None


LOGGER = logging.getLogger(__name__)
EVENT_POLL_MS = 100
DEFAULT_LANGUAGE = "es"
DEFAULT_OUTPUT_FOLDER_NAME = "transcripciones"


class AudioView(ctk.CTkFrame):
    """Pantalla para buscar, visualizar y transcribir archivos de audio."""

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        self.logger = LOGGER
        self.audio_records: List[Dict[str, Any]] = []
        self.audio_row_map: Dict[str, str] = {}
        self.selected_folder = ""
        self.current_output_directory = ""
        self._images: Dict[str, ctk.CTkImage] = {}

        self.worker = TranscriptionWorker(service=whisper_service)
        self.worker_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.worker_poll_job: Optional[str] = None

        self.language = DEFAULT_LANGUAGE
        self.vad_filter = True
        self.word_timestamps = False

        self.grid_columnconfigure(0, weight=1)

        # The table receives all remaining vertical space.
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1, minsize=280)
        self.grid_rowconfigure(4, weight=0)

        self.create_header()
        self.create_project_and_folder_panel()
        self.create_statistics()
        self.create_audio_table()
        self.create_processing_panel()

        self.load_project_information()
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _icon(self, name: str, size: int, color: str):
        key = f"{name}_{size}_{color}"
        image = IconFactory.create(name, size=size, color=color)
        self._images[key] = image
        return image

    def create_header(self):
        """Crea el encabezado moderno de Gestión de Audios."""

        header = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.SURFACE,
            border_color=Theme.colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        )
        header.grid(
            row=0,
            column=0,
            padx=Theme.spacing.PAGE_X,
            pady=(Theme.spacing.PAGE_Y, Theme.spacing.MD),
            sticky="ew",
        )
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="",
            image=self._icon("microphone", 28, Theme.colors.PRIMARY),
            width=58,
            height=58,
            fg_color=Theme.colors.PRIMARY_LIGHT,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        ).grid(
            row=0,
            column=0,
            rowspan=2,
            padx=Theme.spacing.LG,
            pady=Theme.spacing.LG,
        )

        ctk.CTkLabel(
            header,
            text="Gestión de Audios",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=25,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=0,
            column=1,
            pady=(Theme.spacing.LG, 0),
            sticky="sw",
        )

        ctk.CTkLabel(
            header,
            text="Seleccione, revise y transcriba los audios del proyecto.",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=13,
            ),
            anchor="w",
        ).grid(
            row=1,
            column=1,
            pady=(0, Theme.spacing.LG),
            sticky="nw",
        )

        self.header_status_label = ctk.CTkLabel(
            header,
            text="●  Listo",
            text_color=Theme.colors.SUCCESS,
            fg_color=Theme.colors.SUCCESS_LIGHT,
            corner_radius=999,
            padx=13,
            pady=5,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=12,
                weight="bold",
            ),
        )
        self.header_status_label.grid(
            row=0,
            column=2,
            rowspan=2,
            padx=Theme.spacing.LG,
        )

    def create_project_and_folder_panel(self):
        """Muestra el proyecto activo y la carpeta de audios."""

        panel = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.SURFACE,
            border_color=Theme.colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        )
        panel.grid(
            row=1,
            column=0,
            padx=Theme.spacing.PAGE_X,
            pady=(0, Theme.spacing.MD),
            sticky="ew",
        )
        panel.grid_columnconfigure(1, weight=1)

        project_box = ctk.CTkFrame(
            panel,
            fg_color=Theme.colors.TRANSPARENT,
        )
        project_box.grid(
            row=0,
            column=0,
            padx=Theme.spacing.LG,
            pady=Theme.spacing.LG,
            sticky="w",
        )

        ctk.CTkLabel(
            project_box,
            text="PROYECTO ACTIVO",
            text_color=Theme.colors.PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=11,
                weight="bold",
            ),
        ).pack(anchor="w")

        self.project_name_label = ctk.CTkLabel(
            project_box,
            text="Ningún proyecto abierto",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=17,
                weight="bold",
            ),
        )
        self.project_name_label.pack(anchor="w", pady=(3, 0))

        self.client_name_label = ctk.CTkLabel(
            project_box,
            text="Cliente: --",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=12,
            ),
        )
        self.client_name_label.pack(anchor="w", pady=(2, 0))

        folder_box = ctk.CTkFrame(
            panel,
            fg_color=Theme.colors.TRANSPARENT,
        )
        folder_box.grid(
            row=0,
            column=1,
            padx=Theme.spacing.LG,
            pady=Theme.spacing.LG,
            sticky="ew",
        )
        folder_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            folder_box,
            text="CARPETA DE AUDIOS",
            text_color=Theme.colors.PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=11,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            pady=(0, 5),
            sticky="w",
        )

        self.folder_entry = ctk.CTkEntry(
            folder_box,
            height=40,
            placeholder_text="Seleccione una carpeta con archivos de audio",
            fg_color=Theme.colors.SURFACE,
            text_color=Theme.colors.TEXT_PRIMARY,
            placeholder_text_color=Theme.colors.TEXT_MUTED,
            border_color=Theme.colors.BORDER,
            corner_radius=Theme.dimensions.RADIUS,
        )
        self.folder_entry.grid(
            row=1,
            column=0,
            padx=(0, Theme.spacing.MD),
            sticky="ew",
        )

        self.select_folder_button = ctk.CTkButton(
            folder_box,
            text="Seleccionar carpeta",
            image=self._icon("folder", 19, Theme.colors.TEXT_ON_PRIMARY),
            compound="left",
            width=180,
            height=40,
            fg_color=Theme.colors.PRIMARY,
            hover_color=Theme.colors.PRIMARY_HOVER,
            text_color=Theme.colors.TEXT_ON_PRIMARY,
            corner_radius=Theme.dimensions.RADIUS,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=13,
                weight="bold",
            ),
            command=self.select_folder,
        )
        self.select_folder_button.grid(row=1, column=1)

    def create_statistics(self):
        """Crea las tarjetas de estadísticas."""

        frame = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.TRANSPARENT,
        )
        frame.grid(
            row=2,
            column=0,
            padx=Theme.spacing.PAGE_X,
            pady=(0, Theme.spacing.MD),
            sticky="ew",
        )

        for column in range(4):
            frame.grid_columnconfigure(column, weight=1)

        self.total_card = MetricCard(
            frame,
            icon_name="microphone",
            value="0",
            title="Audios",
            subtitle="Archivos encontrados",
            bg=Theme.colors.CARD_PURPLE,
            icon_color=Theme.colors.CARD_PURPLE_ICON,
        )
        self.size_card = MetricCard(
            frame,
            icon_name="document",
            value="0 B",
            title="Tamaño total",
            subtitle="Carpeta seleccionada",
            bg=Theme.colors.CARD_BLUE,
            icon_color=Theme.colors.CARD_BLUE_ICON,
        )
        self.empty_card = MetricCard(
            frame,
            icon_name="check",
            value="0",
            title="Archivos vacíos",
            subtitle="Requieren revisión",
            bg=Theme.colors.CARD_GREEN,
            icon_color=Theme.colors.CARD_GREEN_ICON,
        )
        self.formats_card = MetricCard(
            frame,
            icon_name="wave",
            value="--",
            title="Formatos",
            subtitle="Tipos encontrados",
            bg=Theme.colors.CARD_CYAN,
            icon_color=Theme.colors.CARD_CYAN_ICON,
        )

        for column, card in enumerate(
            (
                self.total_card,
                self.size_card,
                self.empty_card,
                self.formats_card,
            )
        ):
            card.grid(
                row=0,
                column=column,
                padx=Theme.spacing.XS,
                sticky="nsew",
            )

    def create_audio_table(self):
        """Crea la tabla y mantiene visibles las acciones."""

        table_card = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.SURFACE,
            border_color=Theme.colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        )
        table_card.grid(
            row=3,
            column=0,
            padx=Theme.spacing.PAGE_X,
            pady=(0, Theme.spacing.MD),
            sticky="nsew",
        )
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(1, weight=1, minsize=190)

        toolbar = ctk.CTkFrame(
            table_card,
            height=52,
            fg_color=Theme.colors.TRANSPARENT,
        )
        toolbar.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=Theme.spacing.LG,
            pady=(Theme.spacing.MD, Theme.spacing.SM),
            sticky="ew",
        )
        toolbar.grid_columnconfigure(0, weight=1)

        self.table_title_label = ctk.CTkLabel(
            toolbar,
            text="Archivos encontrados",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=17,
                weight="bold",
            ),
        )
        self.table_title_label.grid(row=0, column=0, sticky="w")

        self.analyze_button = ctk.CTkButton(
            toolbar,
            text="Analizar audios",
            width=150,
            height=38,
            state="disabled",
            fg_color=Theme.colors.PRIMARY,
            hover_color=Theme.colors.PRIMARY_HOVER,
            text_color=Theme.colors.TEXT_ON_PRIMARY,
            corner_radius=Theme.dimensions.RADIUS,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=13,
                weight="bold",
            ),
            command=self.analyze_audios,
        )
        self.analyze_button.grid(row=0, column=1, padx=(8, 0))

        self.pause_button = ctk.CTkButton(
            toolbar,
            text="Pausar",
            width=100,
            height=38,
            state="disabled",
            fg_color=Theme.colors.BLUE,
            hover_color=Theme.colors.BLUE_HOVER,
            text_color=Theme.colors.TEXT_ON_PRIMARY,
            corner_radius=Theme.dimensions.RADIUS,
            command=self.toggle_pause_resume,
        )
        self.pause_button.grid(row=0, column=2, padx=(8, 0))

        self.cancel_button = ctk.CTkButton(
            toolbar,
            text="Cancelar",
            width=100,
            height=38,
            state="disabled",
            fg_color=Theme.colors.ERROR,
            hover_color=Theme.colors.ERROR_HOVER,
            text_color=Theme.colors.TEXT_ON_PRIMARY,
            corner_radius=Theme.dimensions.RADIUS,
            command=self.cancel_processing,
        )
        self.cancel_button.grid(row=0, column=3, padx=(8, 0))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "AudioV2.Treeview",
            background=Theme.colors.TABLE_ROW,
            fieldbackground=Theme.colors.TABLE_ROW,
            foreground=Theme.colors.TEXT_PRIMARY,
            rowheight=38,
            borderwidth=0,
            font=(Theme.fonts.FAMILY, 10),
        )
        style.configure(
            "AudioV2.Treeview.Heading",
            background=Theme.colors.TABLE_HEADER,
            foreground=Theme.colors.TEXT_PRIMARY,
            relief="flat",
            font=(Theme.fonts.FAMILY, 10, "bold"),
        )
        style.map(
            "AudioV2.Treeview",
            background=[("selected", Theme.colors.TABLE_SELECTED)],
            foreground=[("selected", Theme.colors.TEXT_PRIMARY)],
        )

        columns = ("nombre", "extension", "tamano", "estado")
        self.audio_table = ttk.Treeview(
            table_card,
            columns=columns,
            show="headings",
            selectmode="extended",
            style="AudioV2.Treeview",
            height=7,
        )

        self.audio_table.heading("nombre", text="Nombre del archivo")
        self.audio_table.heading("extension", text="Formato")
        self.audio_table.heading("tamano", text="Tamaño")
        self.audio_table.heading("estado", text="Estado")

        self.audio_table.column("nombre", width=560, minwidth=260, anchor="w")
        self.audio_table.column("extension", width=100, minwidth=75, anchor="center")
        self.audio_table.column("tamano", width=120, minwidth=90, anchor="center")
        self.audio_table.column("estado", width=145, minwidth=110, anchor="center")

        vertical_scrollbar = ttk.Scrollbar(
            table_card,
            orient="vertical",
            command=self.audio_table.yview,
        )
        horizontal_scrollbar = ttk.Scrollbar(
            table_card,
            orient="horizontal",
            command=self.audio_table.xview,
        )

        self.audio_table.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.audio_table.grid(
            row=1,
            column=0,
            padx=(Theme.spacing.LG, 0),
            sticky="nsew",
        )
        vertical_scrollbar.grid(
            row=1,
            column=1,
            padx=(0, Theme.spacing.LG),
            sticky="ns",
        )
        horizontal_scrollbar.grid(
            row=2,
            column=0,
            padx=(Theme.spacing.LG, 0),
            pady=(0, Theme.spacing.MD),
            sticky="ew",
        )

    def create_processing_panel(self):
        """Crea la barra inferior de progreso."""

        panel = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.SURFACE,
            border_color=Theme.colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        )
        panel.grid(
            row=4,
            column=0,
            padx=Theme.spacing.PAGE_X,
            pady=(0, Theme.spacing.PAGE_Y),
            sticky="ew",
        )
        panel.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            panel,
            text="Sin procesamiento en curso.",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=12,
                weight="bold",
            ),
            width=245,
            anchor="w",
        )
        self.status_label.grid(
            row=0,
            column=0,
            padx=(Theme.spacing.LG, Theme.spacing.MD),
            pady=Theme.spacing.MD,
            sticky="w",
        )

        self.progress_bar = ctk.CTkProgressBar(
            panel,
            fg_color=Theme.colors.PROGRESS_BACKGROUND,
            progress_color=Theme.colors.PROGRESS_FILL,
            height=11,
            corner_radius=999,
        )
        self.progress_bar.grid(
            row=0,
            column=1,
            padx=(0, Theme.spacing.MD),
            pady=Theme.spacing.MD,
            sticky="ew",
        )
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            panel,
            text="0 %",
            text_color=Theme.colors.TEXT_PRIMARY,
            width=55,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=12,
                weight="bold",
            ),
        )
        self.progress_label.grid(
            row=0,
            column=2,
            padx=(0, Theme.spacing.MD),
        )

        self.summary_label = ctk.CTkLabel(
            panel,
            text="0 procesados · 0 correctos · 0 errores",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=11,
            ),
        )
        self.summary_label.grid(
            row=0,
            column=3,
            padx=(0, Theme.spacing.LG),
            sticky="e",
        )

    def refresh_project_information(self):
        """Actualiza la información del proyecto activo."""
        self.load_project_information()

    def load_project_information(self):
        if not project_manager.has_open_project():
            self.project_name_label.configure(text="Ningún proyecto abierto")
            self.client_name_label.configure(text="Cliente: --")
            self.select_folder_button.configure(state="disabled")
            return

        self.project_name_label.configure(text=project_manager.get_project_name())
        self.client_name_label.configure(text=f"Cliente: {project_manager.get_project_client()}")
        self.select_folder_button.configure(state="normal")

    def select_folder(self):
        if not project_manager.has_open_project():
            messagebox.showwarning("Proyecto requerido", "Primero debe crear o abrir un proyecto.")
            return

        if self.worker.is_running:
            messagebox.showwarning(
                "Procesamiento en curso",
                "No puede cambiar de carpeta mientras se procesan audios.",
            )
            return

        folder_path = filedialog.askdirectory(title="Seleccione la carpeta de audios")
        if not folder_path:
            return

        self.selected_folder = folder_path
        self.folder_entry.delete(0, "end")
        self.folder_entry.insert(0, folder_path)
        self.scan_folder()

    def scan_folder(self):
        try:
            self.select_folder_button.configure(state="disabled", text="Buscando...")
            result = AudioService.scan_folder(self.selected_folder)
            self.audio_records = result.get("audios", [])

            self.update_statistics(result.get("estadisticas", {}))
            self.update_audio_table()
            self.reset_processing_panel()

            if self.audio_records:
                self.analyze_button.configure(state="normal")
            else:
                self.analyze_button.configure(state="disabled")
                messagebox.showinfo(
                    "Sin audios",
                    "No se encontraron archivos de audio compatibles en la carpeta seleccionada.",
                )
        except Exception as error:
            self.logger.exception("Error al buscar audios: %s", error)
            messagebox.showerror("Error al buscar audios", str(error))
        finally:
            self.select_folder_button.configure(state="normal", text="Seleccionar carpeta")

    def update_statistics(self, statistics):
        total_files = statistics.get("total_archivos", 0)
        total_size = statistics.get("tamano_total_legible", "0 B")
        empty_files = statistics.get("archivos_vacios", 0)
        extension_data = statistics.get("por_extension", {})

        formats = ", ".join(
            extension.replace(".", "").upper() for extension in extension_data.keys()
        )

        self.total_card.set_value(total_files)
        self.size_card.set_value(total_size)
        self.empty_card.set_value(empty_files)
        self.formats_card.set_value(formats if formats else "--")

    def update_audio_table(self):
        self.audio_row_map.clear()

        for item in self.audio_table.get_children():
            self.audio_table.delete(item)

        for index, audio in enumerate(self.audio_records):
            audio_path = self._extract_audio_path(audio)
            row_id = f"audio_{index}"
            self.audio_row_map[audio_path] = row_id

            self.audio_table.insert(
                "",
                "end",
                iid=row_id,
                values=(
                    audio.get("nombre", ""),
                    audio.get("extension", "").replace(".", "").upper(),
                    audio.get("tamano_legible", "0 B"),
                    audio.get("estado", "Pendiente"),
                ),
            )

    def analyze_audios(self):
        if self.worker.is_running:
            messagebox.showwarning("Procesamiento en curso", "Ya existe un procesamiento en ejecución.")
            return

        if not self.audio_records:
            messagebox.showwarning("Sin audios", "Primero seleccione una carpeta con audios válidos.")
            return

        selected_records = self.get_selected_audio_records() or list(self.audio_records)
        audio_paths = self._resolve_existing_audio_paths(selected_records)

        if not audio_paths:
            messagebox.showwarning("Sin archivos válidos", "No fue posible resolver rutas de audio válidas.")
            return

        self.current_output_directory = self.resolve_output_directory()

        for audio_path in audio_paths:
            self.set_audio_status(str(audio_path), "En cola")

        self.set_processing_controls(is_processing=True)
        self.reset_processing_panel()
        self.status_label.configure(text=f"Preparando {len(audio_paths)} audio(s)...")
        self.header_status_label.configure(text="● Procesando")

        try:
            self.worker.start(
                audio_paths=audio_paths,
                output_directory=self.current_output_directory or None,
                language=self.language,
                vad_filter=self.vad_filter,
                word_timestamps=self.word_timestamps,
                on_progress=self._enqueue_progress_event,
                on_finished=self._enqueue_finished_event,
                on_error=self._enqueue_error_event,
            )
            self.start_worker_polling()
        except (RuntimeError, ValueError, FileNotFoundError, WhisperServiceError) as error:
            self.set_processing_controls(is_processing=False)
            messagebox.showerror("Error al iniciar", str(error))
        except Exception as error:
            self.set_processing_controls(is_processing=False)
            messagebox.showerror("Error inesperado", f"No fue posible iniciar la transcripción: {error}")

    def toggle_pause_resume(self):
        if not self.worker.is_running:
            return

        if self.worker.is_paused:
            self.worker.resume()
            self.pause_button.configure(text="Pausar")
            self.status_label.configure(text="Procesamiento reanudado.")
        else:
            self.worker.pause()
            self.pause_button.configure(text="Reanudar")
            self.status_label.configure(text="Procesamiento en pausa.")

    def cancel_processing(self):
        if not self.worker.is_running:
            return

        if not messagebox.askyesno("Cancelar procesamiento", "¿Desea cancelar la transcripción en curso?"):
            return

        self.worker.cancel()
        self.pause_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.status_label.configure(text="Cancelando procesamiento...")

    def get_selected_audio_records(self) -> List[Dict[str, Any]]:
        selected_items = set(self.audio_table.selection())
        if not selected_items:
            return []

        records = []
        for audio in self.audio_records:
            audio_path = self._extract_audio_path(audio)
            if self.audio_row_map.get(audio_path) in selected_items:
                records.append(audio)
        return records

    def set_processing_controls(self, is_processing: bool):
        if is_processing:
            self.analyze_button.configure(state="disabled")
            self.select_folder_button.configure(state="disabled")
            self.pause_button.configure(state="normal", text="Pausar")
            self.cancel_button.configure(state="normal")
        else:
            self.analyze_button.configure(state="normal" if self.audio_records else "disabled")
            self.select_folder_button.configure(state="normal")
            self.pause_button.configure(state="disabled", text="Pausar")
            self.cancel_button.configure(state="disabled")

    def reset_processing_panel(self):
        self.progress_bar.set(0)
        self.progress_label.configure(text="0 %")
        self.summary_label.configure(text="0 procesados · 0 correctos · 0 errores")
        self.status_label.configure(text="Sin procesamiento en curso.")

    def start_worker_polling(self):
        if self.worker_poll_job is None:
            self.worker_poll_job = self.after(EVENT_POLL_MS, self.poll_worker_events)

    def poll_worker_events(self):
        self.worker_poll_job = None

        while True:
            try:
                event = self.worker_queue.get_nowait()
            except queue.Empty:
                break

            event_type = event.get("type")
            payload = event.get("payload", {})

            if event_type == "progress":
                self.process_worker_progress(payload)
            elif event_type == "error":
                self.process_worker_error(payload)
            elif event_type == "finished":
                self.process_worker_finished(payload)

        if self.worker.is_running or not self.worker_queue.empty():
            self.worker_poll_job = self.after(EVENT_POLL_MS, self.poll_worker_events)

    def process_worker_progress(self, payload: Dict[str, Any]):
        progress = float(payload.get("progress", 0.0) or 0.0)
        processed = int(payload.get("processed", 0) or 0)
        successful = int(payload.get("successful", 0) or 0)
        failed = int(payload.get("failed", 0) or 0)
        cancelled = int(payload.get("cancelled", 0) or 0)
        status = payload.get("status", "")
        message = payload.get("message", "")
        file_path = payload.get("file", "")

        self.progress_bar.set(max(0.0, min(progress, 1.0)))
        self.progress_label.configure(text=f"{round(progress * 100, 1)} %")
        self.summary_label.configure(
            text=(
                f"{processed} procesados · {successful} correctos · "
                f"{failed} errores · {cancelled} cancelados"
            )
        )

        if message:
            self.status_label.configure(text=message)

        if status == "processing" and file_path:
            self.set_audio_status(file_path, "Procesando")
        elif status == "completed" and file_path:
            self.set_audio_status(file_path, "Completado")
        elif status == "error" and file_path:
            self.set_audio_status(file_path, "Error")
        elif status == "model_loading":
            self.status_label.configure(text="Cargando el modelo Whisper...")

    def process_worker_error(self, payload: Dict[str, Any]):
        file_path = payload.get("file", "")
        message = payload.get("message") or payload.get("error") or "Error desconocido"

        if file_path:
            self.set_audio_status(file_path, "Error")

        self.status_label.configure(text=message)

    def process_worker_finished(self, payload: Dict[str, Any]):
        self.set_processing_controls(is_processing=False)
        self.header_status_label.configure(text="● Listo")

        status = payload.get("status", "finished")
        processed = int(payload.get("processed", 0) or 0)
        successful = int(payload.get("successful", 0) or 0)
        failed = int(payload.get("failed", 0) or 0)
        cancelled = int(payload.get("cancelled", 0) or 0)
        progress = float(payload.get("progress", 0.0) or 0.0)
        message = payload.get("message", "Procesamiento finalizado.")

        self.progress_bar.set(max(0.0, min(progress, 1.0)))
        self.progress_label.configure(text=f"{round(progress * 100, 1)} %")
        self.summary_label.configure(
            text=(
                f"{processed} procesados · {successful} correctos · "
                f"{failed} errores · {cancelled} cancelados"
            )
        )
        self.status_label.configure(text=message)

        if status == "fatal_error":
            messagebox.showerror("Error de procesamiento", message)
            return

        if failed:
            messagebox.showwarning(
                "Procesamiento completado con incidencias",
                (
                    f"Se procesaron {processed} audio(s).\n"
                    f"Correctos: {successful}.\n"
                    f"Errores: {failed}.\n"
                    f"Cancelados: {cancelled}."
                ),
            )
            return

        if cancelled:
            messagebox.showinfo(
                "Procesamiento cancelado",
                (
                    f"Se procesaron {processed} audio(s).\n"
                    f"Correctos: {successful}.\n"
                    f"Cancelados: {cancelled}."
                ),
            )
            return

        messagebox.showinfo(
            "Procesamiento completado",
            (
                f"Se procesaron correctamente {successful} audio(s).\n\n"
                f"Archivos de salida:\n{self.current_output_directory}"
            ),
        )

    def set_audio_status(self, audio_path: str, status: str):
        normalized_path = str(Path(audio_path)) if audio_path else ""
        row_id = self.audio_row_map.get(normalized_path)

        if row_id and self.audio_table.exists(row_id):
            current_values = list(self.audio_table.item(row_id, "values"))
            if len(current_values) >= 4:
                current_values[3] = status
                self.audio_table.item(row_id, values=current_values)

        for audio in self.audio_records:
            if self._extract_audio_path(audio) == normalized_path:
                audio["estado"] = status
                break

    def resolve_output_directory(self) -> str:
        if not self.selected_folder:
            return ""

        output_directory = Path(self.selected_folder) / DEFAULT_OUTPUT_FOLDER_NAME
        output_directory.mkdir(parents=True, exist_ok=True)
        return str(output_directory)

    def _resolve_existing_audio_paths(self, records: Iterable[Dict[str, Any]]) -> List[Path]:
        paths = []
        for audio in records:
            raw_path = self._extract_audio_path(audio)
            if not raw_path:
                continue

            file_path = Path(raw_path)
            if file_path.exists() and file_path.is_file():
                paths.append(file_path)
        return paths

    def _extract_audio_path(self, audio: Dict[str, Any]) -> str:
        for key in (
            "ruta",
            "path",
            "ruta_completa",
            "full_path",
            "archivo",
            "file_path",
            "source_path",
        ):
            value = audio.get(key)
            if value:
                return str(Path(value))

        name = audio.get("nombre", "")
        extension = audio.get("extension", "")
        if not name:
            return ""

        if extension and not str(name).lower().endswith(str(extension).lower()):
            filename = f"{name}{extension}"
        else:
            filename = str(name)

        if self.selected_folder:
            return str(Path(self.selected_folder) / filename)
        return filename

    def _enqueue_progress_event(self, payload: Dict[str, Any]):
        self.worker_queue.put({"type": "progress", "payload": dict(payload)})

    def _enqueue_error_event(self, payload: Dict[str, Any]):
        self.worker_queue.put({"type": "error", "payload": dict(payload)})

    def _enqueue_finished_event(self, payload: Dict[str, Any]):
        self.worker_queue.put({"type": "finished", "payload": dict(payload)})

    def _on_destroy(self, event):
        if event.widget is not self:
            return

        if self.worker_poll_job is not None:
            try:
                self.after_cancel(self.worker_poll_job)
            except Exception:
                pass
            finally:
                self.worker_poll_job = None

        if self.worker.is_running:
            try:
                self.worker.cancel()
            except Exception:
                pass
