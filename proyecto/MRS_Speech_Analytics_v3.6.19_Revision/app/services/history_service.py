"""
============================================================
MRS Speech Analytics Professional
Servicio: Historial
============================================================
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class HistoryService:
    """
    Servicio encargado de construir el historial del proyecto.

    Historial v1:
    - Transcripciones
    - Analytics
    - Reportes exportados

    Este servicio solo consulta archivos existentes.
    No modifica el proyecto.
    """

    # =========================================================
    # HISTORIAL GENERAL
    # =========================================================

    @classmethod
    def get_history_data(
        cls,
        project_path,
    ) -> Dict[str, Any]:

        project_directory = (
            Path(project_path)
            .expanduser()
            .resolve()
        )

        transcriptions = cls.get_transcription_items(
            project_directory
        )

        analytics = cls.get_analytics_items(
            project_directory
        )

        reports = cls.get_report_items(
            project_directory
        )

        items = (
            transcriptions
            + analytics
            + reports
        )

        # Más reciente primero.
        items.sort(
            key=lambda item: item.get(
                "modified_timestamp",
                0.0,
            ),
            reverse=True,
        )

        return {
            "project_path": str(
                project_directory
            ),

            "generated_at": datetime.now().isoformat(
                timespec="seconds"
            ),

            "total_items": len(
                items
            ),

            "counts": {
                "transcriptions": len(
                    transcriptions
                ),

                "analytics": len(
                    analytics
                ),

                "reports": len(
                    reports
                ),
            },

            "items": items,
        }

    # =========================================================
    # TRANSCRIPCIONES
    # =========================================================

    @classmethod
    def get_transcription_items(
        cls,
        project_path,
    ) -> List[Dict[str, Any]]:
        """
        Busca transcripciones en las ubicaciones conocidas.

        Rutas soportadas:

        proyecto/03_Transcripciones
        proyecto/transcripciones
        proyecto/01_Audios/transcripciones

        Si existe JSON y TXT de la misma transcripción,
        se muestra una sola vez y se prefiere JSON.
        """

        project_directory = Path(
            project_path
        )

        directories = [
            project_directory
            / "03_Transcripciones",

            project_directory
            / "transcripciones",

            project_directory
            / "01_Audios"
            / "transcripciones",
        ]

        # -----------------------------------------------------
        # RECOLECTAR ARCHIVOS
        # -----------------------------------------------------

        found_files = []

        for directory in directories:

            if not directory.exists():
                continue

            if not directory.is_dir():
                continue

            for file_path in directory.rglob(
                "*"
            ):
                if not file_path.is_file():
                    continue

                extension = (
                    file_path.suffix
                    .lower()
                )

                if extension not in {
                    ".json",
                    ".txt",
                }:
                    continue

                try:
                    found_files.append(
                        file_path.resolve()
                    )

                except OSError:
                    found_files.append(
                        file_path
                    )

        # -----------------------------------------------------
        # AGRUPAR TXT + JSON
        # -----------------------------------------------------

        grouped = {}

        for file_path in found_files:

            key = str(
                file_path.with_suffix("")
            ).lower()

            existing = grouped.get(
                key
            )

            if existing is None:
                grouped[
                    key
                ] = file_path

                continue

            # Si ya tenemos TXT y aparece JSON,
            # damos preferencia al JSON.
            if (
                existing.suffix.lower() == ".txt"
                and file_path.suffix.lower() == ".json"
            ):
                grouped[
                    key
                ] = file_path

        # -----------------------------------------------------
        # CONSTRUIR REGISTROS
        # -----------------------------------------------------

        items = []

        for file_path in grouped.values():

            items.append(
                cls._build_item(
                    file_path=file_path,
                    item_type="transcription",
                    type_label="Transcripción",
                )
            )

        return items

    # =========================================================
    # ANALYTICS
    # =========================================================

    @classmethod
    def get_analytics_items(
        cls,
        project_path,
    ) -> List[Dict[str, Any]]:

        analytics_directory = (
            Path(project_path)
            / "04_Reportes"
            / "Analytics"
        )

        if not analytics_directory.exists():
            return []

        if not analytics_directory.is_dir():
            return []

        items = []

        for file_path in analytics_directory.rglob(
            "*.json"
        ):

            if not file_path.is_file():
                continue

            items.append(
                cls._build_item(
                    file_path=file_path,
                    item_type="analytics",
                    type_label="Analytics",
                )
            )

        return items

    # =========================================================
    # REPORTES
    # =========================================================

    @classmethod
    def get_report_items(
        cls,
        project_path,
    ) -> List[Dict[str, Any]]:

        reports_directory = (
            Path(project_path)
            / "04_Reportes"
            / "Exportados"
        )

        if not reports_directory.exists():
            return []

        if not reports_directory.is_dir():
            return []

        allowed_extensions = {
            ".json",
            ".csv",
            ".xlsx",
            ".pdf",
        }

        items = []

        for file_path in reports_directory.rglob(
            "*"
        ):

            if not file_path.is_file():
                continue

            if (
                file_path.suffix.lower()
                not in allowed_extensions
            ):
                continue

            items.append(
                cls._build_item(
                    file_path=file_path,
                    item_type="report",
                    type_label="Reporte",
                )
            )

        return items

    # =========================================================
    # CREAR REGISTRO
    # =========================================================

    @classmethod
    def _build_item(
        cls,
        file_path,
        item_type,
        type_label,
    ) -> Dict[str, Any]:

        file_path = Path(
            file_path
        )

        try:
            stat = file_path.stat()

            modified_timestamp = float(
                stat.st_mtime
            )

            size_bytes = int(
                stat.st_size
            )

        except OSError:
            modified_timestamp = 0.0
            size_bytes = 0

        if modified_timestamp > 0:

            modified_datetime = (
                datetime.fromtimestamp(
                    modified_timestamp
                )
            )

            modified_at = (
                modified_datetime.isoformat(
                    timespec="seconds"
                )
            )

            modified_display = (
                modified_datetime.strftime(
                    "%d/%m/%Y %H:%M"
                )
            )

        else:
            modified_at = ""
            modified_display = "Sin fecha"

        return {
            "type": item_type,

            "type_label": type_label,

            "file_name": file_path.name,

            "path": str(
                file_path
            ),

            "extension": (
                file_path.suffix
                .lower()
                .lstrip(".")
            ),

            "modified_at": modified_at,

            "modified_display": modified_display,

            "modified_timestamp": modified_timestamp,

            "size_bytes": size_bytes,

            "size_display": cls._format_size(
                size_bytes
            ),
        }

    # =========================================================
    # FORMATO DE TAMAÑO
    # =========================================================

    @staticmethod
    def _format_size(
        size_bytes,
    ) -> str:

        try:
            size = float(
                size_bytes
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):
            size = 0.0

        if size < 1024:
            return f"{int(size)} B"

        size /= 1024

        if size < 1024:
            return f"{size:.1f} KB"

        size /= 1024

        if size < 1024:
            return f"{size:.1f} MB"

        size /= 1024

        return f"{size:.1f} GB"

    # =========================================================
    # FILTROS
    # =========================================================

    @staticmethod
    def filter_items(
        items,
        item_type="",
        search_text="",
    ) -> List[Dict[str, Any]]:

        normalized_type = str(
            item_type
            or ""
        ).strip().lower()

        normalized_search = str(
            search_text
            or ""
        ).strip().lower()

        result = []

        for item in items:

            current_type = str(
                item.get(
                    "type",
                    "",
                )
                or ""
            ).lower()

            file_name = str(
                item.get(
                    "file_name",
                    "",
                )
                or ""
            ).lower()

            path = str(
                item.get(
                    "path",
                    "",
                )
                or ""
            ).lower()

            # -------------------------------------------------
            # FILTRO POR TIPO
            # -------------------------------------------------

            if (
                normalized_type
                and normalized_type != "all"
                and current_type != normalized_type
            ):
                continue

            # -------------------------------------------------
            # BÚSQUEDA
            # -------------------------------------------------

            if (
                normalized_search
                and normalized_search not in file_name
                and normalized_search not in path
            ):
                continue

            result.append(
                item
            )

        return result