"""
MRS Speech Analytics Professional
Vista: Abrir proyecto
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import customtkinter as ctk
from tkinter import TclError, filedialog, messagebox

from app.core import project_manager
from app.services.project_service import ProjectService
from app.ui.components.icon_factory import IconFactory
from app.ui.themes import Theme


ProjectCallback = Callable[[Dict[str, Any]], None]


class OpenProjectView(ctk.CTkFrame):
    """Pantalla para seleccionar, validar y abrir un proyecto."""

    def __init__(
        self,
        parent,
        on_project_opened: Optional[ProjectCallback] = None,
    ):
        super().__init__(
            parent,
            fg_color=Theme.colors.BACKGROUND,
            corner_radius=0,
        )

        self.on_project_opened = on_project_opened
        self.selected_file = ""
        self.selected_project_data: Optional[Dict[str, Any]] = None
        self.navigation_pending = False
        self.images: Dict[str, ctk.CTkImage] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_ui()

    def _build_ui(self):
        self.card = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.SURFACE,
            border_color=Theme.colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        )
        self.card.grid(
            row=0,
            column=0,
            padx=Theme.spacing.PAGE_X,
            pady=Theme.spacing.PAGE_Y,
            sticky="nsew",
        )

        self.card.grid_columnconfigure(0, weight=1)
        self.card.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_selector()
        self._build_info()
        self._build_actions()

    def _build_header(self):
        frame = ctk.CTkFrame(
            self.card,
            fg_color=Theme.colors.TRANSPARENT,
        )
        frame.grid(
            row=0,
            column=0,
            padx=Theme.spacing.XL,
            pady=(Theme.spacing.XL, Theme.spacing.LG),
            sticky="ew",
        )
        frame.grid_columnconfigure(1, weight=1)

        self.images["folder"] = IconFactory.create(
            "folder",
            size=30,
            color=Theme.colors.PRIMARY,
        )

        icon_box = ctk.CTkFrame(
            frame,
            width=60,
            height=60,
            fg_color=Theme.colors.PRIMARY_LIGHT,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        )
        icon_box.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(0, Theme.spacing.LG),
        )
        icon_box.grid_propagate(False)

        ctk.CTkLabel(
            icon_box,
            text="",
            image=self.images["folder"],
        ).place(
            relx=0.5,
            rely=0.5,
            anchor="center",
        )

        ctk.CTkLabel(
            frame,
            text="Abrir proyecto",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=26,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=0,
            column=1,
            sticky="sw",
        )

        ctk.CTkLabel(
            frame,
            text="Seleccione el archivo proyecto.json del proyecto.",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=14,
            ),
            anchor="w",
        ).grid(
            row=1,
            column=1,
            pady=(Theme.spacing.XS, 0),
            sticky="nw",
        )

        self.status_chip = ctk.CTkLabel(
            frame,
            text="Sin archivo",
            text_color=Theme.colors.TEXT_SECONDARY,
            fg_color=Theme.colors.PRIMARY_SOFT,
            corner_radius=999,
            padx=12,
            pady=5,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=11,
                weight="bold",
            ),
        )
        self.status_chip.grid(
            row=0,
            column=2,
            rowspan=2,
            padx=(Theme.spacing.LG, 0),
        )

    def _build_selector(self):
        frame = ctk.CTkFrame(
            self.card,
            fg_color=Theme.colors.PRIMARY_SOFT,
            border_color=Theme.colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        )
        frame.grid(
            row=1,
            column=0,
            padx=Theme.spacing.XL,
            pady=(0, Theme.spacing.LG),
            sticky="ew",
        )
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text="Archivo del proyecto",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=13,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            padx=(Theme.spacing.LG, Theme.spacing.MD),
            pady=Theme.spacing.LG,
            sticky="w",
        )

        self.file_entry = ctk.CTkEntry(
            frame,
            height=42,
            placeholder_text="Seleccione proyecto.json",
            fg_color=Theme.colors.SURFACE,
            text_color=Theme.colors.TEXT_PRIMARY,
            placeholder_text_color=Theme.colors.TEXT_MUTED,
            border_color=Theme.colors.BORDER,
            corner_radius=Theme.dimensions.RADIUS,
        )
        self.file_entry.grid(
            row=0,
            column=1,
            padx=(0, Theme.spacing.MD),
            pady=Theme.spacing.LG,
            sticky="ew",
        )
        self.file_entry.configure(state="readonly")

        self.select_button = ctk.CTkButton(
            frame,
            text="Examinar",
            width=120,
            height=42,
            fg_color=Theme.colors.PRIMARY,
            hover_color=Theme.colors.PRIMARY_HOVER,
            text_color=Theme.colors.TEXT_ON_PRIMARY,
            corner_radius=Theme.dimensions.RADIUS,
            command=self.select_project_file,
        )
        self.select_button.grid(
            row=0,
            column=2,
            padx=(0, Theme.spacing.LG),
            pady=Theme.spacing.LG,
        )

    def _build_info(self):
        self.info_frame = ctk.CTkFrame(
            self.card,
            fg_color=Theme.colors.SURFACE,
            border_color=Theme.colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=Theme.dimensions.RADIUS_LARGE,
        )
        self.info_frame.grid(
            row=2,
            column=0,
            padx=Theme.spacing.XL,
            pady=(0, Theme.spacing.LG),
            sticky="nsew",
        )
        self.info_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.info_frame,
            text="Información del proyecto",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=18,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            padx=Theme.spacing.LG,
            pady=(Theme.spacing.LG, Theme.spacing.MD),
            sticky="w",
        )

        self.name_value = self._info_row(1, "Nombre")
        self.client_value = self._info_row(2, "Cliente")
        self.path_value = self._info_row(3, "Ruta", 760)
        self.description_value = self._info_row(4, "Descripción", 760)
        self.version_value = self._info_row(5, "Versión")

    def _info_row(self, row, label, wraplength=0):
        ctk.CTkLabel(
            self.info_frame,
            text=f"{label}:",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=13,
                weight="bold",
            ),
            anchor="nw",
        ).grid(
            row=row,
            column=0,
            padx=(Theme.spacing.LG, Theme.spacing.MD),
            pady=Theme.spacing.SM,
            sticky="nw",
        )

        value = ctk.CTkLabel(
            self.info_frame,
            text="--",
            text_color=Theme.colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=13,
            ),
            anchor="w",
            justify="left",
            wraplength=wraplength,
        )
        value.grid(
            row=row,
            column=1,
            padx=(0, Theme.spacing.LG),
            pady=Theme.spacing.SM,
            sticky="ew",
        )
        return value

    def _build_actions(self):
        frame = ctk.CTkFrame(
            self.card,
            fg_color=Theme.colors.TRANSPARENT,
        )
        frame.grid(
            row=3,
            column=0,
            padx=Theme.spacing.XL,
            pady=(Theme.spacing.SM, Theme.spacing.XL),
            sticky="ew",
        )
        frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            frame,
            text="Seleccione un archivo proyecto.json.",
            text_color=Theme.colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family=Theme.fonts.FAMILY,
                size=12,
            ),
            anchor="w",
        )
        self.status_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.open_button = ctk.CTkButton(
            frame,
            text="Abrir proyecto",
            width=180,
            height=42,
            state="disabled",
            fg_color=Theme.colors.PRIMARY,
            hover_color=Theme.colors.PRIMARY_HOVER,
            text_color=Theme.colors.TEXT_ON_PRIMARY,
            corner_radius=Theme.dimensions.RADIUS,
            command=self.open_project,
        )
        self.open_button.grid(
            row=0,
            column=1,
            sticky="e",
        )

    def select_project_file(self):
        selected_file = filedialog.askopenfilename(
            title="Seleccione proyecto.json",
            filetypes=[
                ("Proyecto MRS", "proyecto.json"),
                ("Archivos JSON", "*.json"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if not selected_file:
            return

        self._set_busy(True, "Validando proyecto...")

        try:
            project_data = ProjectService.open_project(
                selected_file
            )

        except Exception as error:
            self._reset_selection()

            self.status_chip.configure(
                text="Proyecto inválido",
                text_color=Theme.colors.ERROR,
                fg_color=Theme.colors.ERROR_LIGHT,
            )

            self.status_label.configure(
                text="No fue posible validar el proyecto.",
                text_color=Theme.colors.ERROR,
            )

            messagebox.showerror(
                "Proyecto no válido",
                f"No fue posible validar el proyecto.\n\nDetalle: {error}",
            )
            return

        self.selected_file = selected_file
        self.selected_project_data = dict(project_data)

        self._set_entry(selected_file)
        self._show_project(project_data)

        self.status_chip.configure(
            text="Proyecto válido",
            text_color=Theme.colors.SUCCESS,
            fg_color=Theme.colors.SUCCESS_LIGHT,
        )

        self.status_label.configure(
            text="El proyecto está listo para abrirse.",
            text_color=Theme.colors.SUCCESS,
        )

        self.select_button.configure(state="normal")
        self.open_button.configure(
            state="normal",
            text="Abrir proyecto",
        )

    def open_project(self):
        if self.navigation_pending:
            return

        if not self.selected_file:
            messagebox.showwarning(
                "Archivo requerido",
                "Seleccione primero un archivo proyecto.json.",
            )
            return

        self._set_busy(True, "Abriendo proyecto...")

        try:
            project_data = ProjectService.open_project(
                self.selected_file
            )

            project_manager.set_current_project(
                project_data
            )

        except Exception as error:
            self.navigation_pending = False
            self._set_busy(
                False,
                "No fue posible abrir el proyecto.",
            )

            messagebox.showerror(
                "Error al abrir el proyecto",
                f"No fue posible abrir el proyecto.\n\nDetalle: {error}",
            )
            return

        messagebox.showinfo(
            "Proyecto abierto",
            (
                "El proyecto se abrió correctamente.\n\n"
                f"Nombre: {project_data['nombre']}\n"
                f"Cliente: {project_data['cliente']}\n"
                f"Ruta: {project_data['ruta']}"
            ),
        )

        if self.on_project_opened is None:
            self._set_busy(
                False,
                "Proyecto abierto correctamente.",
            )
            return

        self.navigation_pending = True
        callback = self.on_project_opened
        callback_data = dict(project_data)

        self.after_idle(
            lambda: self._navigate(
                callback,
                callback_data,
            )
        )

    def _navigate(self, callback, project_data):
        try:
            callback(project_data)

        except TclError:
            pass

        except Exception as error:
            self.navigation_pending = False

            try:
                if self.winfo_exists():
                    self._set_busy(
                        False,
                        "No fue posible cambiar de pantalla.",
                    )

                    messagebox.showerror(
                        "Error de navegación",
                        (
                            "El proyecto se abrió, pero no fue posible "
                            "mostrar Gestión de Audios.\n\n"
                            f"Detalle: {error}"
                        ),
                    )
            except TclError:
                pass

    def _show_project(self, project_data):
        self.name_value.configure(
            text=project_data.get("nombre", "--")
        )
        self.client_value.configure(
            text=project_data.get("cliente", "--")
        )
        self.path_value.configure(
            text=project_data.get("ruta", "--")
        )
        self.description_value.configure(
            text=project_data.get("descripcion", "--") or "--"
        )
        self.version_value.configure(
            text=project_data.get("version_proyecto", "--")
        )

    def _set_busy(self, busy, message):
        try:
            if not self.winfo_exists():
                return

            self.select_button.configure(
                state="disabled" if busy else "normal"
            )

            self.open_button.configure(
                state=(
                    "disabled"
                    if busy or not self.selected_project_data
                    else "normal"
                ),
                text="Abriendo..." if busy else "Abrir proyecto",
            )

            self.status_label.configure(
                text=message,
                text_color=(
                    Theme.colors.BLUE
                    if busy
                    else Theme.colors.TEXT_SECONDARY
                ),
            )

        except TclError:
            pass

    def _set_entry(self, value):
        try:
            self.file_entry.configure(state="normal")
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, value)
            self.file_entry.configure(state="readonly")
        except TclError:
            pass

    def _reset_selection(self):
        self.selected_file = ""
        self.selected_project_data = None
        self.navigation_pending = False

        self._set_entry("")

        for label in (
            self.name_value,
            self.client_value,
            self.path_value,
            self.description_value,
            self.version_value,
        ):
            try:
                label.configure(text="--")
            except TclError:
                pass

        try:
            self.select_button.configure(state="normal")
            self.open_button.configure(
                state="disabled",
                text="Abrir proyecto",
            )
        except TclError:
            pass
