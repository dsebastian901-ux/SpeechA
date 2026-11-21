"""Importación compatible del único motor Whisper local de producción.

Este espacio no proporciona un motor alternativo ni descarga modelos.
"""
from app.services.whisper_service import WhisperService, WhisperServiceError

__all__ = ['WhisperService', 'WhisperServiceError']
