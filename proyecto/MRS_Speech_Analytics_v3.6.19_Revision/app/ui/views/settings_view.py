"""
============================================================
MRS Speech Analytics Professional
Vista: Configuración
============================================================
"""

import customtkinter as ctk
from tkinter import messagebox

from app.services.settings_service import SettingsService
from app.ui.themes import Theme


class SettingsView(ctk.CTkFrame):
    """
    Vista de configuración general.

    Permite editar:
    - Apariencia
    - Modelo Whisper
    - Idioma
    - Dispositivo
    - Tipo de cálculo
    - Beam size
    - VAD
    - Word timestamps
    - Máximo de workers
    - Tamaño de lote
    - Puntaje mínimo
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        self.current_settings = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_content()

        self.load_settings()

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
            text="CONFIGURACIÓN",
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

        ctk.CTkLabel(
            self.header,
            text="Preferencias generales de la aplicación",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
            anchor="w",
        ).grid(
            row=1,
            column=0,
            padx=24,
            pady=(0, 18),
            sticky="w",
        )

        self.save_button = ctk.CTkButton(
            self.header,
            text="Guardar cambios",
            width=140,
            height=36,
            fg_color=Theme.colors.PRIMARY,
            corner_radius=9,
            command=self.save_settings,
        )

        self.save_button.grid(
            row=0,
            column=1,
            padx=(10, 8),
            pady=18,
            sticky="e",
        )

        self.reset_button = ctk.CTkButton(
            self.header,
            text="Restablecer",
            width=110,
            height=36,
            fg_color="#EDEDF4",
            hover_color="#DEDEE9",
            text_color=Theme.colors.TEXT_PRIMARY,
            corner_radius=9,
            command=self.reset_settings,
        )

        self.reset_button.grid(
            row=0,
            column=2,
            padx=(0, 24),
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

        self._build_appearance_panel()
        self._build_whisper_panel()
        self._build_processing_panel()
        self._build_quality_panel()

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
            row=4,
            column=0,
            padx=4,
            pady=(12, 4),
            sticky="ew",
        )

    # =========================================================
    # PANEL APARIENCIA
    # =========================================================

    def _build_appearance_panel(self):
        panel = self._create_panel(
            row=0,
            title="Apariencia",
            subtitle="Preferencias visuales de la aplicación.",
        )

        self.appearance_combo = self._create_combo_row(
            panel=panel,
            row=2,
            label="Modo de apariencia",
            values=SettingsService.APPEARANCE_MODES,
        )

        self.color_theme_entry = self._create_entry_row(
            panel=panel,
            row=3,
            label="Tema de color",
            placeholder="blue",
        )

    # =========================================================
    # PANEL WHISPER
    # =========================================================

    def _build_whisper_panel(self):
        panel = self._create_panel(
            row=1,
            title="Transcripción / Whisper",
            subtitle=(
                "Configuración del motor de transcripción. "
                "Algunos cambios requieren reiniciar la aplicación."
            ),
        )

        self.whisper_model_combo = self._create_combo_row(
            panel=panel,
            row=2,
            label="Modelo Whisper",
            values=SettingsService.WHISPER_MODELS,
        )

        self.whisper_language_combo = self._create_combo_row(
            panel=panel,
            row=3,
            label="Idioma",
            values=SettingsService.WHISPER_LANGUAGES,
        )

        self.whisper_device_combo = self._create_combo_row(
            panel=panel,
            row=4,
            label="Dispositivo",
            values=SettingsService.WHISPER_DEVICES,
        )

        self.compute_type_combo = self._create_combo_row(
            panel=panel,
            row=5,
            label="Tipo de cálculo",
            values=SettingsService.COMPUTE_TYPES,
        )

        self.beam_size_entry = self._create_entry_row(
            panel=panel,
            row=6,
            label="Beam size",
            placeholder="5",
        )

        self.vad_switch = self._create_switch_row(
            panel=panel,
            row=7,
            label="Filtro VAD",
        )

        self.word_timestamps_switch = self._create_switch_row(
            panel=panel,
            row=8,
            label="Word timestamps",
        )

    # =========================================================
    # PANEL PROCESAMIENTO
    # =========================================================

    def _build_processing_panel(self):
        panel = self._create_panel(
            row=2,
            title="Procesamiento",
            subtitle="Parámetros generales de ejecución.",
        )

        self.max_workers_entry = self._create_entry_row(
            panel=panel,
            row=2,
            label="Máximo de workers",
            placeholder="2",
        )

        self.batch_size_entry = self._create_entry_row(
            panel=panel,
            row=3,
            label="Tamaño de lote",
            placeholder="10",
        )

    # =========================================================
    # PANEL CALIDAD
    # =========================================================

    def _build_quality_panel(self):
        panel = self._create_panel(
            row=3,
            title="Calidad",
            subtitle="Parámetros utilizados por las reglas de evaluación.",
        )

        self.minimum_score_entry = self._create_entry_row(
            panel=panel,
            row=2,
            label="Puntaje mínimo",
            placeholder="80",
        )

    # =========================================================
    # CREAR PANEL
    # =========================================================

    def _create_panel(
        self,
        row,
        title,
        subtitle,
    ):
        panel = ctk.CTkFrame(
            self.content,
            fg_color=Theme.colors.SURFACE,
            corner_radius=15,
            border_width=1,
            border_color=Theme.colors.BORDER_LIGHT,
        )

        panel.grid(
            row=row,
            column=0,
            pady=(0, 12),
            sticky="ew",
        )

        panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            panel,
            text=title,
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
            columnspan=2,
            padx=20,
            pady=(18, 3),
            sticky="ew",
        )

        ctk.CTkLabel(
            panel,
            text=subtitle,
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            padx=20,
            pady=(0, 12),
            sticky="ew",
        )

        return panel

    # =========================================================
    # COMBO ROW
    # =========================================================

    def _create_combo_row(
        self,
        panel,
        row,
        label,
        values,
    ):
        ctk.CTkLabel(
            panel,
            text=label,
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
            anchor="w",
        ).grid(
            row=row,
            column=0,
            padx=(20, 12),
            pady=8,
            sticky="w",
        )

        combo = ctk.CTkComboBox(
            panel,
            values=values,
            width=240,
            height=36,
            state="readonly",
        )

        combo.grid(
            row=row,
            column=1,
            padx=(0, 20),
            pady=8,
            sticky="e",
        )

        return combo

    # =========================================================
    # ENTRY ROW
    # =========================================================

    def _create_entry_row(
        self,
        panel,
        row,
        label,
        placeholder,
    ):
        ctk.CTkLabel(
            panel,
            text=label,
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
            anchor="w",
        ).grid(
            row=row,
            column=0,
            padx=(20, 12),
            pady=8,
            sticky="w",
        )

        entry = ctk.CTkEntry(
            panel,
            width=240,
            height=36,
            placeholder_text=placeholder,
        )

        entry.grid(
            row=row,
            column=1,
            padx=(0, 20),
            pady=8,
            sticky="e",
        )

        return entry

    # =========================================================
    # SWITCH ROW
    # =========================================================

    def _create_switch_row(
        self,
        panel,
        row,
        label,
    ):
        ctk.CTkLabel(
            panel,
            text=label,
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
            anchor="w",
        ).grid(
            row=row,
            column=0,
            padx=(20, 12),
            pady=8,
            sticky="w",
        )

        switch = ctk.CTkSwitch(
            panel,
            text="",
            width=50,
        )

        switch.grid(
            row=row,
            column=1,
            padx=(0, 20),
            pady=8,
            sticky="e",
        )

        return switch

    # =========================================================
    # CARGAR CONFIGURACIÓN
    # =========================================================

    def load_settings(self):
        try:
            data = SettingsService.load()

            self.current_settings = data

            self.appearance_combo.set(
                data.get(
                    "appearance",
                    "System",
                )
            )

            self.color_theme_entry.delete(
                0,
                "end",
            )

            self.color_theme_entry.insert(
                0,
                data.get(
                    "color_theme",
                    "blue",
                ),
            )

            self.whisper_model_combo.set(
                data.get(
                    "whisper_model",
                    "small",
                )
            )

            self.whisper_language_combo.set(
                data.get(
                    "whisper_language",
                    "es",
                )
            )

            self.whisper_device_combo.set(
                data.get(
                    "whisper_device",
                    "cpu",
                )
            )

            self.compute_type_combo.set(
                data.get(
                    "whisper_compute_type",
                    "int8",
                )
            )

            self._set_entry(
                self.beam_size_entry,
                data.get(
                    "whisper_beam_size",
                    5,
                ),
            )

            self._set_entry(
                self.max_workers_entry,
                data.get(
                    "max_workers",
                    2,
                ),
            )

            self._set_entry(
                self.batch_size_entry,
                data.get(
                    "process_batch_size",
                    10,
                ),
            )

            self._set_entry(
                self.minimum_score_entry,
                data.get(
                    "minimum_score",
                    80,
                ),
            )

            if data.get(
                "whisper_vad_filter",
                True,
            ):
                self.vad_switch.select()
            else:
                self.vad_switch.deselect()

            if data.get(
                "whisper_word_timestamps",
                False,
            ):
                self.word_timestamps_switch.select()
            else:
                self.word_timestamps_switch.deselect()

            self.status_label.configure(
                text="Configuración cargada."
            )

        except Exception as error:
            messagebox.showerror(
                "Configuración",
                "No fue posible cargar la configuración.\n\n"
                f"Detalle: {error}",
            )

    # =========================================================
    # GUARDAR
    # =========================================================

    def save_settings(self):
        try:
            data = {
                "appearance": self.appearance_combo.get(),

                "color_theme": self.color_theme_entry.get(),

                "whisper_model": self.whisper_model_combo.get(),

                "whisper_language": self.whisper_language_combo.get(),

                "whisper_device": self.whisper_device_combo.get(),

                "whisper_compute_type": self.compute_type_combo.get(),

                "whisper_beam_size": self.beam_size_entry.get(),

                "whisper_vad_filter": bool(
                    self.vad_switch.get()
                ),

                "whisper_word_timestamps": bool(
                    self.word_timestamps_switch.get()
                ),

                "max_workers": self.max_workers_entry.get(),

                "process_batch_size": self.batch_size_entry.get(),

                "minimum_score": self.minimum_score_entry.get(),
            }

            output = SettingsService.save(
                data
            )

            validated = SettingsService.load()

            self.current_settings = validated

            # Aplicar apariencia inmediatamente.
            ctk.set_appearance_mode(
                validated.get(
                    "appearance",
                    "System",
                )
            )

            self.status_label.configure(
                text=(
                    "✓ Configuración guardada · "
                    f"{output.name}"
                )
            )

            messagebox.showinfo(
                "Configuración",
                (
                    "Configuración guardada correctamente.\n\n"
                    "Los cambios de apariencia se aplican de inmediato.\n"
                    "Los cambios de Whisper se utilizarán cuando "
                    "el servicio de transcripción los lea."
                ),
            )

        except Exception as error:
            messagebox.showerror(
                "Configuración",
                "No fue posible guardar la configuración.\n\n"
                f"Detalle: {error}",
            )

    # =========================================================
    # RESTABLECER
    # =========================================================

    def reset_settings(self):
        confirmed = messagebox.askyesno(
            "Configuración",
            (
                "¿Desea restablecer todos los valores "
                "a la configuración predeterminada?"
            ),
        )

        if not confirmed:
            return

        try:
            defaults = SettingsService.reset()

            self.current_settings = defaults

            self.load_settings()

            ctk.set_appearance_mode(
                defaults.get(
                    "appearance",
                    "System",
                )
            )

            self.status_label.configure(
                text="✓ Configuración restablecida."
            )

        except Exception as error:
            messagebox.showerror(
                "Configuración",
                "No fue posible restablecer la configuración.\n\n"
                f"Detalle: {error}",
            )

    # =========================================================
    # UTILIDAD ENTRY
    # =========================================================

    @staticmethod
    def _set_entry(
        entry,
        value,
    ):
        entry.delete(
            0,
            "end",
        )

        entry.insert(
            0,
            str(value),
        )