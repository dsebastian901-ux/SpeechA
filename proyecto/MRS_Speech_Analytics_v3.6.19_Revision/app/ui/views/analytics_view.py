"""
============================================================
MRS Speech Analytics Professional
Vista: Analytics de Llamadas
============================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import customtkinter as ctk
from tkinter import messagebox

from app.core import project_manager
from app.models.analytics_model import AnalyticsModel
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService
from app.services.transcription_services import TranscriptionService
from app.services.review_service import ReviewService
from app.services.amount_review_service import AmountReviewService
from app.services.asr_amount_recovery import validated_entries
from app.services.relation_service import RelationService
from app.ui.themes import Theme


class AnalyticsView(ctk.CTkFrame):
    """
    Vista para analizar las transcripciones del proyecto activo.

    Funciones:
    - Localizar transcripciones.
    - Seleccionar una llamada.
    - Analizar llamada.
    - Guardar automáticamente el análisis.
    - Recuperar análisis previamente guardados.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        self.transcriptions: List[TranscriptionModel] = []
        self.selected_transcription: Optional[TranscriptionModel] = None
        self.current_analysis: Optional[AnalyticsModel] = None

        self.list_buttons = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

        self.load_transcriptions()

    # =========================================================
    # HEADER
    # =========================================================

    def _build_header(self):
        self.header = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
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
            text="ANALYTICS DE LLAMADAS",
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

        self.reload_button = ctk.CTkButton(
            self.header,
            text="Recargar",
            width=110,
            height=36,
            fg_color=Theme.colors.PRIMARY,
            corner_radius=9,
            command=self.load_transcriptions,
        )

        self.reload_button.grid(
            row=0,
            column=1,
            rowspan=2,
            padx=24,
            pady=18,
            sticky="e",
        )

    # =========================================================
    # BODY
    # =========================================================

    def _build_body(self):
        self.body = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        self.body.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 20),
            sticky="nsew",
        )

        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_columnconfigure(1, weight=3)
        self.body.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()

    # =========================================================
    # PANEL IZQUIERDO
    # =========================================================

    def _build_left_panel(self):
        self.left_panel = ctk.CTkFrame(
            self.body,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
        )

        self.left_panel.grid(
            row=0,
            column=0,
            padx=(0, 10),
            sticky="nsew",
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
            anchor="w",
        ).grid(
            row=0,
            column=0,
            padx=18,
            pady=(18, 2),
            sticky="ew",
        )

        self.count_label = ctk.CTkLabel(
            self.left_panel,
            text="0 archivos",
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
            padx=18,
            pady=(0, 8),
            sticky="ew",
        )

        self.transcription_list = ctk.CTkScrollableFrame(
            self.left_panel,
            fg_color="transparent",
        )

        self.transcription_list.grid(
            row=2,
            column=0,
            padx=12,
            pady=(0, 12),
            sticky="nsew",
        )

        self.transcription_list.grid_columnconfigure(0, weight=1)

    # =========================================================
    # PANEL DERECHO
    # =========================================================

    def _build_right_panel(self):
        self.right_panel = ctk.CTkFrame(
            self.body,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
        )

        self.right_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(6, weight=1)

        # -----------------------------------------------------
        # CABECERA
        # -----------------------------------------------------

        header = ctk.CTkFrame(
            self.right_panel,
            fg_color="transparent",
        )

        header.grid(
            row=0,
            column=0,
            padx=22,
            pady=(18, 8),
            sticky="ew",
        )

        header.grid_columnconfigure(0, weight=1)

        self.selected_file_label = ctk.CTkLabel(
            header,
            text="Seleccione una transcripción",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=18,
                weight="bold",
            ),
            anchor="w",
        )

        self.selected_file_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.analyze_button = ctk.CTkButton(
            header,
            text="Analizar llamada",
            width=150,
            height=38,
            fg_color=Theme.colors.PRIMARY,
            corner_radius=9,
            state="disabled",
            command=self.analyze_selected,
        )

        self.analyze_button.grid(
            row=0,
            column=1,
            sticky="e",
        )
        ctk.CTkButton(header, text="Validar trato", width=150,
                      command=self.validate_treatment).grid(row=1, column=1, pady=(8, 0), sticky="e")
        ctk.CTkButton(header, text="Validar importe", width=150,
                      command=self.validate_amount).grid(row=2, column=1, pady=(8, 0), sticky="e")

        # -----------------------------------------------------
        # ESTADO
        # -----------------------------------------------------

        self.status_label = ctk.CTkLabel(
            self.right_panel,
            text="Seleccione una llamada para comenzar.",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        )

        self.status_label.grid(
            row=1,
            column=0,
            padx=22,
            pady=(0, 10),
            sticky="ew",
        )

        # -----------------------------------------------------
        # MÉTRICAS
        # -----------------------------------------------------

        self.metrics_frame = ctk.CTkFrame(
            self.right_panel,
            fg_color="transparent",
        )

        self.metrics_frame.grid(
            row=2,
            column=0,
            padx=17,
            pady=(0, 12),
            sticky="ew",
        )

        for column in range(4):
            self.metrics_frame.grid_columnconfigure(
                column,
                weight=1,
            )

        self.reason_value = self._create_metric(
            column=0,
            title="Motivo",
            background="#EEF5FF",
        )

        self.sentiment_value = self._create_metric(
            column=1,
            title="Sentimiento",
            background="#F2EEFF",
        )

        self.compliance_value = self._create_metric(
            column=2,
            title="Cumplimiento",
            background="#EEF9F2",
        )

        self.words_value = self._create_metric(
            column=3,
            title="Palabras",
            background="#FFF5E9",
        )

        # -----------------------------------------------------
        # RESUMEN
        # -----------------------------------------------------

        ctk.CTkLabel(
            self.right_panel,
            text="Resumen",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=3,
            column=0,
            padx=22,
            pady=(2, 5),
            sticky="ew",
        )

        self.summary_box = ctk.CTkTextbox(
            self.right_panel,
            height=120,
            wrap="word",
            fg_color="#FFFFFF",
            text_color=Theme.colors.TEXT_PRIMARY,
            border_width=1,
            border_color="#E5E5EF",
            corner_radius=10,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
        )

        self.summary_box.grid(
            row=4,
            column=0,
            padx=22,
            pady=(0, 12),
            sticky="ew",
        )

        self.summary_box.configure(state="disabled")

        # -----------------------------------------------------
        # PALABRAS CLAVE
        # -----------------------------------------------------

        ctk.CTkLabel(
            self.right_panel,
            text="Palabras clave",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=5,
            column=0,
            padx=22,
            pady=(2, 5),
            sticky="ew",
        )

        self.keywords_box = ctk.CTkTextbox(
            self.right_panel,
            wrap="word",
            fg_color="#FFFFFF",
            text_color=Theme.colors.TEXT_PRIMARY,
            border_width=1,
            border_color="#E5E5EF",
            corner_radius=10,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
        )

        self.keywords_box.grid(
            row=6,
            column=0,
            padx=22,
            pady=(0, 20),
            sticky="nsew",
        )

        self.keywords_box.configure(state="disabled")

    # =========================================================
    # MÉTRICA
    # =========================================================

    def _create_metric(
        self,
        column: int,
        title: str,
        background: str,
    ):
        frame = ctk.CTkFrame(
            self.metrics_frame,
            fg_color=background,
            corner_radius=12,
        )

        frame.grid(
            row=0,
            column=column,
            padx=5,
            sticky="ew",
        )

        ctk.CTkLabel(
            frame,
            text=title,
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold",
            ),
        ).pack(
            anchor="w",
            padx=14,
            pady=(10, 2),
        )

        value_label = ctk.CTkLabel(
            frame,
            text="--",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14,
                weight="bold",
            ),
        )

        value_label.pack(
            anchor="w",
            padx=14,
            pady=(0, 10),
        )

        return value_label

    # =========================================================
    # CARGAR TRANSCRIPCIONES
    # =========================================================

    def load_transcriptions(self):
        self._clear_transcription_list()
        self._clear_analysis()

        project_path = self._get_active_project_path()

        if project_path is None:
            self.project_label.configure(
                text="Proyecto: Sin proyecto abierto"
            )

            self._show_empty_message(
                "Abra un proyecto para analizar llamadas."
            )

            return

        self.project_label.configure(
            text=f"Proyecto: {self._get_active_project_name()}"
        )

        try:
            candidate_directories = self._get_candidate_directories(
                project_path
            )

            loaded: List[TranscriptionModel] = []
            seen = set()

            for directory in candidate_directories:

                if not directory.exists():
                    continue

                if not directory.is_dir():
                    continue

                try:
                    items = TranscriptionService.scan_directory(
                        directory
                    )
                except Exception:
                    continue

                for transcription in items:

                    unique_key = self._transcription_unique_key(
                        transcription
                    )

                    if unique_key in seen:
                        continue

                    seen.add(unique_key)
                    loaded.append(transcription)

            self.transcriptions = sorted(
                loaded,
                key=lambda item: str(
                    item.file_name or ""
                ).lower(),
            )

            self._render_transcriptions()

        except Exception as error:

            self.transcriptions = []

            self._show_empty_message(
                "No fue posible cargar las transcripciones."
            )

            messagebox.showerror(
                "Analytics de Llamadas",
                "No fue posible cargar las transcripciones.\n\n"
                f"Detalle: {error}",
            )

    # =========================================================
    # DIRECTORIOS
    # =========================================================

    def _get_candidate_directories(
        self,
        project_path: Path,
    ) -> List[Path]:

        candidates: List[Path] = []

        standard = (
            project_path
            / "03_Transcripciones"
        )

        alternate = (
            project_path
            / "transcripciones"
        )

        if standard.exists() and standard.is_dir():
            candidates.append(
                standard.resolve()
            )

        if alternate.exists() and alternate.is_dir():

            resolved = alternate.resolve()

            if resolved not in candidates:
                candidates.append(
                    resolved
                )

        try:
            for directory in project_path.rglob("*"):

                if not directory.is_dir():
                    continue

                name = (
                    directory.name
                    .strip()
                    .lower()
                )

                if name in {
                    "transcripciones",
                    "03_transcripciones",
                }:

                    resolved = directory.resolve()

                    if resolved not in candidates:
                        candidates.append(
                            resolved
                        )

        except OSError:
            pass

        try:
            service_directory = (
                TranscriptionService
                .get_transcriptions_directory(
                    project_path
                )
                .resolve()
            )

            if service_directory not in candidates:
                candidates.insert(
                    0,
                    service_directory,
                )

        except Exception:
            pass

        return candidates

    # =========================================================
    # PROYECTO
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

                if isinstance(project, dict):

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

    # =========================================================
    # CLAVE ÚNICA
    # =========================================================

    @staticmethod
    def _transcription_unique_key(
        transcription: TranscriptionModel,
    ):
        json_path = str(
            getattr(
                transcription,
                "json_path",
                "",
            )
            or ""
        ).strip().lower()

        if json_path:
            return (
                "json",
                json_path,
            )

        txt_path = str(
            getattr(
                transcription,
                "txt_path",
                "",
            )
            or ""
        ).strip().lower()

        if txt_path:
            return (
                "txt",
                txt_path,
            )

        audio_path = str(
            getattr(
                transcription,
                "audio_path",
                "",
            )
            or ""
        ).strip().lower()

        if audio_path:
            return (
                "audio",
                audio_path,
            )

        return (
            "name",
            str(
                getattr(
                    transcription,
                    "file_name",
                    "",
                )
                or ""
            ).strip().lower(),
        )

    # =========================================================
    # RENDER LISTA
    # =========================================================

    def _render_transcriptions(self):
        self._clear_transcription_list()

        total = len(
            self.transcriptions
        )

        self.count_label.configure(
            text=(
                f"{total} archivo"
                if total == 1
                else f"{total} archivos"
            )
        )

        if not self.transcriptions:
            self._show_empty_message(
                "No se encontraron transcripciones "
                "en el proyecto activo."
            )
            return

        for index, transcription in enumerate(
            self.transcriptions
        ):

            display_name = Path(
                str(
                    transcription.file_name
                    or "Transcripción"
                )
            ).stem

            button = ctk.CTkButton(
                self.transcription_list,
                text=display_name,
                height=44,
                anchor="w",
                fg_color="#FFFFFF",
                hover_color="#E8DDFB",
                text_color=Theme.colors.TEXT_PRIMARY,
                border_width=1,
                border_color="#E3DDF0",
                corner_radius=9,
                command=lambda item=transcription: (
                    self.select_transcription(item)
                ),
            )

            button.grid(
                row=index,
                column=0,
                padx=2,
                pady=4,
                sticky="ew",
            )

            self.list_buttons[
                id(transcription)
            ] = button

    def _clear_transcription_list(self):
        for widget in self.transcription_list.winfo_children():
            widget.destroy()

        self.list_buttons.clear()

        self.count_label.configure(
            text="0 archivos"
        )

    def _show_empty_message(
        self,
        message: str,
    ):
        ctk.CTkLabel(
            self.transcription_list,
            text=message,
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
            wraplength=250,
            justify="left",
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=20,
            sticky="w",
        )

    # =========================================================
    # SELECCIONAR TRANSCRIPCIÓN
    # =========================================================

    def select_transcription(
        self,
        transcription: TranscriptionModel,
    ):
        self.selected_transcription = transcription
        self.current_analysis = None

        for button in self.list_buttons.values():
            button.configure(
                fg_color="#FFFFFF"
            )

        selected_button = self.list_buttons.get(
            id(transcription)
        )

        if selected_button is not None:
            selected_button.configure(
                fg_color="#E8DDFB"
            )

        display_name = Path(
            str(
                transcription.file_name
                or "Transcripción"
            )
        ).stem

        self.selected_file_label.configure(
            text=display_name
        )

        self.analyze_button.configure(
            state="normal",
            text="Analizar llamada",
        )

        self._clear_analysis(
            keep_selection=True
        )

        # =====================================================
        # BUSCAR ANÁLISIS YA GUARDADO
        # =====================================================

        project_path = self._get_active_project_path()

        if project_path is None:
            return

        try:
            saved_analysis = (
                AnalyticsService
                .find_analysis_for_transcription(
                    transcription,
                    project_path,
                )
            )

            if saved_analysis is not None:

                self.current_analysis = saved_analysis

                self._display_analysis(
                    saved_analysis
                )

                self.status_label.configure(
                    text=(
                        "✓ Análisis guardado previamente. "
                        "Puede volver a analizar la llamada si desea actualizarlo."
                    )
                )

                self.analyze_button.configure(
                    text="Volver a analizar"
                )

            else:
                self.status_label.configure(
                    text=(
                        "La llamada todavía no tiene "
                        "un análisis guardado."
                    )
                )

        except Exception:
            self.status_label.configure(
                text="Lista para analizar."
            )

    # =========================================================
    # ANALIZAR Y GUARDAR
    # =========================================================

    def validate_amount(self):
        transcription=self.selected_transcription
        if transcription is None or not transcription.json_path:
            messagebox.showinfo("Validar importe","Seleccione una transcripción JSON.")
            return
        data=transcription.metadata or {}
        entries=validated_entries(data.get("texto",transcription.text),transcription.segments,data.get("recuperacion_importes"))
        if not entries:
            messagebox.showinfo("Validar importe","Esta llamada no tiene importes recuperados válidos pendientes de confirmación.")
            return
        dialog=ctk.CTkToplevel(self);dialog.title("Confirmación de importe");dialog.geometry("700x400")
        dialog.transient(self.winfo_toplevel())
        ctk.CTkLabel(dialog,text="Marque solo los importes que haya comprobado en el audio.").pack(pady=16)
        variables={}
        for entry in entries:
            var=ctk.BooleanVar(value=False);variables[entry["anchor_start"]]=var
            ctk.CTkCheckBox(dialog,text=f"Confirmé ${entry['amount']:g} en el audio ({entry['inicio']:g}–{entry['fin']:g} s).",variable=var).pack(anchor="w",padx=18,pady=8)
        def save():
            try:
                anchors=[key for key,var in variables.items() if var.get()]
                record=AmountReviewService.save(transcription.json_path,anchors,audio_verified=bool(anchors))
                transcription.metadata["amount_audio_review"]=record
            except Exception as error:
                messagebox.showerror("Validar importe",str(error),parent=dialog);return
            dialog.destroy();self.analyze_selected()
        ctk.CTkButton(dialog,text="Guardar y volver a analizar",command=save).pack(pady=16)

    def validate_treatment(self):
        transcription = self.selected_transcription
        if transcription is None or not transcription.json_path:
            messagebox.showinfo("Validación de trato", "Seleccione una transcripción JSON de la llamada.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Validación de trato")
        dialog.geometry("640x350")
        dialog.transient(self.winfo_toplevel())
        ctk.CTkLabel(dialog, text="Marque solo lo que haya comprobado escuchando el audio.").pack(pady=16)
        labels = ["Escuché el audio de esta llamada.",
                  "El interlocutor fue hostil, ofensivo o lascivo.",
                  "Su conducta impidió completar el guion.",
                  "El gestor mantuvo un trato profesional."]
        current = transcription.metadata.get("hostile_interlocutor_exception") or {}
        variables = {key: ctk.BooleanVar(value=current.get(key) is True) for key in ReviewService.FLAGS}
        for key, label in zip(ReviewService.FLAGS, labels):
            ctk.CTkCheckBox(dialog, text=label, variable=variables[key]).pack(anchor="w", padx=24, pady=10)

        def save():
            try:
                flags = ReviewService.save(transcription.json_path, {key: value.get() for key, value in variables.items()})
                transcription.metadata["hostile_interlocutor_exception"] = flags
            except Exception as error:
                messagebox.showerror("Validación de trato", str(error), parent=dialog)
                return
            dialog.destroy()
            self.analyze_selected()

        ctk.CTkButton(dialog, text="Guardar y volver a analizar", command=save).pack(pady=16)

    def analyze_selected(self):
        if self.selected_transcription is None:

            messagebox.showwarning(
                "Analytics de Llamadas",
                "Seleccione una transcripción.",
            )

            return

        project_path = self._get_active_project_path()

        if project_path is None:

            messagebox.showwarning(
                "Analytics de Llamadas",
                "No existe un proyecto activo.",
            )

            return

        try:
            self.analyze_button.configure(
                state="disabled",
                text="Analizando...",
            )

            self.status_label.configure(
                text="Analizando llamada..."
            )

            self.update_idletasks()

            # =================================================
            # ANALIZAR
            # =================================================

            saved_context=dict((getattr(self.current_analysis,"metadata",{}) or {}).get("operational_context") or {})
            if not saved_context.get("corte"):
                saved_context["corte"]=saved_context.get("corte_aplicado")
            previous_decision=(getattr(self.current_analysis,"metadata",{}) or {}).get("shared_classification") or {}
            analysis = (
                AnalyticsService
                .analyze_transcription(
                    self.selected_transcription,
                    operational_context=saved_context
                )
            )

            shared = AnalyticsService.shared_quality_decision(
                getattr(analysis, "metadata", {}) or {},
                getattr(analysis, "compliance_score", 0),
                minimum_score=RelationService().get_minimum_score(),
                duration_seconds=getattr(self.selected_transcription, "duration_seconds", None),
                base_classification=previous_decision,
            )
            analysis.metadata["shared_classification"] = shared
            analysis.metadata["final_result"] = shared["clasificacion"]
            self.current_analysis = analysis

            # =================================================
            # GUARDAR AUTOMÁTICAMENTE
            # =================================================

            saved_path = (
                AnalyticsService
                .save_analysis(
                    analysis,
                    project_path,
                )
            )

            # =================================================
            # MOSTRAR RESULTADO
            # =================================================

            self._display_analysis(
                analysis
            )

            self.status_label.configure(
                text=(
                    "✓ Análisis guardado · "
                    f"{saved_path.name}"
                )
            )

        except Exception as error:

            self.status_label.configure(
                text="No fue posible completar el análisis."
            )

            messagebox.showerror(
                "Analytics de Llamadas",
                "No fue posible analizar la llamada.\n\n"
                f"Detalle: {error}",
            )

        finally:

            if self.selected_transcription is not None:
                self.analyze_button.configure(
                    state="normal",
                    text="Volver a analizar",
                )

    # =========================================================
    # MOSTRAR ANALYTICS
    # =========================================================

    def _display_analysis(
        self,
        analysis: AnalyticsModel,
    ):
        self.reason_value.configure(
            text=(
                analysis.call_reason
                or "No identificado"
            )
        )

        self.sentiment_value.configure(
            text=(
                analysis.sentiment
                or "neutral"
            ).capitalize()
        )

        compliance_text = (
            f"{analysis.compliance_score:.0f}%"
        )

        verdict = (analysis.metadata or {}).get("final_result") or analysis.compliance_status
        if verdict:
            compliance_text += (
                f" · {verdict.replace('_', ' ')}"
            )

        self.compliance_value.configure(
            text=compliance_text, wraplength=250
        )

        self.words_value.configure(
            text=str(
                analysis.word_count
            )
        )

        self._set_textbox(
            self.summary_box,
            analysis.summary
            or "No se generó resumen.",
        )

        keywords = (
            ", ".join(
                analysis.keywords
            )
            if analysis.keywords
            else "No se identificaron palabras clave."
        )

        self._set_textbox(
            self.keywords_box,
            keywords,
        )

    # =========================================================
    # TEXTBOX
    # =========================================================

    @staticmethod
    def _set_textbox(
        textbox,
        text,
    ):
        textbox.configure(
            state="normal"
        )

        textbox.delete(
            "1.0",
            "end",
        )

        textbox.insert(
            "1.0",
            str(text or ""),
        )

        textbox.configure(
            state="disabled"
        )

    # =========================================================
    # LIMPIAR
    # =========================================================

    def _clear_analysis(
        self,
        keep_selection=False,
    ):
        self.reason_value.configure(
            text="--"
        )

        self.sentiment_value.configure(
            text="--"
        )

        self.compliance_value.configure(
            text="--"
        )

        self.words_value.configure(
            text="--"
        )

        self._set_textbox(
            self.summary_box,
            "",
        )

        self._set_textbox(
            self.keywords_box,
            "",
        )

        if not keep_selection:

            self.selected_transcription = None
            self.current_analysis = None

            self.selected_file_label.configure(
                text="Seleccione una transcripción"
            )

            self.status_label.configure(
                text="Seleccione una llamada para comenzar."
            )

            self.analyze_button.configure(
                state="disabled",
                text="Analizar llamada",
            )
