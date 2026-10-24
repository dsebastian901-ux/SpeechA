"""
MRS Speech Analytics Professional
Servicio: Gestión de proyectos
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class ProjectService:
    """Administra la creación, apertura y validación de proyectos."""

    PROJECT_FOLDERS = [
        "01_Audios",
        "02_Excel",
        "03_Transcripciones",
        "04_Reportes",
        "05_Excelentes",
        "06_Configuracion",
        "07_Logs",
        "08_Temporal",
    ]

    REQUIRED_FIELDS = ("nombre", "cliente", "ruta")

    @staticmethod
    def sanitize_project_name(project_name: str) -> str:
        clean_name = str(project_name or "").strip()
        clean_name = re.sub(r'[<>:"/\\|?*]', "-", clean_name)
        return re.sub(r"\s+", " ", clean_name)

    @classmethod
    def create_project(
        cls,
        base_path,
        project_name,
        client,
        description="",
    ) -> Dict[str, Any]:
        project_name = cls.sanitize_project_name(project_name)
        client = str(client or "").strip()

        if not project_name:
            raise ValueError("El nombre del proyecto no puede estar vacío.")
        if not client:
            raise ValueError("Debe seleccionar un cliente.")
        if not base_path:
            raise ValueError("Debe seleccionar una ubicación para guardar el proyecto.")

        base_directory = Path(base_path).expanduser().resolve()
        if not base_directory.exists():
            raise FileNotFoundError(f"La ubicación seleccionada no existe:\n{base_directory}")
        if not base_directory.is_dir():
            raise NotADirectoryError(f"La ubicación seleccionada no es una carpeta:\n{base_directory}")

        project_directory = base_directory / project_name
        if project_directory.exists():
            raise FileExistsError(
                f"Ya existe un proyecto llamado '{project_name}' en la ubicación seleccionada."
            )

        try:
            project_directory.mkdir(parents=True, exist_ok=False)
            for folder_name in cls.PROJECT_FOLDERS:
                (project_directory / folder_name).mkdir()

            project_data = {
                "nombre": project_name,
                "cliente": client,
                "descripcion": str(description or "").strip(),
                "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
                "ruta": str(project_directory.resolve()),
                "estado": "activo",
                "version_proyecto": "1.0",
            }

            with (project_directory / "proyecto.json").open("w", encoding="utf-8") as file:
                json.dump(project_data, file, ensure_ascii=False, indent=4)

            return project_data

        except Exception:
            cls._remove_incomplete_project(project_directory)
            raise

    @classmethod
    def open_project(cls, project_file_path) -> Dict[str, Any]:
        if not project_file_path:
            raise ValueError("Debe seleccionar un archivo proyecto.json.")

        project_file = Path(project_file_path).expanduser().resolve()
        if not project_file.exists() or not project_file.is_file():
            raise FileNotFoundError(f"El archivo del proyecto no existe:\n{project_file}")
        if project_file.suffix.lower() != ".json":
            raise ValueError("El archivo seleccionado debe ser un archivo JSON.")

        try:
            with project_file.open("r", encoding="utf-8") as file:
                project_data = json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError("El archivo proyecto.json contiene JSON inválido.") from error

        if not isinstance(project_data, dict):
            raise ValueError("El archivo proyecto.json no contiene un objeto válido.")

        missing_fields = [
            field for field in cls.REQUIRED_FIELDS
            if not str(project_data.get(field, "")).strip()
        ]
        if missing_fields:
            raise ValueError(
                "El proyecto no contiene los campos obligatorios: " + ", ".join(missing_fields)
            )

        project_directory = Path(str(project_data["ruta"])).expanduser()
        if not project_directory.is_absolute():
            project_directory = (project_file.parent / project_directory).resolve()
        else:
            project_directory = project_directory.resolve()

        if not project_directory.exists():
            project_directory = project_file.parent.resolve()
        if not project_directory.is_dir():
            raise NotADirectoryError("La ruta registrada del proyecto no es una carpeta.")

        normalized_data = dict(project_data)
        normalized_data["nombre"] = str(normalized_data["nombre"]).strip()
        normalized_data["cliente"] = str(normalized_data["cliente"]).strip()
        normalized_data["ruta"] = str(project_directory)
        return normalized_data

    @staticmethod
    def _remove_incomplete_project(project_directory: Path) -> None:
        if not project_directory.exists():
            return
        for item in sorted(project_directory.rglob("*"), reverse=True):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                item.rmdir()
        project_directory.rmdir()
