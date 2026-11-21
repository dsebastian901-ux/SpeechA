"""Compatibilidad de importación histórica; usa el motor local vigente.

El respaldo antiguo descargaba un modelo por nombre. No mantener otra
implementación: todas las rutas delegan en el servicio canónico sin internet.
"""
from app.services.whisper_service import WhisperService, WhisperServiceError

__all__ = ['WhisperService', 'WhisperServiceError']
