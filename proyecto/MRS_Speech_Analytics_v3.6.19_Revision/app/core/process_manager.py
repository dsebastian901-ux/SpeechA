"""
============================================================
MRS Speech Analytics Professional
Núcleo: Administrador de procesos en segundo plano
============================================================

Este módulo administra tareas largas sin bloquear la interfaz.

Funciones disponibles:
- Ejecutar una tarea en segundo plano.
- Reportar progreso.
- Pausar y reanudar.
- Solicitar cancelación.
- Enviar eventos a la interfaz principal.
- Capturar errores.
============================================================
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional


class ProcessStatus(str, Enum):
    """Estados posibles de un proceso."""

    PENDING = "Pendiente"
    RUNNING = "Procesando"
    PAUSED = "Pausado"
    COMPLETED = "Completado"
    CANCELLED = "Cancelado"
    ERROR = "Error"


@dataclass
class ProcessEvent:
    """Evento enviado por el administrador a la interfaz."""

    event_type: str
    process_id: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessInformation:
    """Información general de un proceso."""

    process_id: str
    name: str
    status: ProcessStatus = ProcessStatus.PENDING
    progress: float = 0.0
    current_item: int = 0
    total_items: int = 0
    message: str = ""
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


class ProcessContext:
    """
    Contexto entregado a la tarea que se ejecuta.

    La tarea puede utilizar este objeto para:

    - Reportar progreso.
    - Comprobar si debe cancelarse.
    - Esperar cuando el proceso está pausado.
    - Enviar mensajes a la interfaz.
    """

    def __init__(
        self,
        process_id: str,
        manager: "ProcessManager",
        cancel_event: threading.Event,
        pause_event: threading.Event,
    ):
        self.process_id = process_id
        self._manager = manager
        self._cancel_event = cancel_event
        self._pause_event = pause_event

    def is_cancelled(self) -> bool:
        """Indica si se solicitó cancelar el proceso."""

        return self._cancel_event.is_set()

    def wait_if_paused(self) -> None:
        """
        Detiene temporalmente el trabajo mientras el proceso esté pausado.

        La tarea debe llamar periódicamente este método.
        """

        while not self._pause_event.is_set():
            if self.is_cancelled():
                return

            time.sleep(0.1)

    def check_cancelled(self) -> None:
        """
        Genera una excepción interna cuando el proceso fue cancelado.
        """

        if self.is_cancelled():
            raise ProcessCancelledError(
                "El proceso fue cancelado por el usuario."
            )

    def report_progress(
        self,
        current: int,
        total: int,
        message: str = "",
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Reporta el avance de la tarea.

        Args:
            current:
                Elemento actual.

            total:
                Total de elementos.

            message:
                Mensaje que se mostrará en la interfaz.

            extra_data:
                Información adicional del proceso.
        """

        if total <= 0:
            progress = 0.0
        else:
            progress = min(
                max((current / total) * 100, 0.0),
                100.0,
            )

        self._manager._update_progress(
            process_id=self.process_id,
            current=current,
            total=total,
            progress=progress,
            message=message,
            extra_data=extra_data,
        )

    def send_message(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Envía un mensaje informativo a la interfaz."""

        self._manager._publish_event(
            ProcessEvent(
                event_type="message",
                process_id=self.process_id,
                data={
                    "message": message,
                    "extra_data": extra_data or {},
                },
            )
        )


class ProcessCancelledError(Exception):
    """Excepción interna utilizada para cancelar procesos."""


class ProcessManager:
    """
    Administrador central de procesos en segundo plano.

    Una tarea debe ser una función que reciba ProcessContext como
    primer parámetro.

    Ejemplo:

        def tarea(context, audios):
            total = len(audios)

            for indice, audio in enumerate(audios, start=1):
                context.wait_if_paused()
                context.check_cancelled()

                procesar(audio)

                context.report_progress(
                    current=indice,
                    total=total,
                    message=audio
                )

            return {"procesados": total}
    """

    def __init__(self):
        self._processes: Dict[str, ProcessInformation] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._cancel_events: Dict[str, threading.Event] = {}
        self._pause_events: Dict[str, threading.Event] = {}

        self._event_queue: queue.Queue[ProcessEvent] = queue.Queue()
        self._lock = threading.RLock()

    def start_process(
        self,
        name: str,
        target: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """
        Inicia una tarea en segundo plano.

        Args:
            name:
                Nombre visible del proceso.

            target:
                Función que realizará el trabajo.

            *args y **kwargs:
                Argumentos adicionales para la función.

        Returns:
            str:
                Identificador único del proceso.
        """

        if not callable(target):
            raise TypeError(
                "La tarea proporcionada no es ejecutable."
            )

        process_id = str(uuid.uuid4())

        cancel_event = threading.Event()
        pause_event = threading.Event()

        # Activado significa que el proceso puede avanzar.
        pause_event.set()

        process_information = ProcessInformation(
            process_id=process_id,
            name=name,
            status=ProcessStatus.PENDING,
            message="Proceso preparado.",
        )

        worker_thread = threading.Thread(
            target=self._run_process,
            args=(
                process_id,
                target,
                args,
                kwargs,
            ),
            name=f"MRS-Process-{process_id[:8]}",
            daemon=True,
        )

        with self._lock:
            self._processes[process_id] = process_information
            self._threads[process_id] = worker_thread
            self._cancel_events[process_id] = cancel_event
            self._pause_events[process_id] = pause_event

        self._publish_event(
            ProcessEvent(
                event_type="created",
                process_id=process_id,
                data=self._process_to_dictionary(
                    process_information
                ),
            )
        )

        worker_thread.start()

        return process_id

    def _run_process(
        self,
        process_id: str,
        target: Callable[..., Any],
        args: tuple,
        kwargs: Dict[str, Any],
    ) -> None:
        """Ejecuta internamente una tarea."""

        cancel_event = self._cancel_events[process_id]
        pause_event = self._pause_events[process_id]

        context = ProcessContext(
            process_id=process_id,
            manager=self,
            cancel_event=cancel_event,
            pause_event=pause_event,
        )

        self._set_process_status(
            process_id=process_id,
            status=ProcessStatus.RUNNING,
            message="Proceso iniciado.",
            started_at=time.time(),
        )

        try:
            result = target(
                context,
                *args,
                **kwargs,
            )

            if cancel_event.is_set():
                self._set_process_status(
                    process_id=process_id,
                    status=ProcessStatus.CANCELLED,
                    message="Proceso cancelado.",
                    finished_at=time.time(),
                )
                return

            with self._lock:
                process = self._processes[process_id]
                process.result = result
                process.progress = 100.0

            self._set_process_status(
                process_id=process_id,
                status=ProcessStatus.COMPLETED,
                message="Proceso completado correctamente.",
                finished_at=time.time(),
            )

        except ProcessCancelledError:
            self._set_process_status(
                process_id=process_id,
                status=ProcessStatus.CANCELLED,
                message="Proceso cancelado.",
                finished_at=time.time(),
            )

        except Exception as error:
            error_message = str(error)
            error_trace = traceback.format_exc()

            with self._lock:
                process = self._processes[process_id]
                process.error = error_message

            self._set_process_status(
                process_id=process_id,
                status=ProcessStatus.ERROR,
                message=error_message,
                finished_at=time.time(),
                extra_data={
                    "traceback": error_trace,
                },
            )

    def pause_process(self, process_id: str) -> bool:
        """Pausa un proceso activo."""

        with self._lock:
            process = self._processes.get(process_id)

            if process is None:
                return False

            if process.status != ProcessStatus.RUNNING:
                return False

            self._pause_events[process_id].clear()
            process.status = ProcessStatus.PAUSED
            process.message = "Proceso pausado."

        self._publish_event(
            ProcessEvent(
                event_type="status",
                process_id=process_id,
                data=self.get_process(process_id) or {},
            )
        )

        return True

    def resume_process(self, process_id: str) -> bool:
        """Reanuda un proceso pausado."""

        with self._lock:
            process = self._processes.get(process_id)

            if process is None:
                return False

            if process.status != ProcessStatus.PAUSED:
                return False

            self._pause_events[process_id].set()
            process.status = ProcessStatus.RUNNING
            process.message = "Proceso reanudado."

        self._publish_event(
            ProcessEvent(
                event_type="status",
                process_id=process_id,
                data=self.get_process(process_id) or {},
            )
        )

        return True

    def cancel_process(self, process_id: str) -> bool:
        """
        Solicita cancelar un proceso.

        La cancelación es cooperativa. La tarea debe llamar
        periódicamente:

            context.check_cancelled()
        """

        with self._lock:
            process = self._processes.get(process_id)

            if process is None:
                return False

            if process.status in {
                ProcessStatus.COMPLETED,
                ProcessStatus.CANCELLED,
                ProcessStatus.ERROR,
            }:
                return False

            self._cancel_events[process_id].set()

            # Si estaba pausado, se libera para que pueda terminar.
            self._pause_events[process_id].set()

            process.message = "Cancelando proceso..."

        self._publish_event(
            ProcessEvent(
                event_type="cancelling",
                process_id=process_id,
                data=self.get_process(process_id) or {},
            )
        )

        return True

    def get_process(
        self,
        process_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Obtiene la información de un proceso."""

        with self._lock:
            process = self._processes.get(process_id)

            if process is None:
                return None

            return self._process_to_dictionary(process)

    def get_all_processes(self) -> list[Dict[str, Any]]:
        """Devuelve todos los procesos registrados."""

        with self._lock:
            return [
                self._process_to_dictionary(process)
                for process in self._processes.values()
            ]

    def is_running(self, process_id: str) -> bool:
        """Indica si un proceso sigue activo."""

        with self._lock:
            process = self._processes.get(process_id)

            if process is None:
                return False

            return process.status in {
                ProcessStatus.PENDING,
                ProcessStatus.RUNNING,
                ProcessStatus.PAUSED,
            }

    def has_active_processes(self) -> bool:
        """Indica si existe al menos un proceso activo."""

        with self._lock:
            return any(
                process.status in {
                    ProcessStatus.PENDING,
                    ProcessStatus.RUNNING,
                    ProcessStatus.PAUSED,
                }
                for process in self._processes.values()
            )

    def get_next_event(
        self,
    ) -> Optional[ProcessEvent]:
        """
        Obtiene el siguiente evento sin bloquear la aplicación.

        La interfaz debe consultar este método usando `after()`.
        """

        try:
            return self._event_queue.get_nowait()
        except queue.Empty:
            return None

    def clear_finished_processes(self) -> int:
        """Elimina del registro los procesos ya terminados."""

        finished_statuses = {
            ProcessStatus.COMPLETED,
            ProcessStatus.CANCELLED,
            ProcessStatus.ERROR,
        }

        removed = 0

        with self._lock:
            process_ids = [
                process_id
                for process_id, process in self._processes.items()
                if process.status in finished_statuses
            ]

            for process_id in process_ids:
                self._processes.pop(process_id, None)
                self._threads.pop(process_id, None)
                self._cancel_events.pop(process_id, None)
                self._pause_events.pop(process_id, None)
                removed += 1

        return removed

    def _update_progress(
        self,
        process_id: str,
        current: int,
        total: int,
        progress: float,
        message: str,
        extra_data: Optional[Dict[str, Any]],
    ) -> None:
        """Actualiza el progreso interno de un proceso."""

        with self._lock:
            process = self._processes.get(process_id)

            if process is None:
                return

            process.current_item = current
            process.total_items = total
            process.progress = progress

            if message:
                process.message = message

        self._publish_event(
            ProcessEvent(
                event_type="progress",
                process_id=process_id,
                data={
                    "current_item": current,
                    "total_items": total,
                    "progress": progress,
                    "message": message,
                    "extra_data": extra_data or {},
                },
            )
        )

    def _set_process_status(
        self,
        process_id: str,
        status: ProcessStatus,
        message: str = "",
        started_at: Optional[float] = None,
        finished_at: Optional[float] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Modifica el estado interno del proceso."""

        with self._lock:
            process = self._processes.get(process_id)

            if process is None:
                return

            process.status = status

            if message:
                process.message = message

            if started_at is not None:
                process.started_at = started_at

            if finished_at is not None:
                process.finished_at = finished_at

            process_data = self._process_to_dictionary(process)

        if extra_data:
            process_data["extra_data"] = extra_data

        self._publish_event(
            ProcessEvent(
                event_type="status",
                process_id=process_id,
                data=process_data,
            )
        )

    def _publish_event(
        self,
        event: ProcessEvent,
    ) -> None:
        """Coloca un evento en la cola de comunicación."""

        self._event_queue.put(event)

    @staticmethod
    def _process_to_dictionary(
        process: ProcessInformation,
    ) -> Dict[str, Any]:
        """Convierte la información del proceso en diccionario."""

        elapsed_seconds = None

        if process.started_at is not None:
            end_time = (
                process.finished_at
                if process.finished_at is not None
                else time.time()
            )

            elapsed_seconds = max(
                end_time - process.started_at,
                0.0,
            )

        return {
            "process_id": process.process_id,
            "name": process.name,
            "status": process.status.value,
            "progress": process.progress,
            "current_item": process.current_item,
            "total_items": process.total_items,
            "message": process.message,
            "result": process.result,
            "error": process.error,
            "started_at": process.started_at,
            "finished_at": process.finished_at,
            "elapsed_seconds": elapsed_seconds,
        }


# Instancia global que podrá utilizar toda la aplicación.
process_manager = ProcessManager()