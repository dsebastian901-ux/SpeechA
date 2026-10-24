"""
============================================================
MRS Speech Analytics Professional
Servicio: Gestión de transcripciones
============================================================
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import List, Optional

from app.models.transcriptions import TranscriptionModel
from app.services.review_service import ReviewService


class TranscriptionService:
    """
    Lee, organiza, actualiza y guarda las transcripciones
    generadas por Whisper.
    """

    TXT_EXTENSION = ".txt"
    JSON_EXTENSION = ".json"

    @staticmethod
    def _normalize_asr_money_display(text: str) -> str:
        """Normaliza solo separadores monetarios inequívocos producidos por ASR.

        No toca terminaciones, teléfonos, fechas ni referencias. Ejemplos:
        '7.200 pesos' / '7.2000 pesos' -> '7,200 pesos'.
        """
        value = str(text or "")
        # 7.2000 es un artefacto ASR inequívoco para este dominio: cuatro decimales
        # no representan centavos. Se normaliza aun cuando Whisper omita "pesos".
        value = re.sub(
            r"\b(\d{1,3})\.(\d{3})0\b",
            lambda m: f"{m.group(1)},{m.group(2)}",
            value,
        )
        # 7.200/4.500 se normalizan cuando están explícitamente ligados a pesos.
        pattern = re.compile(r"\b(\d{1,3})\.(\d{3})(?=\s*pesos?\b)", re.IGNORECASE)
        value = pattern.sub(lambda m: f"{m.group(1)},{m.group(2)}", value)
        return value

    @classmethod
    def scan_directory(
        cls,
        directory_path: str | Path,
    ) -> List[TranscriptionModel]:
        """
        Busca todos los archivos JSON y TXT disponibles
        dentro de una carpeta de transcripciones.
        """

        directory = Path(
            directory_path
        ).expanduser().resolve()

        if not directory.exists():
            return []

        if not directory.is_dir():
            raise NotADirectoryError(
                f"La ruta no es una carpeta:\n{directory}"
            )

        transcriptions: List[TranscriptionModel] = []

        json_files = sorted(
            directory.glob(
                f"*{cls.JSON_EXTENSION}"
            ),
            key=lambda path: path.name.lower(),
        )

        processed_names = set()

        for json_path in json_files:
            try:
                transcription = cls.load_from_json(
                    json_path
                )

                transcriptions.append(
                    transcription
                )

                processed_names.add(
                    json_path.stem.lower()
                )

            except Exception:
                # Un archivo dañado no debe impedir que
                # se carguen las demás transcripciones.
                continue

        txt_files = sorted(
            directory.glob(
                f"*{cls.TXT_EXTENSION}"
            ),
            key=lambda path: path.name.lower(),
        )

        for txt_path in txt_files:
            if txt_path.stem.lower() in processed_names:
                continue

            try:
                transcription = cls.load_from_txt(
                    txt_path
                )

                transcriptions.append(
                    transcription
                )

            except Exception:
                continue

        return sorted(
            transcriptions,
            key=lambda item: item.file_name.lower(),
        )

    @classmethod
    def load_from_json(
        cls,
        json_path: str | Path,
    ) -> TranscriptionModel:
        """
        Carga una transcripción desde el JSON generado
        por Whisper.
        """

        path = Path(
            json_path
        ).expanduser().resolve()

        cls._validate_file(
            path,
            cls.JSON_EXTENSION,
        )

        try:
            with path.open(
                mode="r",
                encoding="utf-8",
            ) as file:
                data = json.load(
                    file
                )

        except json.JSONDecodeError as error:
            raise ValueError(
                f"El archivo JSON contiene datos inválidos:\n{path.name}"
            ) from error

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                f"El archivo JSON no contiene una transcripción válida:\n"
                f"{path.name}"
            )

        txt_path = path.with_suffix(
            cls.TXT_EXTENSION
        )

        transcription = TranscriptionModel.from_dict(
            data=data,
            txt_path=(
                str(txt_path)
                if txt_path.exists()
                else ""
            ),
            json_path=str(
                path
            ),
        )

        if (
            not transcription.text.strip()
            and txt_path.exists()
        ):
            transcription.text = cls._read_text_file(
                txt_path
            )

        if not transcription.file_name:
            transcription.file_name = (
                cls._resolve_audio_file_name(
                    data=data,
                    fallback_name=path.stem,
                )
            )

        # v3.6.11: la vista y Analytics trabajan con una representación monetaria
        # normalizada, pero conservamos el texto crudo de Whisper en metadata.
        raw_text = str(transcription.text or "")
        normalized_text = cls._normalize_asr_money_display(raw_text)
        if normalized_text != raw_text:
            transcription.metadata = dict(transcription.metadata or {})
            transcription.metadata["texto_whisper_original"] = raw_text
            transcription.metadata["normalizacion_monetaria_asr"] = True
            transcription.text = normalized_text

        review = ReviewService.load(path)
        if review is not None:
            transcription.metadata["hostile_interlocutor_exception"] = review
        return transcription

    @classmethod
    def load_from_txt(
        cls,
        txt_path: str | Path,
    ) -> TranscriptionModel:
        """
        Carga una transcripción desde un archivo TXT
        cuando no existe JSON asociado.
        """

        path = Path(
            txt_path
        ).expanduser().resolve()

        cls._validate_file(
            path,
            cls.TXT_EXTENSION,
        )

        text = cls._read_text_file(
            path
        )

        json_path = path.with_suffix(
            cls.JSON_EXTENSION
        )

        return TranscriptionModel(
            file_name=path.name,
            audio_path="",
            text=text,
            txt_path=str(
                path
            ),
            json_path=(
                str(json_path)
                if json_path.exists()
                else ""
            ),
            metadata={
                "archivo": path.name,
                "texto": text,
                "ruta_txt": str(path),
            },
        )

    @classmethod
    def save(
        cls,
        transcription: TranscriptionModel,
    ) -> TranscriptionModel:
        """
        Guarda los cambios de una transcripción
        en TXT y JSON.
        """

        if not isinstance(
            transcription,
            TranscriptionModel,
        ):
            raise TypeError(
                "Se esperaba una instancia de TranscriptionModel."
            )

        txt_path = cls._resolve_txt_path(
            transcription
        )

        json_path = cls._resolve_json_path(
            transcription
        )

        txt_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        txt_path.write_text(
            transcription.text,
            encoding="utf-8",
        )

        metadata = dict(
            transcription.metadata
        )

        metadata.update(
            {
                "archivo": transcription.file_name,
                "ruta_audio": transcription.audio_path,
                "texto": transcription.text,
                "ruta_txt": str(txt_path),
                "ruta_json": str(json_path),
                "modelo": transcription.model_name,
                "dispositivo": transcription.device,
                "tipo_calculo": transcription.compute_type,
                "idioma_solicitado": (
                    transcription.requested_language
                ),
                "idioma_detectado": (
                    transcription.detected_language
                ),
                "probabilidad_idioma": (
                    transcription.language_probability
                ),
                "duracion_segundos": (
                    transcription.duration_seconds
                ),
                "duracion_legible": (
                    transcription.readable_duration
                ),
                "fecha_transcripcion": (
                    transcription.transcription_date
                ),
                "segmentos": list(
                    transcription.segments
                ),
            }
        )

        with json_path.open(
            mode="w",
            encoding="utf-8",
        ) as file:
            json.dump(
                metadata,
                file,
                ensure_ascii=False,
                indent=4,
            )

        transcription.txt_path = str(
            txt_path
        )

        transcription.json_path = str(
            json_path
        )

        transcription.metadata = metadata

        return transcription

    @classmethod
    def search(
        cls,
        transcriptions: List[TranscriptionModel],
        query: str,
    ) -> List[TranscriptionModel]:
        """
        Filtra transcripciones por nombre o contenido.
        """

        normalized_query = str(
            query
            or ""
        ).strip().lower()

        if not normalized_query:
            return list(
                transcriptions
            )

        results = []

        for transcription in transcriptions:
            searchable_text = " ".join(
                [
                    transcription.file_name,
                    transcription.audio_path,
                    transcription.text,
                    transcription.detected_language,
                    transcription.transcription_date,
                ]
            ).lower()

            if normalized_query in searchable_text:
                results.append(
                    transcription
                )

        return results

    @staticmethod
    def get_transcriptions_directory(
        project_path: str | Path,
    ) -> Path:
        """
        Obtiene la carpeta de transcripciones del proyecto.

        Primero busca 03_Transcripciones. Si no existe,
        busca una carpeta llamada transcripciones.
        """

        project_directory = Path(
            project_path
        ).expanduser().resolve()

        preferred_directory = (
            project_directory
            / "03_Transcripciones"
        )

        if preferred_directory.exists():
            return preferred_directory

        alternate_directory = (
            project_directory
            / "transcripciones"
        )

        if alternate_directory.exists():
            return alternate_directory

        preferred_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return preferred_directory

    @staticmethod
    def _validate_file(
        path: Path,
        expected_extension: str,
    ) -> None:
        """
        Valida existencia, tipo y extensión.
        """

        if not path.exists():
            raise FileNotFoundError(
                f"El archivo no existe:\n{path}"
            )

        if not path.is_file():
            raise ValueError(
                f"La ruta no corresponde a un archivo:\n{path}"
            )

        if path.suffix.lower() != expected_extension:
            raise ValueError(
                f"El archivo debe tener extensión "
                f"{expected_extension}:\n{path.name}"
            )

    @staticmethod
    def _read_text_file(
        path: Path,
    ) -> str:
        """
        Lee un archivo TXT en UTF-8.
        """

        try:
            return path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            return path.read_text(
                encoding="latin-1"
            )

    @staticmethod
    def _resolve_audio_file_name(
        data: dict,
        fallback_name: str,
    ) -> str:
        """
        Obtiene el nombre del audio desde los metadatos.
        """

        audio_name = str(
            data.get(
                "archivo",
                "",
            )
            or ""
        ).strip()

        if audio_name:
            return audio_name

        return fallback_name

    @staticmethod
    def _resolve_txt_path(
        transcription: TranscriptionModel,
    ) -> Path:
        """
        Obtiene la ruta TXT de una transcripción.
        """

        if transcription.txt_path:
            return Path(
                transcription.txt_path
            ).expanduser().resolve()

        if transcription.json_path:
            return Path(
                transcription.json_path
            ).expanduser().resolve().with_suffix(
                ".txt"
            )

        raise ValueError(
            "La transcripción no tiene una ruta para guardar el TXT."
        )

    @staticmethod
    def _resolve_json_path(
        transcription: TranscriptionModel,
    ) -> Path:
        """
        Obtiene la ruta JSON de una transcripción.
        """

        if transcription.json_path:
            return Path(
                transcription.json_path
            ).expanduser().resolve()

        if transcription.txt_path:
            return Path(
                transcription.txt_path
            ).expanduser().resolve().with_suffix(
                ".json"
            )

        raise ValueError(
            "La transcripción no tiene una ruta para guardar el JSON."
        )
