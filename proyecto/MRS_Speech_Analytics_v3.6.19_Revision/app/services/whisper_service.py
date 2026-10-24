"""
============================================================
MRS Speech Analytics Professional
Servicio de transcripción con Faster-Whisper
============================================================
"""

from __future__ import annotations

import json
import logging
import threading
from time import perf_counter

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config.settings import TRANSCRIPTIONS_DIR
from app.services.settings_service import SettingsService


LOGGER = logging.getLogger(__name__)


class WhisperServiceError(Exception):
    """Error controlado del servicio de transcripción."""


class WhisperService:
    """
    Servicio de transcripción con Faster-Whisper.

    Características:
    - Lee la configuración editable desde SettingsService.
    - Carga el modelo una sola vez.
    - Recarga automáticamente el modelo si cambia:
        * modelo
        * dispositivo
        * compute type
    - Respeta configuración de:
        * idioma
        * beam size
        * VAD
        * word timestamps
    - Permite sobrescribir parámetros por llamada.
    """

    def __init__(self) -> None:
        self._model = None

        # Configuración utilizada por el modelo actualmente cargado.
        self._loaded_model_config: Optional[
            Tuple[str, str, str]
        ] = None

        self._model_lock = threading.RLock()
        self._transcription_lock = threading.RLock()

    # =========================================================
    # ESTADO DEL MODELO
    # =========================================================

    @property
    def is_model_loaded(self) -> bool:
        return self._model is not None

    # =========================================================
    # CONFIGURACIÓN DE EJECUCIÓN
    # =========================================================

    @staticmethod
    def get_runtime_configuration() -> Dict[str, Any]:
        """
        Devuelve la configuración que Whisper utilizará
        en este momento.
        """

        configuration = SettingsService.load()

        return {
            "model": str(
                configuration.get(
                    "whisper_model",
                    "small",
                )
            ),

            "language": str(
                configuration.get(
                    "whisper_language",
                    "es",
                )
            ),

            "device": str(
                configuration.get(
                    "whisper_device",
                    "cpu",
                )
            ),

            "compute_type": str(
                configuration.get(
                    "whisper_compute_type",
                    "int8",
                )
            ),

            "beam_size": WhisperService._safe_int(
                configuration.get(
                    "whisper_beam_size",
                    5,
                ),
                default=5,
                minimum=1,
                maximum=20,
            ),

            "vad_filter": WhisperService._safe_bool(
                configuration.get(
                    "whisper_vad_filter",
                    True,
                )
            ),

            "word_timestamps": WhisperService._safe_bool(
                configuration.get(
                    "whisper_word_timestamps",
                    False,
                )
            ),
        }

    # =========================================================
    # CARGAR MODELO
    # =========================================================

    def load_model(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ) -> None:
        """
        Carga Faster-Whisper.

        Si el modelo ya está cargado con la misma configuración,
        se reutiliza.

        Si cambió modelo, dispositivo o compute type,
        se vuelve a cargar automáticamente.
        """

        runtime = self.get_runtime_configuration()

        selected_model = str(
            model_name
            or runtime["model"]
        )

        selected_device = str(
            device
            or runtime["device"]
        )

        selected_compute_type = str(
            compute_type
            or runtime["compute_type"]
        )

        requested_config = (
            selected_model,
            selected_device,
            selected_compute_type,
        )

        # -----------------------------------------------------
        # YA CARGADO CON LA MISMA CONFIGURACIÓN
        # -----------------------------------------------------

        if (
            self._model is not None
            and self._loaded_model_config
            == requested_config
        ):
            return

        # -----------------------------------------------------
        # CARGA / RECARGA
        # -----------------------------------------------------

        with self._model_lock:

            if (
                self._model is not None
                and self._loaded_model_config
                == requested_config
            ):
                return

            try:
                from faster_whisper import WhisperModel

                LOGGER.info(
                    (
                        "Cargando Faster-Whisper: "
                        "modelo=%s device=%s compute_type=%s"
                    ),
                    selected_model,
                    selected_device,
                    selected_compute_type,
                )

                new_model = WhisperModel(
                    selected_model,
                    device=selected_device,
                    compute_type=selected_compute_type,
                )

                self._model = new_model

                self._loaded_model_config = (
                    requested_config
                )

            except Exception as error:

                raise WhisperServiceError(
                    "No fue posible cargar Whisper.\n\n"
                    f"Modelo: {selected_model}\n"
                    f"Dispositivo: {selected_device}\n"
                    f"Tipo de cálculo: "
                    f"{selected_compute_type}\n\n"
                    f"Detalle: {error}"
                ) from error

    # =========================================================
    # DESCARGAR MODELO
    # =========================================================

    def unload_model(self) -> None:
        """
        Libera la referencia al modelo cargado.

        En la siguiente transcripción se volverá a cargar
        utilizando la configuración vigente.
        """

        with self._model_lock:
            self._model = None
            self._loaded_model_config = None

    # =========================================================
    # TRANSCRIBIR AUDIO
    # =========================================================

    def transcribe_audio(
        self,
        audio_path: str | Path,
        output_directory: Optional[str | Path] = None,
        language: Optional[str] = None,
        beam_size: Optional[int] = None,
        vad_filter: Optional[bool] = None,
        word_timestamps: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe un archivo de audio.

        Los parámetros recibidos explícitamente tienen prioridad.

        Si se omiten, se toman desde SettingsService.
        """

        # -----------------------------------------------------
        # CONFIGURACIÓN
        # -----------------------------------------------------

        runtime = self.get_runtime_configuration()

        selected_model = runtime[
            "model"
        ]

        selected_device = runtime[
            "device"
        ]

        selected_compute_type = runtime[
            "compute_type"
        ]

        configured_language = str(
            runtime[
                "language"
            ]
            or "es"
        )

        # -----------------------------------------------------
        # IDIOMA
        # -----------------------------------------------------

        requested_language = (
            str(language).strip()
            if language is not None
            else configured_language.strip()
        )

        # Faster-Whisper usa language=None para autodetección.
        if requested_language.lower() == "auto":
            selected_language = None
        else:
            selected_language = (
                requested_language
            )

        # -----------------------------------------------------
        # BEAM SIZE
        # -----------------------------------------------------

        selected_beam_size = self._safe_int(
            beam_size
            if beam_size is not None
            else runtime[
                "beam_size"
            ],
            default=runtime[
                "beam_size"
            ],
            minimum=1,
            maximum=20,
        )

        # -----------------------------------------------------
        # VAD
        # -----------------------------------------------------

        selected_vad_filter = (
            self._safe_bool(
                vad_filter
            )
            if vad_filter is not None
            else self._safe_bool(
                runtime[
                    "vad_filter"
                ]
            )
        )

        # -----------------------------------------------------
        # WORD TIMESTAMPS
        # -----------------------------------------------------

        selected_word_timestamps = (
            self._safe_bool(
                word_timestamps
            )
            if word_timestamps is not None
            else self._safe_bool(
                runtime[
                    "word_timestamps"
                ]
            )
        )

        # -----------------------------------------------------
        # AUDIO
        # -----------------------------------------------------

        path = (
            Path(audio_path)
            .expanduser()
            .resolve()
        )

        self._validate_audio(
            path
        )

        # -----------------------------------------------------
        # DIRECTORIO DESTINO
        # -----------------------------------------------------

        destination = (
            Path(
                output_directory
            )
            .expanduser()
            .resolve()

            if output_directory

            else Path(
                TRANSCRIPTIONS_DIR
            ).resolve()
        )

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        # -----------------------------------------------------
        # CARGAR MODELO
        # -----------------------------------------------------

        self.load_model(
            model_name=selected_model,
            device=selected_device,
            compute_type=selected_compute_type,
        )

        # -----------------------------------------------------
        # TRANSCRIPCIÓN
        # -----------------------------------------------------

        # Cronómetro interno de Whisper. Mide la inferencia real
        # (incluye un posible reintento sin VAD si fuera necesario).
        transcription_started = perf_counter()
        effective_vad_filter = selected_vad_filter

        try:
            segments, information = (
                self._run_transcription(
                    path=path,
                    language=selected_language,
                    beam_size=selected_beam_size,
                    vad_filter=selected_vad_filter,
                    word_timestamps=(
                        selected_word_timestamps
                    ),
                )
            )

        except Exception as first_error:

            # -------------------------------------------------
            # FALLBACK SIN VAD
            # -------------------------------------------------

            if selected_vad_filter:

                LOGGER.warning(
                    "Reintentando sin VAD: %s",
                    path.name,
                )

                try:
                    segments, information = (
                        self._run_transcription(
                            path=path,
                            language=selected_language,
                            beam_size=(
                                selected_beam_size
                            ),
                            vad_filter=False,
                            word_timestamps=(
                                selected_word_timestamps
                            ),
                        )
                    )
                    effective_vad_filter = False

                except Exception as retry_error:

                    raise WhisperServiceError(
                        "No fue posible transcribir "
                        "el audio:\n"
                        f"{path.name}\n\n"
                        f"Primer intento: "
                        f"{first_error}\n"
                        f"Segundo intento sin VAD: "
                        f"{retry_error}"
                    ) from retry_error

            else:

                raise WhisperServiceError(
                    "No fue posible transcribir "
                    "el audio:\n"
                    f"{path.name}\n\n"
                    f"Detalle: {first_error}"
                ) from first_error

        transcription_seconds = max(
            0.0,
            perf_counter() - transcription_started,
        )

        # -----------------------------------------------------
        # SEGMENTOS
        # -----------------------------------------------------

        normalized_segments = (
            self._consume_segments(
                segments,
                include_words=(
                    selected_word_timestamps
                ),
            )
        )

        complete_text = self._join_text(
            normalized_segments
        )

        # -----------------------------------------------------
        # DURACIÓN
        # -----------------------------------------------------

        duration = float(
            getattr(
                information,
                "duration",
                0.0,
            )
            or 0.0
        )

        # -----------------------------------------------------
        # IDIOMA DETECTADO
        # -----------------------------------------------------

        detected_language = getattr(
            information,
            "language",
            selected_language
            or "",
        )

        # -----------------------------------------------------
        # RESULTADO
        # -----------------------------------------------------

        data = {
            "archivo": path.name,

            "ruta_audio": str(
                path
            ),

            "modelo": selected_model,

            "dispositivo": selected_device,

            "tipo_calculo": (
                selected_compute_type
            ),

            "idioma_solicitado": (
                requested_language
            ),

            "idioma_detectado": (
                detected_language
            ),

            "probabilidad_idioma": float(
                getattr(
                    information,
                    "language_probability",
                    0.0,
                )
                or 0.0
            ),

            "beam_size": (
                selected_beam_size
            ),

            "vad_filter": (
                selected_vad_filter
            ),

            "word_timestamps": (
                selected_word_timestamps
            ),

            "duracion_segundos": (
                duration
            ),

            "duracion_legible": (
                self._format_duration(
                    duration
                )
            ),

            # Métricas de rendimiento para diagnóstico.
            "tiempo_whisper_segundos": round(
                transcription_seconds,
                3,
            ),

            "tiempo_whisper_legible": (
                self._format_duration(
                    transcription_seconds
                )
            ),

            # factor_tiempo_real < 1.0 significa que Whisper
            # transcribió más rápido que la duración del audio.
            "factor_tiempo_real": round(
                (transcription_seconds / duration)
                if duration > 0
                else 0.0,
                4,
            ),

            # Ejemplo: 2.50x = procesa 2.5 segundos de audio
            # por cada segundo de reloj.
            "velocidad_tiempo_real_x": round(
                (duration / transcription_seconds)
                if transcription_seconds > 0
                else 0.0,
                3,
            ),

            "vad_efectivo": (
                effective_vad_filter
            ),

            "texto": (
                complete_text
            ),

            "segmentos": (
                normalized_segments
            ),

            "fecha_transcripcion": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ),
        }

        # -----------------------------------------------------
        # GUARDAR TXT + JSON
        # -----------------------------------------------------

        data.update(
            self._save_outputs(
                audio_path=path,
                output_directory=destination,
                data=data,
            )
        )

        return data

    # =========================================================
    # EJECUTAR FASTER-WHISPER
    # =========================================================

    def _run_transcription(
        self,
        *,
        path: Path,
        language: Optional[str],
        beam_size: int,
        vad_filter: bool,
        word_timestamps: bool,
    ):
        if self._model is None:
            raise WhisperServiceError(
                "El modelo Whisper no está cargado."
            )

        with self._transcription_lock:

            segment_generator, information = (
                self._model.transcribe(
                    str(path),
                    language=language,
                    task="transcribe",
                    beam_size=beam_size,
                    vad_filter=vad_filter,
                    # Silero VAD es conservador por defecto. En llamadas
                    # telefónicas hay pausas frecuentes; 700 ms reduce
                    # trabajo innecesario sin usar un corte agresivo.
                    vad_parameters=(
                        {
                            "min_silence_duration_ms": 700,
                            "speech_pad_ms": 200,
                        }
                        if vad_filter
                        else None
                    ),
                    word_timestamps=(
                        word_timestamps
                    ),
                    condition_on_previous_text=False,
                )
            )

            # La transcripción real ocurre al consumir
            # el generador.
            segments = list(
                segment_generator
            )

        return (
            segments,
            information,
        )

    # =========================================================
    # VALIDAR AUDIO
    # =========================================================

    @staticmethod
    def _validate_audio(
        path: Path,
    ) -> None:

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

    # =========================================================
    # CONSUMIR SEGMENTOS
    # =========================================================

    @staticmethod
    def _consume_segments(
        segments,
        include_words: bool,
    ) -> List[Dict[str, Any]]:

        result: List[
            Dict[str, Any]
        ] = []

        for index, segment in enumerate(
            segments
        ):

            item = {
                "id": int(
                    getattr(
                        segment,
                        "id",
                        index,
                    )
                ),

                "inicio": round(
                    float(
                        getattr(
                            segment,
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
                            segment,
                            "end",
                            0.0,
                        )
                        or 0.0
                    ),
                    3,
                ),

                "texto": str(
                    getattr(
                        segment,
                        "text",
                        "",
                    )
                    or ""
                ).strip(),
            }

            # -------------------------------------------------
            # PALABRAS
            # -------------------------------------------------

            if include_words:

                words = []

                for word in (
                    getattr(
                        segment,
                        "words",
                        None,
                    )
                    or []
                ):

                    words.append(
                        {
                            "palabra": str(
                                getattr(
                                    word,
                                    "word",
                                    "",
                                )
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

                item[
                    "palabras"
                ] = words

            result.append(
                item
            )

        return result

    # =========================================================
    # UNIR TEXTO
    # =========================================================

    @staticmethod
    def _join_text(
        segments: List[
            Dict[str, Any]
        ],
    ) -> str:

        return " ".join(
            segment.get(
                "texto",
                "",
            ).strip()

            for segment in segments

            if segment.get(
                "texto",
                "",
            ).strip()
        ).strip()

    # =========================================================
    # GUARDAR RESULTADOS
    # =========================================================

    @staticmethod
    def _save_outputs(
        *,
        audio_path: Path,
        output_directory: Path,
        data: Dict[str, Any],
    ) -> Dict[str, str]:

        txt_path = (
            output_directory
            / f"{audio_path.stem}.txt"
        )

        json_path = (
            output_directory
            / f"{audio_path.stem}.json"
        )

        # -----------------------------------------------------
        # TXT
        # -----------------------------------------------------

        txt_path.write_text(
            data.get(
                "texto",
                "",
            ),
            encoding="utf-8",
        )

        # -----------------------------------------------------
        # JSON
        # -----------------------------------------------------

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
            "ruta_txt": str(
                txt_path
            ),

            "ruta_json": str(
                json_path
            ),
        }

    # =========================================================
    # DURACIÓN
    # =========================================================

    @staticmethod
    def _format_duration(
        seconds: float,
    ) -> str:

        total = max(
            int(
                round(
                    seconds
                )
            ),
            0,
        )

        hours, remainder = divmod(
            total,
            3600,
        )

        minutes, seconds = divmod(
            remainder,
            60,
        )

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    # =========================================================
    # BOOLEANO SEGURO
    # =========================================================

    @staticmethod
    def _safe_bool(
        value,
    ) -> bool:

        if isinstance(
            value,
            bool,
        ):
            return value

        if isinstance(
            value,
            str,
        ):

            normalized = (
                value
                .strip()
                .lower()
            )

            if normalized in {
                "true",
                "1",
                "yes",
                "si",
                "sí",
                "on",
            }:
                return True

            if normalized in {
                "false",
                "0",
                "no",
                "off",
            }:
                return False

        return bool(
            value
        )

    # =========================================================
    # ENTERO SEGURO
    # =========================================================

    @staticmethod
    def _safe_int(
        value,
        default=1,
        minimum=None,
        maximum=None,
    ) -> int:

        try:
            number = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            number = int(
                default
            )

        if (
            minimum is not None
            and number < minimum
        ):
            number = minimum

        if (
            maximum is not None
            and number > maximum
        ):
            number = maximum

        return number


# =============================================================
# INSTANCIA GLOBAL
# =============================================================

whisper_service = WhisperService()