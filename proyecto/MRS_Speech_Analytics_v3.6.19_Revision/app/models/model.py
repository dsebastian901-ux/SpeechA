"""
============================================================
MRS Speech Analytics Professional
Modelo: Transcripción
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TranscriptionModel:
    """
    Representa una transcripción generada por Whisper.

    Este modelo reúne la información del archivo TXT y JSON
    asociado a un audio procesado.
    """

    file_name: str
    audio_path: str
    text: str

    txt_path: str = ""
    json_path: str = ""

    model_name: str = ""
    device: str = ""
    compute_type: str = ""

    requested_language: str = ""
    detected_language: str = ""
    language_probability: float = 0.0

    duration_seconds: float = 0.0
    readable_duration: str = "00:00:00"

    transcription_date: str = ""

    segments: List[Dict[str, Any]] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def base_name(self) -> str:
        """
        Devuelve el nombre del archivo sin extensión.
        """

        return Path(
            self.file_name
        ).stem

    @property
    def has_text(self) -> bool:
        """
        Indica si la transcripción contiene texto.
        """

        return bool(
            self.text.strip()
        )

    @property
    def has_segments(self) -> bool:
        """
        Indica si la transcripción contiene segmentos.
        """

        return bool(
            self.segments
        )

    @property
    def exists_txt(self) -> bool:
        """
        Indica si el archivo TXT existe.
        """

        if not self.txt_path:
            return False

        return Path(
            self.txt_path
        ).exists()

    @property
    def exists_json(self) -> bool:
        """
        Indica si el archivo JSON existe.
        """

        if not self.json_path:
            return False

        return Path(
            self.json_path
        ).exists()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el modelo a diccionario.
        """

        return {
            "file_name": self.file_name,
            "audio_path": self.audio_path,
            "text": self.text,
            "txt_path": self.txt_path,
            "json_path": self.json_path,
            "model_name": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "requested_language": self.requested_language,
            "detected_language": self.detected_language,
            "language_probability": self.language_probability,
            "duration_seconds": self.duration_seconds,
            "readable_duration": self.readable_duration,
            "transcription_date": self.transcription_date,
            "segments": list(
                self.segments
            ),
            "metadata": dict(
                self.metadata
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        txt_path: Optional[str] = None,
        json_path: Optional[str] = None,
    ) -> "TranscriptionModel":
        """
        Crea una instancia a partir del JSON generado por Whisper.
        """

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "Los datos de la transcripción deben ser un diccionario."
            )

        return cls(
            file_name=str(
                data.get(
                    "archivo",
                    "",
                )
            ),
            audio_path=str(
                data.get(
                    "ruta_audio",
                    "",
                )
            ),
            text=str(
                data.get(
                    "texto",
                    "",
                )
                or ""
            ),
            txt_path=str(
                txt_path
                or data.get(
                    "ruta_txt",
                    "",
                )
                or ""
            ),
            json_path=str(
                json_path
                or data.get(
                    "ruta_json",
                    "",
                )
                or ""
            ),
            model_name=str(
                data.get(
                    "modelo",
                    "",
                )
            ),
            device=str(
                data.get(
                    "dispositivo",
                    "",
                )
            ),
            compute_type=str(
                data.get(
                    "tipo_calculo",
                    "",
                )
            ),
            requested_language=str(
                data.get(
                    "idioma_solicitado",
                    "",
                )
            ),
            detected_language=str(
                data.get(
                    "idioma_detectado",
                    "",
                )
            ),
            language_probability=float(
                data.get(
                    "probabilidad_idioma",
                    0.0,
                )
                or 0.0
            ),
            duration_seconds=float(
                data.get(
                    "duracion_segundos",
                    0.0,
                )
                or 0.0
            ),
            readable_duration=str(
                data.get(
                    "duracion_legible",
                    "00:00:00",
                )
            ),
            transcription_date=str(
                data.get(
                    "fecha_transcripcion",
                    "",
                )
            ),
            segments=list(
                data.get(
                    "segmentos",
                    [],
                )
                or []
            ),
            metadata=dict(
                data
            ),
        )

    def update_text(
        self,
        new_text: str,
    ) -> None:
        """
        Actualiza el texto de la transcripción.
        """

        self.text = str(
            new_text
            or ""
        )

        self.metadata[
            "texto"
        ] = self.text