"""
============================================================
MRS Speech Analytics Professional
Vista: Procesamiento por Lotes
============================================================
"""

from pathlib import Path
import os
from threading import Thread
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.core import project_manager
from app.services.batch_service import BatchService
from app.ui.themes import Theme


class BatchView(ctk.CTkFrame):
    """
    Vista para procesar múltiples audios de forma secuencial.

    Permite:
    - Seleccionar varios archivos
    - Ver la cola
    - Procesar uno por uno
    - Mostrar estado por archivo
    - Mostrar progreso general
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        self.batch_service = BatchService()
        self.is_processing = False
        self.relation_excel_path = None
        self.last_report_path = None
        self.batch_mode = "A"
        self._resume_checked_project = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_content()
        self.after(100, self._load_latest_existing_report)
        self.after(350, self._watch_project_checkpoint)

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
            text="PROCESAMIENTO POR LOTES",
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

        self.select_button = ctk.CTkButton(
            self.header,
            text="Agregar audios",
            width=130,
            height=36,
            fg_color=Theme.colors.PRIMARY,
            corner_radius=9,
            command=self.select_audio_files,
        )

        self.select_button.grid(
            row=0,
            column=1,
            rowspan=2,
            padx=(10, 8),
            pady=18,
        )

        self.start_button = ctk.CTkButton(
            self.header,
            text="Procesar lote",
            width=130,
            height=36,
            fg_color="#4F9D69",
            hover_color="#42875A",
            corner_radius=9,
            command=self.start_processing,
        )

        self.excel_button = ctk.CTkButton(
            self.header,
            text="Cargar Excel",
            width=120,
            height=36,
            fg_color="#7C6FD0",
            corner_radius=9,
            command=self.select_relation_excel,
        )
        self.excel_button.grid(
            row=0,
            column=2,
            rowspan=2,
            padx=(0, 8),
            pady=18,
        )

        self.start_button.grid(
            row=0,
            column=3,
            rowspan=2,
            padx=(0, 8),
            pady=18,
        )

        self.report_button = ctk.CTkButton(
            self.header,
            text="Abrir reporte Excel",
            width=145,
            height=36,
            fg_color="#6F5CC2",
            hover_color="#5E4DA8",
            corner_radius=9,
            command=self.open_last_report,
            state="disabled",
        )
        self.report_button.grid(
            row=0,
            column=4,
            rowspan=2,
            padx=(0, 8),
            pady=18,
        )

        self.partial_report_button = ctk.CTkButton(
            self.header,
            text="Reporte parcial",
            width=130,
            height=36,
            fg_color="#6F5CC2",
            hover_color="#5E4DA8",
            corner_radius=9,
            command=self.generate_partial_report_now,
        )
        self.partial_report_button.grid(
            row=0,
            column=5,
            rowspan=2,
            padx=(0, 24),
            pady=18,
        )

    # =========================================================
    # CONTENIDO
    # =========================================================

    def _build_content(self):
        self.content = ctk.CTkFrame(
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
        self.content.grid_rowconfigure(3, weight=1)

        self._build_mode_selector()
        self._build_summary()
        self._build_progress()
        self._build_queue()

        self._refresh_project_label()

    # =========================================================
    # MODO DE PROCESAMIENTO
    # =========================================================

    def _build_mode_selector(self):
        self.mode_frame = ctk.CTkFrame(
            self.content,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )
        self.mode_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.mode_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.mode_frame,
            text="Modo de procesamiento",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=18, pady=(14, 4), sticky="w")

        self.mode_segmented = ctk.CTkSegmentedButton(
            self.mode_frame,
            values=["Modo A · Audios + Excel", "Modo B · Solo audios"],
            command=self._on_mode_changed,
            selected_color=Theme.colors.PRIMARY,
            selected_hover_color=Theme.colors.PRIMARY,
        )
        self.mode_segmented.grid(row=1, column=0, padx=18, pady=(0, 6), sticky="w")
        self.mode_segmented.set("Modo A · Audios + Excel")

        self.mode_help_label = ctk.CTkLabel(
            self.mode_frame,
            text="Usa el Excel de relación, valida estatus autorizado y aplica nombre final.",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="w",
        )
        self.mode_help_label.grid(row=2, column=0, padx=18, pady=(0, 14), sticky="w")

    def _on_mode_changed(self, value):
        if self.is_processing:
            return

        if str(value).startswith("Modo B"):
            self.batch_mode = "B"
            self.batch_service.clear_relation_excel()
            self.relation_excel_path = None
            self.excel_button.configure(state="disabled")
            self.mode_help_label.configure(
                text="No usa Excel. Clasifica por score + reglas de Analytics y conserva el nombre original."
            )
            self.progress_label.configure(
                text=(
                    "Modo B · Solo audios · "
                    f"Umbral: {self.batch_service.get_relation_service().get_minimum_score()}%"
                )
            )
        else:
            self.batch_mode = "A"
            self.excel_button.configure(state="normal")
            self.mode_help_label.configure(
                text="Usa el Excel de relación, valida estatus autorizado y aplica nombre final."
            )
            if self.batch_service.has_relation_excel():
                self._show_relation_summary()
            else:
                self.progress_label.configure(
                    text="Modo A · Agregue audios y cargue el Excel de relación."
                )

        self._render_queue()

    # =========================================================
    # RESUMEN
    # =========================================================

    def _build_summary(self):
        self.summary_frame = ctk.CTkFrame(
            self.content,
            fg_color="transparent",
        )

        self.summary_frame.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        for column in range(4):
            self.summary_frame.grid_columnconfigure(
                column,
                weight=1,
                uniform="batch_kpi",
            )

        self.total_value = self._create_summary_card(
            0,
            "Total",
            "0",
            "#EEF5FF",
        )

        self.pending_value = self._create_summary_card(
            1,
            "Pendientes",
            "0",
            "#FFF5E9",
        )

        self.completed_value = self._create_summary_card(
            2,
            "Completados",
            "0",
            "#EEF9F2",
        )

        self.errors_value = self._create_summary_card(
            3,
            "Errores",
            "0",
            "#FCECEC",
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

        label = ctk.CTkLabel(
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

        label.pack(
            anchor="w",
            padx=18,
            pady=(0, 17),
        )

        return label

    # =========================================================
    # PROGRESO
    # =========================================================

    def _build_progress(self):
        self.progress_panel = ctk.CTkFrame(
            self.content,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        self.progress_panel.grid(
            row=2,
            column=0,
            pady=(12, 0),
            sticky="ew",
        )

        self.progress_panel.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(
            self.progress_panel,
            text="Esperando archivos...",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
            anchor="w",
        )

        self.progress_label.grid(
            row=0,
            column=0,
            padx=20,
            pady=(16, 8),
            sticky="ew",
        )

        self.metrics_label = ctk.CTkLabel(
            self.progress_panel,
            text="Tiempo: 00:00 · Promedio global: -- · Promedio reciente: -- · ETA reciente: --\nWhisper: -- · Analytics: -- · Copia: -- · Checkpoint: -- · Configuración: --",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="w",
        )
        self.metrics_label.grid(
            row=1, column=0, padx=20, pady=(0, 8), sticky="ew"
        )

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_panel,
            height=14,
        )

        self.progress_bar.grid(
            row=2,
            column=0,
            padx=20,
            pady=(0, 16),
            sticky="ew",
        )

        self.progress_bar.set(0)

    # =========================================================
    # COLA
    # =========================================================

    def _build_queue(self):
        self.queue_panel = ctk.CTkFrame(
            self.content,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        self.queue_panel.grid(
            row=3,
            column=0,
            pady=(12, 0),
            sticky="nsew",
        )

        self.queue_panel.grid_columnconfigure(0, weight=1)
        self.queue_panel.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self.queue_panel,
            text="Cola de procesamiento",
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

        self.queue_count_label = ctk.CTkLabel(
            self.queue_panel,
            text="0 archivos",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        )

        self.queue_count_label.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 10),
            sticky="ew",
        )

        self.queue_scroll = ctk.CTkScrollableFrame(
            self.queue_panel,
            fg_color="transparent",
        )

        self.queue_scroll.grid(
            row=2,
            column=0,
            padx=20,
            pady=(0, 20),
            sticky="nsew",
        )

        self.queue_scroll.grid_columnconfigure(0, weight=1)

        self._render_queue()

    # =========================================================
    # SELECCIONAR AUDIOS
    # =========================================================

    def select_audio_files(self):
        if self.is_processing:
            return

        files = filedialog.askopenfilenames(
            title="Seleccionar archivos de audio",
            filetypes=[
                (
                    "Archivos de audio",
                    "*.wav *.mp3 *.m4a *.ogg *.flac *.aac *.wma",
                ),
                (
                    "Todos los archivos",
                    "*.*",
                ),
            ],
        )

        if not files:
            return

        self.batch_service.set_files(
            files
        )

        self.progress_bar.set(0)
        self.metrics_label.configure(
            text="Tiempo: 00:00 · Promedio global: -- · Promedio reciente: -- · ETA reciente: --\nWhisper: -- · Analytics: -- · Copia: -- · Checkpoint: -- · Configuración: --"
        )

        if self.batch_service.has_relation_excel():
            self._show_relation_summary()
        else:
            self.progress_label.configure(
                text="Archivos cargados. Listos para procesar."
            )

        self._render_queue()
        self._update_summary()


    # =========================================================
    # SELECCIONAR EXCEL DE RELACIÓN
    # =========================================================

    def select_relation_excel(self):
        if self.is_processing:
            return

        if self.batch_mode != "A":
            return

        excel_path = filedialog.askopenfilename(
            title="Seleccionar Excel de relación",
            filetypes=[
                ("Archivos de Excel", "*.xlsx *.xlsm"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if not excel_path:
            return

        try:
            self.batch_service.set_relation_excel(excel_path)
            self.relation_excel_path = excel_path
            self._show_relation_summary()
            self._render_queue()
        except Exception as error:
            messagebox.showerror(
                "Relación de audios",
                f"No fue posible cargar el Excel.\n\nDetalle: {error}",
            )


    # =========================================================
    # RESUMEN DE RELACION EXCEL
    # =========================================================

    def _show_relation_summary(self):
        try:
            summary = self.batch_service.get_relation_summary()

            if not summary.get("modo_excel"):
                return

            excel_name = Path(
                summary.get("archivo_excel") or ""
            ).name

            minimum_score = summary.get(
                "puntaje_minimo",
                80,
            )

            matches = summary.get(
                "total_coincidencias",
                0,
            )

            missing = summary.get(
                "audios_sin_relacion",
                0,
            )

            self.progress_label.configure(
                text=(
                    f"Modo Audios + Excel · {excel_name} · "
                    f"Umbral: {minimum_score}% · "
                    f"Relacionados: {matches} · "
                    f"Sin relacion: {missing}"
                )
            )

        except Exception as error:
            self.progress_label.configure(
                text=f"No fue posible mostrar la validacion Excel: {error}"
            )

    # =========================================================
    # REANUDAR LOTE INTERRUMPIDO
    # =========================================================

    def _get_batch_output_directory(self):
        project_path = self._get_active_project_path()
        if project_path is None:
            return None
        path = project_path / "01_Audios" / "transcripciones"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _watch_project_checkpoint(self):
        """
        Vigila el proyecto activo.

        La versión anterior revisaba el checkpoint una sola vez al abrir
        BatchView. Si el proyecto todavía no estaba activo en ese instante,
        nunca volvía a preguntar. Esta vigilancia detecta también cambios
        posteriores de proyecto.
        """
        if not self.is_processing:
            project_path = self._get_active_project_path()
            project_key = str(project_path).lower() if project_path else None

            if project_key and project_key != self._resume_checked_project:
                self._resume_checked_project = project_key
                self._offer_resume_checkpoint()

        # Mantener la vigilancia viva mientras exista la vista.
        try:
            self.after(1000, self._watch_project_checkpoint)
        except Exception:
            pass

    def _offer_resume_checkpoint(self):
        if self.is_processing:
            return
        output_directory = self._get_batch_output_directory()
        if output_directory is None:
            return
        checkpoint = self.batch_service.find_checkpoint(output_directory)
        if not checkpoint:
            return

        partial_report_path = None
        if int(checkpoint.get("completed", 0) or 0) + int(checkpoint.get("errors", 0) or 0) > 0:
            try:
                partial_report_path = self.batch_service.generate_partial_report_from_checkpoint(
                    output_directory
                )
                self.last_report_path = partial_report_path
                self.report_button.configure(state="normal")
            except Exception:
                partial_report_path = None

        answer = messagebox.askyesnocancel(
            "Lote interrumpido detectado",
            "Se encontró un lote sin terminar.\n\n"
            f"Modo: {checkpoint.get('mode')}\n"
            f"Total: {checkpoint.get('total')}\n"
            f"Completados: {checkpoint.get('completed')}\n"
            f"Errores: {checkpoint.get('errors')}\n"
            f"Pendientes: {checkpoint.get('pending')}\n"
            f"Último guardado: {checkpoint.get('updated_at') or ''}\n\n"
            + (
                "Reporte parcial actualizado: Reporte_Parcial_Lote.xlsx\n\n"
                if partial_report_path else
                "No fue posible actualizar el reporte parcial automáticamente.\n\n"
            )
            + "Sí = Reanudar\nNo = Descartar checkpoint\nCancelar = Conservarlo",
        )
        if answer is None:
            return
        if answer is False:
            if messagebox.askyesno("Descartar lote","¿Seguro? Los audios originales no se eliminarán."):
                self.batch_service.discard_checkpoint(output_directory)
            return

        try:
            self.batch_service.resume_from_checkpoint(output_directory)
        except Exception as error:
            messagebox.showerror("Reanudar lote",f"No fue posible recuperar el lote.\n\n{error}")
            return

        self.batch_mode = checkpoint.get("mode","B")
        if self.batch_mode == "B":
            self.mode_segmented.set("Modo B · Solo audios")
            self.excel_button.configure(state="disabled")
            self.relation_excel_path = None
        else:
            self.mode_segmented.set("Modo A · Audios + Excel")
            self.excel_button.configure(state="normal")
            self.relation_excel_path = checkpoint.get("relation_excel")

        self._render_queue()
        self._update_summary()
        self._update_metrics()
        self.progress_label.configure(
            text=f"Lote recuperado · {checkpoint.get('completed')} de {checkpoint.get('total')} terminados · {checkpoint.get('pending')} pendientes"
        )
        self.is_processing = True
        if partial_report_path:
            self.last_report_path = partial_report_path
            self.report_button.configure(state="normal")
        self._set_controls_enabled(False)
        Thread(target=self._process_worker,args=(output_directory,),daemon=True).start()

    # =========================================================
    # INICIAR
    # =========================================================

    def start_processing(self):
        if self.is_processing:
            return

        items = self.batch_service.get_items()

        if not items:
            messagebox.showwarning(
                "Procesamiento por lotes",
                "Primero agregue archivos de audio.",
            )
            return

        project_path = self._get_active_project_path()

        if project_path is None:
            messagebox.showwarning(
                "Procesamiento por lotes",
                "Abra un proyecto antes de procesar audios.",
            )
            return

        if self.batch_mode == "A" and not self.batch_service.has_relation_excel():
            messagebox.showwarning(
                "Modo A · Audios + Excel",
                "Cargue el Excel de relación antes de procesar el lote.",
            )
            return

        if self.batch_mode == "B" and self.batch_service.has_relation_excel():
            self.batch_service.clear_relation_excel()
            self.relation_excel_path = None

        output_directory = (
            project_path
            / "01_Audios"
            / "transcripciones"
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.is_processing = True
        self.last_report_path = None
        self.report_button.configure(state="disabled")
        self._set_controls_enabled(False)

        self.progress_label.configure(
            text="Iniciando procesamiento..."
        )

        worker = Thread(
            target=self._process_worker,
            args=(output_directory,),
            daemon=True,
        )

        worker.start()

    # =========================================================
    # WORKER
    # =========================================================

    def _process_worker(
        self,
        output_directory,
    ):
        try:
            self.batch_service.process_all(
                output_directory=output_directory,
                progress_callback=self._progress_callback,
            )

            self.after(
                0,
                self._processing_finished,
            )

        except Exception as error:
            self.after(
                0,
                lambda: self._processing_failed(
                    error
                ),
            )

    # =========================================================
    # CALLBACK DE PROGRESO
    # =========================================================

    def _progress_callback(
        self,
        index,
        total,
        item,
    ):
        self.after(
            0,
            lambda: self._update_progress_ui(
                index,
                total,
                item,
            ),
        )

    # =========================================================
    # ACTUALIZAR PROGRESO
    # =========================================================

    def _update_progress_ui(
        self,
        index,
        total,
        item,
    ):
        status = item.get(
            "status",
            "",
        )

        file_name = item.get(
            "file_name",
            "",
        )

        if status == "procesando":
            completed_before = max(
                index - 1,
                0,
            )

            progress = (
                completed_before / total
                if total > 0
                else 0
            )

            self.progress_label.configure(
                text=(
                    f"Procesando {index} de {total}: "
                    f"{file_name}"
                )
            )

        else:
            progress = (
                index / total
                if total > 0
                else 0
            )

            self.progress_label.configure(
                text=(
                    f"{index} de {total} finalizado: "
                    f"{file_name}"
                )
            )

        self.progress_bar.set(
            progress
        )

        self._render_queue()
        self._update_summary()
        self._update_metrics()

    # =========================================================
    # FINALIZADO
    # =========================================================

    def _processing_finished(self):
        self.is_processing = False

        self._set_controls_enabled(True)

        self.progress_bar.set(1)

        summary = self.batch_service.get_summary()

        completed = summary.get(
            "completed",
            0,
        )

        errors = summary.get(
            "errors",
            0,
        )

        self.progress_label.configure(
            text=(
                f"Proceso terminado · "
                f"{completed} completados · "
                f"{errors} errores"
            )
        )

        self._render_queue()
        self._update_summary()
        self._update_metrics()

        classification_summary = (
            self.batch_service.get_classification_summary()
            if hasattr(
                self.batch_service,
                "get_classification_summary",
            )
            else {}
        )

        approved = classification_summary.get(
            "aprobados",
            0,
        )
        review = classification_summary.get(
            "revisar",
            0,
        )
        minimum_score = classification_summary.get(
            "puntaje_minimo",
            80,
        )

        report_path = None
        if hasattr(self.batch_service, "get_last_report_path"):
            report_path = self.batch_service.get_last_report_path()

        if report_path and Path(report_path).exists():
            self.last_report_path = str(report_path)
            self.report_button.configure(state="normal")
            report_message = (
                "\n\nReporte Excel generado correctamente."
                "\nUse el botón 'Abrir reporte Excel' para consultarlo."
            )
        else:
            self.last_report_path = None
            self.report_button.configure(state="disabled")
            report_message = (
                "\n\nNo se encontró un reporte Excel generado para este lote."
            )

        messagebox.showinfo(
            "Procesamiento por lotes",
            (
                "Procesamiento terminado.\n\n"
                f"Completados: {completed}\n"
                f"Errores: {errors}\n"
                f"Aprobados: {approved}\n"
                f"Revisar: {review}\n"
                f"Umbral: {minimum_score}%"
                f"{report_message}"
            ),
        )

    # =========================================================
    # DETECTAR ÚLTIMO REPORTE EXISTENTE
    # =========================================================

    def _load_latest_existing_report(self):
        """Busca el reporte Excel más reciente del proyecto activo."""
        if self.is_processing:
            return

        project_path = self._get_active_project_path()
        if project_path is None:
            self.last_report_path = None
            self.report_button.configure(state="disabled")
            return

        reports_dir = project_path / "04_Reportes"
        if not reports_dir.exists():
            self.last_report_path = None
            self.report_button.configure(state="disabled")
            return

        candidates = [
            path
            for path in reports_dir.glob("*.xlsx")
            if path.is_file()
            and (
                path.name.startswith("Reporte_Analisis_Audios_")
                or path.name == "Reporte_Parcial_Lote.xlsx"
            )
        ]

        if not candidates:
            self.last_report_path = None
            self.report_button.configure(state="disabled")
            return

        latest = max(candidates, key=lambda path: path.stat().st_mtime)
        self.last_report_path = str(latest.resolve())
        self.report_button.configure(state="normal")

    # =========================================================
    # REPORTE PARCIAL DE SEGURIDAD
    # =========================================================

    def generate_partial_report_now(self):
        output_directory = self._get_batch_output_directory()
        if output_directory is None:
            messagebox.showwarning(
                "Reporte parcial",
                "Abra un proyecto antes de generar el reporte parcial.",
            )
            return

        try:
            # Si el lote está cargado en memoria, usa el estado actual.
            processed = [
                item for item in self.batch_service.get_items()
                if item.get("status") in ("completado", "error")
            ]
            if processed:
                report_path = self.batch_service.generate_partial_report(output_directory)
            else:
                # Si la app acaba de abrir tras una interrupción, usa el checkpoint.
                report_path = self.batch_service.generate_partial_report_from_checkpoint(
                    output_directory
                )

            self.last_report_path = report_path
            self.report_button.configure(state="normal")
            messagebox.showinfo(
                "Reporte parcial",
                "Reporte parcial actualizado correctamente.\n\n"
                f"{report_path}",
            )
        except Exception as error:
            messagebox.showerror(
                "Reporte parcial",
                "No fue posible generar el reporte parcial.\n\n"
                f"Detalle: {error}",
            )

    # =========================================================
    # ABRIR ÚLTIMO REPORTE EXCEL
    # =========================================================

    def open_last_report(self):
        report_path = (
            self.last_report_path
            or (
                self.batch_service.get_last_report_path()
                if hasattr(self.batch_service, "get_last_report_path")
                else None
            )
        )

        if not report_path:
            messagebox.showwarning(
                "Reporte Excel",
                "Todavía no hay un reporte generado en esta sesión.",
            )
            return

        path = Path(report_path).expanduser().resolve()

        if not path.exists():
            self.report_button.configure(state="disabled")
            messagebox.showerror(
                "Reporte Excel",
                f"No se encontró el archivo:\n\n{path}",
            )
            return

        try:
            os.startfile(str(path))
        except Exception as error:
            messagebox.showerror(
                "Reporte Excel",
                "No fue posible abrir el reporte.\n\n"
                f"Detalle: {error}",
            )

    # =========================================================
    # ERROR GENERAL
    # =========================================================

    def _processing_failed(
        self,
        error,
    ):
        self.is_processing = False

        self._set_controls_enabled(True)

        self.progress_label.configure(
            text="El procesamiento fue interrumpido."
        )

        messagebox.showerror(
            "Procesamiento por lotes",
            "Ocurrió un error durante el lote.\n\n"
            f"Detalle: {error}",
        )

    # =========================================================
    # RENDER COLA
    # =========================================================

    def _render_queue(self):
        for widget in self.queue_scroll.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        items = self.batch_service.get_items()

        total = len(items)

        self.queue_count_label.configure(
            text=(
                f"{total} archivo"
                f"{'' if total == 1 else 's'}"
            )
        )

        if not items:
            ctk.CTkLabel(
                self.queue_scroll,
                text="No hay archivos en la cola.",
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

        for row, item in enumerate(
            items
        ):
            self._create_queue_row(
                row,
                item,
            )

    # =========================================================
    # FILA
    # =========================================================

    def _create_queue_row(
        self,
        row,
        item,
    ):
        frame = ctk.CTkFrame(
            self.queue_scroll,
            fg_color="#FAFAFD",
            corner_radius=8,
            border_width=1,
            border_color="#EEEEF4",
        )

        frame.grid(
            row=row,
            column=0,
            pady=3,
            sticky="ew",
        )

        frame.grid_columnconfigure(0, weight=1)

        status = item.get(
            "status",
            "pendiente",
        )

        file_name = item.get(
            "file_name",
            "",
        )

        status_text = {
            "pendiente": "Pendiente",
            "procesando": "Procesando",
            "completado": "Completado",
            "error": "Error",
        }.get(
            status,
            status,
        )

        relation_status = item.get(
            "relation_status",
            "sin_validar",
        )

        if self.batch_service.has_relation_excel():
            if relation_status == "relacionado":
                status_text = f"{status_text} · Relacionado"
            elif relation_status == "sin_relacion":
                status_text = f"{status_text} · SIN RELACION"
            else:
                status_text = f"{status_text} · Sin validar"

        status_color = {
            "pendiente": "#6B7280",
            "procesando": "#4F7DD9",
            "completado": "#388E5A",
            "error": "#C64B4B",
        }.get(
            status,
            Theme.colors.TEXT_SECONDARY,
        )

        relation = item.get("relation") or {}
        gestor = str(relation.get("gestor") or "").strip()
        estatus_grabacion = str(
            relation.get("estatus_grabacion") or ""
        ).strip()

        compliance_score = item.get("compliance_score")
        classification = item.get("classification") or {}

        result_text = str(
            classification.get("clasificacion") or ""
        ).strip()

        reason_text = str(
            classification.get("motivo") or ""
        ).strip()

        ctk.CTkLabel(
            frame,
            text=file_name,
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            padx=12,
            pady=(10, 3),
            sticky="ew",
        )

        detail_parts = []

        if gestor:
            detail_parts.append(
                f"Gestor: {gestor}"
            )

        if estatus_grabacion:
            detail_parts.append(
                f"Estatus: {estatus_grabacion}"
            )

        if compliance_score is not None:
            try:
                detail_parts.append(
                    f"Score: {float(compliance_score):.1f}%"
                )
            except (TypeError, ValueError):
                detail_parts.append(
                    f"Score: {compliance_score}"
                )

        if result_text:
            detail_parts.append(
                f"Resultado: {result_text}"
            )

        if detail_parts:
            ctk.CTkLabel(
                frame,
                text=" · ".join(detail_parts),
                text_color=Theme.colors.TEXT_SECONDARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                ),
                anchor="w",
            ).grid(
                row=1,
                column=0,
                columnspan=2,
                padx=12,
                pady=(0, 3),
                sticky="ew",
            )

        if reason_text and result_text.upper() == "REVISAR":
            ctk.CTkLabel(
                frame,
                text=f"Motivo: {reason_text}",
                text_color="#C64B4B",
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                    weight="bold",
                ),
                anchor="w",
            ).grid(
                row=2,
                column=0,
                columnspan=2,
                padx=12,
                pady=(0, 4),
                sticky="ew",
            )

        elapsed_seconds = float(
            item.get("elapsed_seconds", 0.0)
            or 0.0
        )

        if status in ("completado", "error") and elapsed_seconds > 0:
            status_text = (
                f"{status_text} · "
                f"{self._format_seconds(elapsed_seconds)}"
            )

        status_row = 3 if reason_text and result_text.upper() == "REVISAR" else (
            2 if detail_parts else 1
        )

        ctk.CTkLabel(
            frame,
            text=status_text,
            text_color=status_color,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold",
            ),
            anchor="e",
        ).grid(
            row=status_row,
            column=1,
            padx=12,
            pady=(0, 10),
            sticky="e",
        )

    # =========================================================
    # MÉTRICAS
    # =========================================================

    @staticmethod
    def _format_seconds(seconds):
        seconds = max(0, int(round(float(seconds or 0))))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return (
            f"{hours:02d}:{minutes:02d}:{secs:02d}"
            if hours
            else f"{minutes:02d}:{secs:02d}"
        )

    def _update_metrics(self):
        metrics = self.batch_service.get_metrics()
        elapsed = self._format_seconds(metrics.get("elapsed_seconds", 0.0))

        avg_s = float(metrics.get("average_seconds", 0.0) or 0.0)
        recent_s = float(metrics.get("recent_average_seconds", 0.0) or 0.0)
        recent_eta_s = float(metrics.get("recent_estimated_remaining_seconds", 0.0) or 0.0)
        sample = int(metrics.get("recent_sample_size", 0) or 0)

        average = self._format_seconds(avg_s) if avg_s > 0 else "--"
        recent = self._format_seconds(recent_s) if recent_s > 0 else "--"
        recent_eta = self._format_seconds(recent_eta_s) if recent_eta_s > 0 else "--"

        whisper_t = self._format_seconds(metrics.get("whisper_average_seconds", 0.0))
        analytics_t = self._format_seconds(metrics.get("analytics_average_seconds", 0.0))
        copy_t = self._format_seconds(metrics.get("copy_average_seconds", 0.0))
        checkpoint_t = self._format_seconds(metrics.get("checkpoint_average_seconds", 0.0))

        runtime = metrics.get("runtime_configuration") or {}
        model_name = runtime.get("model") or runtime.get("whisper_model") or "--"
        device = str(runtime.get("device") or runtime.get("whisper_device") or "--").upper()
        compute = str(runtime.get("compute_type") or runtime.get("whisper_compute_type") or "--").upper()
        beam = runtime.get("beam_size")
        if beam is None:
            beam = runtime.get("whisper_beam_size", "--")
        vad = runtime.get("vad_filter")
        if vad is None:
            vad = runtime.get("whisper_vad_filter")
        vad_text = "ON" if vad is True else "OFF" if vad is False else "--"

        self.metrics_label.configure(
            text=(
                f"Tiempo: {elapsed} · Promedio global: {average} · "
                f"Promedio reciente ({sample}): {recent} · ETA reciente: {recent_eta}\n"
                f"Whisper: {whisper_t} · Analytics: {analytics_t} · Copia: {copy_t} · "
                f"Checkpoint: {checkpoint_t} · "
                f"Configuración: {model_name} · {device} · {compute} · Beam {beam} · VAD {vad_text}"
            )
        )

    # =========================================================
    # RESUMEN
    # =========================================================

    def _update_summary(self):
        summary = self.batch_service.get_summary()

        self.total_value.configure(
            text=str(
                summary.get(
                    "total",
                    0,
                )
            )
        )

        self.pending_value.configure(
            text=str(
                summary.get(
                    "pending",
                    0,
                )
            )
        )

        self.completed_value.configure(
            text=str(
                summary.get(
                    "completed",
                    0,
                )
            )
        )

        self.errors_value.configure(
            text=str(
                summary.get(
                    "errors",
                    0,
                )
            )
        )

    # =========================================================
    # CONTROLES
    # =========================================================

    def _set_controls_enabled(
        self,
        enabled,
    ):
        state = (
            "normal"
            if enabled
            else "disabled"
        )

        self.select_button.configure(
            state=state
        )

        self.start_button.configure(
            state=state
        )

        self.mode_segmented.configure(
            state=state
        )

        self.excel_button.configure(
            state=("normal" if enabled and self.batch_mode == "A" else "disabled")
        )

        if not enabled:
            self.report_button.configure(state="disabled")
        elif self.last_report_path and Path(self.last_report_path).exists():
            self.report_button.configure(state="normal")
        else:
            self.report_button.configure(state="disabled")

    # =========================================================
    # PROYECTO
    # =========================================================

    def _refresh_project_label(self):
        self.project_label.configure(
            text=(
                f"Proyecto: "
                f"{self._get_active_project_name()}"
            )
        )

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
                    return str(
                        name
                    )

        except Exception:
            pass

        return "Sin proyecto abierto"