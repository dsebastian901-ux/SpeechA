
"""
MRS Speech Analytics Professional
Servicio de transcripción con Faster-Whisper
"""

from __future__ import annotations

import json
import logging
import threading
import traceback

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import (
    TRANSCRIPTIONS_DIR,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_LANGUAGE,
    WHISPER_MODEL,
)


LOGGER = logging.getLogger(__name__)


class WhisperServiceError(Exception):
    """Error controlado del servicio de transcripción."""


class WhisperService:
    """Carga una sola vez el modelo y transcribe audios."""

    def __init__(self) -> None:
        self._model = None
        self._model_lock = threading.RLock()
        self._transcription_lock = threading.RLock()

    @property
    def is_model_loaded(self) -> bool:
        return self._model is not None

    def load_model(self) -> None:
        if self._model is not None:
            return

        with self._model_lock:
            if self._model is not None:
                return

            try:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    WHISPER_MODEL,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE_TYPE,
                )

            except Exception as error:
                raise WhisperServiceError(
                    "No fue posible cargar Whisper.\n\n"
                    f"Modelo: {WHISPER_MODEL}\n"
                    f"Dispositivo: {WHISPER_DEVICE}\n"
                    f"Tipo de cálculo: {WHISPER_COMPUTE_TYPE}\n\n"
                    f"Detalle: {error}"
                ) from error

    def transcribe_audio(
        self,
        audio_path: str | Path,
        output_directory: Optional[str | Path] = None,
        language: Optional[str] = None,
        beam_size: int = 1,
        vad_filter: bool = False,
        word_timestamps: bool = False,
    ) -> Dict[str, Any]:
        path = Path(audio_path).expanduser().resolve()
        self._validate_audio(path)

        destination = (
            Path(output_directory).expanduser().resolve()
            if output_directory
            else Path(TRANSCRIPTIONS_DIR).resolve()
        )
        destination.mkdir(parents=True, exist_ok=True)

        selected_language = language or WHISPER_LANGUAGE
        self.load_model()

        try:
            segments, information = self._run_transcription(
                path=path,
                language=selected_language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps,
            )

        except Exception as first_error:
            # Algunos WAV telefónicos fallan al usar VAD.
            if vad_filter:
                LOGGER.warning(
                    "Reintentando sin VAD: %s",
                    path.name,
                )
                try:
                    segments, information = self._run_transcription(
                        path=path,
                        language=selected_language,
                        beam_size=1,
                        vad_filter=False,
                        word_timestamps=word_timestamps,
                    )
                except Exception as retry_error:
                    raise WhisperServiceError(
                        "No fue posible transcribir el audio:\n"
                        f"{path.name}\n\n"
                        f"Primer intento: {first_error}\n"
                        f"Segundo intento sin VAD: {retry_error}"
                    ) from retry_error
            else:
                raise WhisperServiceError(
                    "No fue posible transcribir el audio:\n"
                    f"{path.name}\n\n"
                    f"Detalle: {first_error}"
                ) from first_error

        normalized_segments = self._consume_segments(
            segments,
            include_words=word_timestamps,
        )

        complete_text = self._join_text(
            normalized_segments
        )

        duration = float(
            getattr(information, "duration", 0.0)
            or 0.0
        )

        data = {
            "archivo": path.name,
            "ruta_audio": str(path),
            "modelo": WHISPER_MODEL,
            "dispositivo": WHISPER_DEVICE,
            "tipo_calculo": WHISPER_COMPUTE_TYPE,
            "idioma_solicitado": selected_language,
            "idioma_detectado": getattr(
                information,
                "language",
                selected_language,
            ),
            "probabilidad_idioma": float(
                getattr(
                    information,
                    "language_probability",
                    0.0,
                )
                or 0.0
            ),
            "duracion_segundos": duration,
            "duracion_legible": self._format_duration(
                duration
            ),
            "texto": complete_text,
            "segmentos": normalized_segments,
            "fecha_transcripcion": datetime.now().isoformat(
                timespec="seconds"
            ),
        }

        data.update(
            self._save_outputs(
                audio_path=path,
                output_directory=destination,
                data=data,
            )
        )

        return data

    def _run_transcription(
        self,
        *,
        path: Path,
        language: str,
        beam_size: int,
        vad_filter: bool,
        word_timestamps: bool,
    ):
        with self._transcription_lock:
            segment_generator, information = self._model.transcribe(
                str(path),
                language=language,
                task="transcribe",
                beam_size=beam_size,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps,
                condition_on_previous_text=True,
            )

            # La transcripción real ocurre al consumir el generador.
            segments = list(segment_generator)

        return segments, information

    @staticmethod
    def _validate_audio(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(
                f"No existe el archivo:\n{path}"
            )

        if not path.is_file():
            raise WhisperServiceError(
                f"La ruta no es un archivo:\n{path}"
            )

        if path.stat().st_size <= 0:
            raise WhisperServiceError(
                f"El archivo está vacío:\n{path.name}"
            )

    @staticmethod
    def _consume_segments(
        segments,
        include_words: bool,
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []

        for index, segment in enumerate(segments):
            item = {
                "id": int(
                    getattr(segment, "id", index)
                ),
                "inicio": round(
                    float(getattr(segment, "start", 0.0)),
                    3,
                ),
                "fin": round(
                    float(getattr(segment, "end", 0.0)),
                    3,
                ),
                "texto": str(
                    getattr(segment, "text", "")
                    or ""
                ).strip(),
            }

            if include_words:
                words = []
                for word in (
                    getattr(segment, "words", None)
                    or []
                ):
                    words.append(
                        {
                            "palabra": str(
                                getattr(word, "word", "")
                                or ""
                            ),
                            "inicio": round(
                                float(
                                    getattr(
                                        word,
                                        "start",
                                        0.0,
                                    )
                                    or 0.0
                                ),
                                3,
                            ),
                            "fin": round(
                                float(
                                    getattr(
                                        word,
                                        "end",
                                        0.0,
                                    )
                                    or 0.0
                                ),
                                3,
                            ),
                            "probabilidad": round(
                                float(
                                    getattr(
                                        word,
                                        "probability",
                                        0.0,
                                    )
                                    or 0.0
                                ),
                                4,
                            ),
                        }
                    )
                item["palabras"] = words

            result.append(item)

        return result

    @staticmethod
    def _join_text(
        segments: List[Dict[str, Any]],
    ) -> str:
        return " ".join(
            segment.get("texto", "").strip()
            for segment in segments
            if segment.get("texto", "").strip()
        ).strip()

    @staticmethod
    def _save_outputs(
        *,
        audio_path: Path,
        output_directory: Path,
        data: Dict[str, Any],
    ) -> Dict[str, str]:
        txt_path = output_directory / (
            f"{audio_path.stem}.txt"
        )
        json_path = output_directory / (
            f"{audio_path.stem}.json"
        )

        txt_path.write_text(
            data.get("texto", ""),
            encoding="utf-8",
        )

        with json_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )

        return {
            "ruta_txt": str(txt_path),
            "ruta_json": str(json_path),
        }

    @staticmethod
    def _format_duration(
        seconds: float,
    ) -> str:
        total = max(int(round(seconds)), 0)
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


whisper_service = WhisperService()
