"""
============================================================
MRS Speech Analytics Professional
Servicio: Gestión y exploración de audios
============================================================
"""

from pathlib import Path


class AudioService:
    """Servicio encargado de localizar y preparar archivos de audio."""

    SUPPORTED_EXTENSIONS = {
        ".mp3",
        ".wav",
        ".ogg",
        ".m4a",
        ".flac",
        ".aac",
        ".wma"
    }

    @classmethod
    def is_supported(cls, file_path):
        """
        Indica si un archivo tiene una extensión de audio compatible.
        """

        path = Path(file_path)

        return (
            path.is_file()
            and path.suffix.lower() in cls.SUPPORTED_EXTENSIONS
        )

    @staticmethod
    def get_extension(file_path):
        """
        Obtiene la extensión del archivo en minúsculas.
        """

        return Path(file_path).suffix.lower()

    @staticmethod
    def get_size(file_path):
        """
        Obtiene el tamaño del archivo en bytes.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"No existe el archivo: {path}"
            )

        return path.stat().st_size

    @classmethod
    def search_audio_files(cls, folder_path):
        """
        Busca archivos de audio en una carpeta y sus subcarpetas.

        Retorna:
            list[Path]: lista ordenada de archivos compatibles.
        """

        if not folder_path:
            raise ValueError(
                "Debe proporcionar una carpeta para buscar audios."
            )

        folder = Path(folder_path)

        if not folder.exists():
            raise FileNotFoundError(
                f"La carpeta no existe: {folder}"
            )

        if not folder.is_dir():
            raise NotADirectoryError(
                f"La ruta no corresponde a una carpeta: {folder}"
            )

        audio_files = [
            file_path
            for file_path in folder.rglob("*")
            if cls.is_supported(file_path)
        ]

        audio_files.sort(
            key=lambda item: str(item).lower()
        )

        return audio_files

    @classmethod
    def create_audio_record(cls, file_path):
        """
        Convierte un archivo en un registro preparado para el sistema.
        """

        path = Path(file_path).resolve()
        size_bytes = cls.get_size(path)

        return {
            "nombre": path.name,
            "ruta": str(path),
            "carpeta": str(path.parent),
            "extension": cls.get_extension(path),
            "tamano_bytes": size_bytes,
            "tamano_legible": cls.format_size(size_bytes),
            "estado": "Pendiente",
            "duracion_segundos": None,
            "duracion_legible": "--",
            "transcripcion": None,
            "resultado": None,
            "error": None
        }

    @classmethod
    def scan_folder(cls, folder_path):
        """
        Explora una carpeta y genera los registros de audio.

        Retorna:
            dict:
                carpeta
                audios
                estadisticas
        """

        folder = Path(folder_path).resolve()

        audio_files = cls.search_audio_files(
            folder
        )

        audio_records = [
            cls.create_audio_record(file_path)
            for file_path in audio_files
        ]

        statistics = cls.get_statistics(
            audio_records
        )

        return {
            "carpeta": str(folder),
            "audios": audio_records,
            "estadisticas": statistics
        }

    @classmethod
    def get_statistics(cls, audio_records):
        """
        Calcula estadísticas de una lista de registros de audio.
        """

        total_files = len(audio_records)

        total_size = sum(
            audio.get("tamano_bytes", 0)
            for audio in audio_records
        )

        extensions = {}

        for audio in audio_records:
            extension = audio.get(
                "extension",
                "desconocido"
            )

            extensions[extension] = (
                extensions.get(extension, 0) + 1
            )

        empty_files = sum(
            1
            for audio in audio_records
            if audio.get("tamano_bytes", 0) == 0
        )

        return {
            "total_archivos": total_files,
            "tamano_total_bytes": total_size,
            "tamano_total_legible": cls.format_size(
                total_size
            ),
            "archivos_vacios": empty_files,
            "por_extension": extensions
        }

    @staticmethod
    def format_size(size_bytes):
        """
        Convierte bytes a un formato legible.
        """

        size = float(size_bytes)

        units = [
            "B",
            "KB",
            "MB",
            "GB",
            "TB"
        ]

        for unit in units:
            if size < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} {unit}"

                return f"{size:.2f} {unit}"

            size /= 1024

        return f"{size_bytes} B"