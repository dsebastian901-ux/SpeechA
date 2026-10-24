"""
============================================================
MRS Speech Analytics Professional
Gestor central de proyectos
============================================================
"""

from pathlib import Path


class ProjectManager:
    """
    Mantiene el proyecto activo durante la ejecución
    de la aplicación.
    """

    def __init__(self):
        self.current_project = None

    def set_current_project(self, project_data):
        """
        Establece un proyecto como proyecto activo.

        Args:
            project_data (dict): Información cargada desde proyecto.json
            o generada al crear el proyecto.
        """

        if not isinstance(project_data, dict):
            raise TypeError(
                "La información del proyecto debe ser un diccionario."
            )

        required_fields = [
            "nombre",
            "cliente",
            "ruta"
        ]

        missing_fields = [
            field
            for field in required_fields
            if not project_data.get(field)
        ]

        if missing_fields:
            fields = ", ".join(missing_fields)

            raise ValueError(
                f"Faltan datos obligatorios del proyecto: {fields}"
            )

        project_path = Path(project_data["ruta"])

        if not project_path.exists():
            raise FileNotFoundError(
                "La carpeta del proyecto no existe."
            )

        self.current_project = project_data

    def close_project(self):
        """Cierra el proyecto activo."""

        self.current_project = None

    def has_open_project(self):
        """Indica si existe un proyecto abierto."""

        return self.current_project is not None

    def get_current_project(self):
        """Devuelve la información del proyecto activo."""

        return self.current_project

    def get_project_name(self):
        """Devuelve el nombre del proyecto activo."""

        if not self.has_open_project():
            return "Sin proyecto abierto"

        return self.current_project.get(
            "nombre",
            "Proyecto sin nombre"
        )

    def get_project_client(self):
        """Devuelve el cliente del proyecto activo."""

        if not self.has_open_project():
            return "Sin cliente"

        return self.current_project.get(
            "cliente",
            "Cliente no definido"
        )

    def get_project_path(self):
        """Devuelve la ruta del proyecto activo."""

        if not self.has_open_project():
            return None

        return Path(self.current_project["ruta"])