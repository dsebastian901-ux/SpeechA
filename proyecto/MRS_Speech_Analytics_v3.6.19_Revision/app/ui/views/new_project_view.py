"""
============================================================
MRS Speech Analytics Professional
Vista: Nuevo proyecto
============================================================
"""

import customtkinter as ctk

from tkinter import filedialog, messagebox

from app.core import project_manager
from app.services.project_service import ProjectService


class NewProjectView(ctk.CTkFrame):
    """Pantalla para crear un nuevo proyecto."""

    def __init__(self, parent, on_project_created=None):
        super().__init__(
            parent,
            corner_radius=0
        )

        self.on_project_created = on_project_created

        self.grid_columnconfigure(
            0,
            weight=1
        )

        self.grid_rowconfigure(
            0,
            weight=1
        )

        self.create_interface()

    def create_interface(self):
        """Crea todos los controles de la pantalla."""

        self.content_frame = ctk.CTkFrame(
            self,
            corner_radius=12
        )

        self.content_frame.grid(
            row=0,
            column=0,
            padx=30,
            pady=30,
            sticky="nsew"
        )

        self.content_frame.grid_columnconfigure(
            1,
            weight=1
        )

        self.create_header()
        self.create_name_field()
        self.create_client_field()
        self.create_description_field()
        self.create_folder_field()
        self.create_action_button()

    def create_header(self):
        """Crea el encabezado de la vista."""

        self.title_label = ctk.CTkLabel(
            self.content_frame,
            text="Crear nuevo proyecto",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=26,
                weight="bold"
            )
        )

        self.title_label.grid(
            row=0,
            column=0,
            columnspan=3,
            padx=30,
            pady=(30, 10),
            sticky="w"
        )

        self.subtitle_label = ctk.CTkLabel(
            self.content_frame,
            text=(
                "Capture la información básica y seleccione "
                "la carpeta donde se guardará el proyecto."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14
            ),
            wraplength=700,
            justify="left"
        )

        self.subtitle_label.grid(
            row=1,
            column=0,
            columnspan=3,
            padx=30,
            pady=(0, 30),
            sticky="w"
        )

    def create_name_field(self):
        """Crea el campo de nombre del proyecto."""

        self.name_label = ctk.CTkLabel(
            self.content_frame,
            text="Nombre del proyecto:"
        )

        self.name_label.grid(
            row=2,
            column=0,
            padx=(30, 15),
            pady=10,
            sticky="w"
        )

        self.name_entry = ctk.CTkEntry(
            self.content_frame,
            height=38,
            placeholder_text="Ejemplo: Bradescard Julio 2026"
        )

        self.name_entry.grid(
            row=2,
            column=1,
            columnspan=2,
            padx=(0, 30),
            pady=10,
            sticky="ew"
        )

    def create_client_field(self):
        """Crea el selector de cliente."""

        self.client_label = ctk.CTkLabel(
            self.content_frame,
            text="Cliente:"
        )

        self.client_label.grid(
            row=3,
            column=0,
            padx=(30, 15),
            pady=10,
            sticky="w"
        )

        self.client_combo = ctk.CTkComboBox(
            self.content_frame,
            height=38,
            values=[
                "Bradescard",
                "Banco Azteca",
                "Sicrea",
                "Liverpool",
                "Coppel",
                "Personalizado"
            ]
        )

        self.client_combo.grid(
            row=3,
            column=1,
            columnspan=2,
            padx=(0, 30),
            pady=10,
            sticky="ew"
        )

        self.client_combo.set(
            "Bradescard"
        )

    def create_description_field(self):
        """Crea el campo de descripción."""

        self.description_label = ctk.CTkLabel(
            self.content_frame,
            text="Descripción:"
        )

        self.description_label.grid(
            row=4,
            column=0,
            padx=(30, 15),
            pady=10,
            sticky="nw"
        )

        self.description_textbox = ctk.CTkTextbox(
            self.content_frame,
            height=110
        )

        self.description_textbox.grid(
            row=4,
            column=1,
            columnspan=2,
            padx=(0, 30),
            pady=10,
            sticky="ew"
        )

    def create_folder_field(self):
        """Crea el campo para seleccionar la ubicación."""

        self.folder_label = ctk.CTkLabel(
            self.content_frame,
            text="Ubicación:"
        )

        self.folder_label.grid(
            row=5,
            column=0,
            padx=(30, 15),
            pady=10,
            sticky="w"
        )

        self.folder_entry = ctk.CTkEntry(
            self.content_frame,
            height=38,
            placeholder_text="Seleccione una carpeta"
        )

        self.folder_entry.grid(
            row=5,
            column=1,
            padx=(0, 10),
            pady=10,
            sticky="ew"
        )

        self.folder_button = ctk.CTkButton(
            self.content_frame,
            text="Examinar",
            width=100,
            height=38,
            command=self.select_folder
        )

        self.folder_button.grid(
            row=5,
            column=2,
            padx=(0, 30),
            pady=10
        )

    def create_action_button(self):
        """Crea el botón para registrar el proyecto."""

        self.create_button = ctk.CTkButton(
            self.content_frame,
            text="Crear proyecto",
            width=180,
            height=42,
            command=self.create_project
        )

        self.create_button.grid(
            row=6,
            column=1,
            columnspan=2,
            padx=30,
            pady=(25, 30),
            sticky="e"
        )

    def select_folder(self):
        """Selecciona la carpeta base para el proyecto."""

        selected_folder = filedialog.askdirectory(
            title="Seleccione dónde guardar el proyecto"
        )

        if not selected_folder:
            return

        self.folder_entry.delete(
            0,
            "end"
        )

        self.folder_entry.insert(
            0,
            selected_folder
        )

    def create_project(self):
        """Valida el formulario y crea el proyecto."""

        project_name = self.name_entry.get().strip()
        client = self.client_combo.get().strip()

        description = self.description_textbox.get(
            "1.0",
            "end"
        ).strip()

        base_path = self.folder_entry.get().strip()

        if not project_name:
            messagebox.showwarning(
                "Nombre requerido",
                "Capture el nombre del proyecto."
            )

            self.name_entry.focus()
            return

        if not client:
            messagebox.showwarning(
                "Cliente requerido",
                "Seleccione un cliente."
            )
            return

        if not base_path:
            messagebox.showwarning(
                "Ubicación requerida",
                "Seleccione la carpeta donde se guardará el proyecto."
            )
            return

        self.set_form_state(
            enabled=False
        )

        try:
            project_data = ProjectService.create_project(
                base_path=base_path,
                project_name=project_name,
                client=client,
                description=description
            )

            project_manager.set_current_project(
                project_data
            )

            messagebox.showinfo(
                "Proyecto creado",
                (
                    "El proyecto se creó correctamente.\n\n"
                    f"Nombre: {project_data['nombre']}\n"
                    f"Cliente: {project_data['cliente']}\n"
                    f"Ruta: {project_data['ruta']}"
                )
            )

            self.clear_form()

            self.set_form_state(
                enabled=True
            )

            # Debe ser la última acción porque cambia y destruye
            # la vista actual.
            if self.on_project_created is not None:
                self.on_project_created(
                    project_data
                )

        except Exception as error:
            self.set_form_state(
                enabled=True
            )

            messagebox.showerror(
                "Error al crear el proyecto",
                (
                    "No fue posible crear el proyecto.\n\n"
                    f"Detalle: {error}"
                )
            )

    def set_form_state(self, enabled):
        """Habilita o deshabilita los controles del formulario."""

        state = "normal" if enabled else "disabled"

        self.name_entry.configure(
            state=state
        )

        self.client_combo.configure(
            state=state
        )

        self.description_textbox.configure(
            state=state
        )

        self.folder_entry.configure(
            state=state
        )

        self.folder_button.configure(
            state=state
        )

        self.create_button.configure(
            state=state,
            text=(
                "Crear proyecto"
                if enabled
                else "Creando..."
            )
        )

    def clear_form(self):
        """Limpia los controles del formulario."""

        self.name_entry.delete(
            0,
            "end"
        )

        self.client_combo.set(
            "Bradescard"
        )

        self.description_textbox.delete(
            "1.0",
            "end"
        )

        self.folder_entry.delete(
            0,
            "end"
        )