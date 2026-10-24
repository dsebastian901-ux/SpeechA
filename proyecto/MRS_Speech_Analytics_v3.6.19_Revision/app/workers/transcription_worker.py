
"""
MRS Speech Analytics Professional
Worker de transcripción en segundo plano
"""

from __future__ import annotations

import logging
import threading
import traceback

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from app.services.whisper_service import (
    WhisperService,
    WhisperServiceError,
    whisper_service,
)


LOGGER = logging.getLogger(__name__)

ProgressCallback = Callable[[Dict[str, Any]], None]
FinishedCallback = Callable[[Dict[str, Any]], None]
ErrorCallback = Callable[[Dict[str, Any]], None]


@dataclass
class TranscriptionSummary:
    total: int
    processed: int = 0
    successful: int = 0
    failed: int = 0
    cancelled: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "processed": self.processed,
            "successful": self.successful,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "results": list(self.results),
            "errors": list(self.errors),
            "first_error": (
                self.errors[0].get("error", "")
                if self.errors
                else ""
            ),
        }


class TranscriptionWorker:
    """Procesa audios secuencialmente sin bloquear Tkinter."""

    def __init__(self, service: Optional[WhisperService] = None) -> None:
        self._service = service or whisper_service
        self._thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._lock = threading.RLock()
        self._running = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def is_paused(self) -> bool:
        return self.is_running and not self._pause_event.is_set()

    def start(
        self,
        audio_paths: Iterable[str | Path],
        *,
        output_directory: Optional[str | Path] = None,
        language: Optional[str] = None,
        vad_filter: bool = True,
        word_timestamps: bool = False,
        on_progress: Optional[ProgressCallback] = None,
        on_finished: Optional[FinishedCallback] = None,
        on_error: Optional[ErrorCallback] = None,
    ) -> None:
        paths = [
            Path(path).expanduser().resolve()
            for path in audio_paths
        ]

        if not paths:
            raise ValueError("No se recibieron archivos de audio.")

        with self._lock:
            if self._running:
                raise RuntimeError(
                    "Ya existe una transcripción en ejecución."
                )

            self._running = True
            self._cancel_event.clear()
            self._pause_event.set()

        self._thread = threading.Thread(
            target=self._run,
            kwargs={
                "audio_paths": paths,
                "output_directory": output_directory,
                "language": language,
                "vad_filter": vad_filter,
                "word_timestamps": word_timestamps,
                "on_progress": on_progress,
                "on_finished": on_finished,
                "on_error": on_error,
            },
            name="MRS-TranscriptionWorker",
            daemon=True,
        )
        self._thread.start()

    def pause(self) -> None:
        if self.is_running:
            self._pause_event.clear()

    def resume(self) -> None:
        if self.is_running:
            self._pause_event.set()

    def cancel(self) -> None:
        if self.is_running:
            self._cancel_event.set()
            self._pause_event.set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        thread = self._thread
        if thread is None:
            return True

        thread.join(timeout=timeout)
        return not thread.is_alive()

    def _run(
        self,
        *,
        audio_paths: List[Path],
        output_directory: Optional[str | Path],
        language: Optional[str],
        vad_filter: bool,
        word_timestamps: bool,
        on_progress: Optional[ProgressCallback],
        on_finished: Optional[FinishedCallback],
        on_error: Optional[ErrorCallback],
    ) -> None:
        summary = TranscriptionSummary(total=len(audio_paths))

        try:
            self._emit(
                on_progress,
                {
                    "status": "started",
                    "message": (
                        f"Se procesarán {len(audio_paths)} audio(s)."
                    ),
                    "total": len(audio_paths),
                    "processed": 0,
                    "progress": 0.0,
                },
            )

            if not self._service.is_model_loaded:
                self._emit(
                    on_progress,
                    {
                        "status": "model_loading",
                        "message": "Cargando el modelo Whisper...",
                        "total": len(audio_paths),
                        "processed": 0,
                        "progress": 0.0,
                    },
                )
                self._service.load_model()

            for index, audio_path in enumerate(
                audio_paths,
                start=1,
            ):
                if self._cancel_event.is_set():
                    summary.cancelled = max(
                        len(audio_paths) - summary.processed,
                        0,
                    )
                    break

                self._pause_event.wait()

                if self._cancel_event.is_set():
                    summary.cancelled = max(
                        len(audio_paths) - summary.processed,
                        0,
                    )
                    break

                self._emit(
                    on_progress,
                    {
                        "status": "processing",
                        "message": f"Transcribiendo: {audio_path.name}",
                        "file": str(audio_path),
                        "file_name": audio_path.name,
                        "index": index,
                        "total": len(audio_paths),
                        "processed": summary.processed,
                        "successful": summary.successful,
                        "failed": summary.failed,
                        "cancelled": summary.cancelled,
                        "progress": self._progress(
                            summary.processed,
                            len(audio_paths),
                        ),
                    },
                )

                try:
                    result = self._service.transcribe_audio(
                        audio_path=audio_path,
                        output_directory=output_directory,
                        language=language,
                        vad_filter=vad_filter,
                        word_timestamps=word_timestamps,
                    )

                    summary.successful += 1
                    summary.results.append(result)

                    file_event = {
                        "status": "completed",
                        "message": (
                            f"Transcripción terminada: "
                            f"{audio_path.name}"
                        ),
                        "file": str(audio_path),
                        "file_name": audio_path.name,
                        "result": result,
                    }

                except Exception as error:
                    summary.failed += 1

                    traceback_text = traceback.format_exc()
                    LOGGER.error(
                        "Error al transcribir %s\n%s",
                        audio_path,
                        traceback_text,
                    )
                    print(traceback_text, flush=True)

                    error_text = str(error) or repr(error)
                    error_data = {
                        "file": str(audio_path),
                        "file_name": audio_path.name,
                        "error": error_text,
                        "traceback": traceback_text,
                    }
                    summary.errors.append(error_data)

                    file_event = {
                        "status": "error",
                        "message": (
                            f"Error en {audio_path.name}: "
                            f"{error_text}"
                        ),
                        **error_data,
                    }
                    self._emit(on_error, file_event)

                finally:
                    summary.processed += 1

                file_event.update(
                    {
                        "index": index,
                        "total": len(audio_paths),
                        "processed": summary.processed,
                        "successful": summary.successful,
                        "failed": summary.failed,
                        "cancelled": summary.cancelled,
                        "progress": self._progress(
                            summary.processed,
                            len(audio_paths),
                        ),
                    }
                )
                self._emit(on_progress, file_event)

            final_data = summary.as_dict()
            final_data.update(
                {
                    "status": (
                        "cancelled"
                        if summary.cancelled
                        else "finished"
                    ),
                    "message": (
                        "Procesamiento finalizado. "
                        f"Correctos: {summary.successful}. "
                        f"Errores: {summary.failed}. "
                        f"Cancelados: {summary.cancelled}."
                    ),
                    "progress": self._progress(
                        summary.processed,
                        len(audio_paths),
                    ),
                }
            )
            self._emit(on_finished, final_data)

        except Exception as error:
            traceback_text = traceback.format_exc()
            LOGGER.error(
                "Error fatal del worker\n%s",
                traceback_text,
            )
            print(traceback_text, flush=True)

            fatal_data = {
                "status": "fatal_error",
                "message": (
                    "No fue posible iniciar la transcripción: "
                    f"{error}"
                ),
                "error": str(error),
                "traceback": traceback_text,
                **summary.as_dict(),
            }
            self._emit(on_error, fatal_data)
            self._emit(on_finished, fatal_data)

        finally:
            with self._lock:
                self._running = False
            self._pause_event.set()

    @staticmethod
    def _progress(processed: int, total: int) -> float:
        if total <= 0:
            return 0.0

        return round(
            min(max(processed / total, 0.0), 1.0),
            4,
        )

    @staticmethod
    def _emit(
        callback: Optional[Callable[[Dict[str, Any]], None]],
        data: Dict[str, Any],
    ) -> None:
        if callback is None:
            return

        try:
            callback(dict(data))
        except Exception:
            LOGGER.exception(
                "Error en callback del worker."
            )
