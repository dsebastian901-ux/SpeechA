"""Workers de procesamiento en segundo plano."""

from app.workers.transcription_worker import TranscriptionWorker

__all__ = ["TranscriptionWorker"]
