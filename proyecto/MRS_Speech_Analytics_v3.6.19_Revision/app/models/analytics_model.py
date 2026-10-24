"""
============================================================
MRS Speech Analytics Professional
Modelo: Analytics de Llamadas
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class AnalyticsModel:
    """
    Representa el resultado del análisis de una llamada.
    """

    # Identificación
    audio_file: str = ""
    transcription_file: str = ""

    # Contenido principal
    summary: str = ""
    call_reason: str = ""
    sentiment: str = "neutral"

    # Información complementaria
    keywords: List[str] = field(
        default_factory=list
    )

    observations: List[str] = field(
        default_factory=list
    )

    # Cumplimiento
    compliance_status: str = "pendiente"
    compliance_score: float = 0.0

    # Métricas
    word_count: int = 0
    character_count: int = 0

    # Trazabilidad
    analysis_date: str = field(
        default_factory=lambda: datetime.now().isoformat(
            timespec="seconds"
        )
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    # ========================================================
    # UTILIDADES
    # ========================================================

    def add_keyword(
        self,
        keyword: str,
    ) -> None:
        """Agrega una palabra clave evitando duplicados."""

        value = str(
            keyword or ""
        ).strip()

        if not value:
            return

        if value not in self.keywords:
            self.keywords.append(
                value
            )

    def add_observation(
        self,
        observation: str,
    ) -> None:
        """Agrega una observación al análisis."""

        value = str(
            observation or ""
        ).strip()

        if value:
            self.observations.append(
                value
            )

    def set_compliance_score(
        self,
        score: float,
    ) -> None:
        """
        Establece cumplimiento entre 0 y 100.
        """

        value = max(
            0.0,
            min(
                float(score),
                100.0,
            ),
        )

        self.compliance_score = round(
            value,
            2,
        )

        if value >= 80:
            self.compliance_status = "cumple"

        elif value >= 60:
            self.compliance_status = "parcial"

        else:
            self.compliance_status = "no_cumple"

    def calculate_text_metrics(
        self,
        text: str,
    ) -> None:
        """Calcula métricas básicas de la transcripción."""

        clean_text = str(
            text or ""
        ).strip()

        self.character_count = len(
            clean_text
        )

        self.word_count = len(
            clean_text.split()
        )

    # ========================================================
    # SERIALIZACIÓN
    # ========================================================

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""

        return {
            "audio_file": self.audio_file,
            "transcription_file": self.transcription_file,
            "summary": self.summary,
            "call_reason": self.call_reason,
            "sentiment": self.sentiment,
            "keywords": list(
                self.keywords
            ),
            "observations": list(
                self.observations
            ),
            "compliance_status": self.compliance_status,
            "compliance_score": self.compliance_score,
            "word_count": self.word_count,
            "character_count": self.character_count,
            "analysis_date": self.analysis_date,
            "metadata": dict(
                self.metadata
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "AnalyticsModel":
        """Reconstruye el modelo desde un diccionario."""

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "Los datos de Analytics deben ser un diccionario."
            )

        return cls(
            audio_file=str(
                data.get(
                    "audio_file",
                    "",
                )
                or ""
            ),
            transcription_file=str(
                data.get(
                    "transcription_file",
                    "",
                )
                or ""
            ),
            summary=str(
                data.get(
                    "summary",
                    "",
                )
                or ""
            ),
            call_reason=str(
                data.get(
                    "call_reason",
                    "",
                )
                or ""
            ),
            sentiment=str(
                data.get(
                    "sentiment",
                    "neutral",
                )
                or "neutral"
            ),
            keywords=list(
                data.get(
                    "keywords",
                    [],
                )
                or []
            ),
            observations=list(
                data.get(
                    "observations",
                    [],
                )
                or []
            ),
            compliance_status=str(
                data.get(
                    "compliance_status",
                    "pendiente",
                )
                or "pendiente"
            ),
            compliance_score=float(
                data.get(
                    "compliance_score",
                    0.0,
                )
                or 0.0
            ),
            word_count=int(
                data.get(
                    "word_count",
                    0,
                )
                or 0
            ),
            character_count=int(
                data.get(
                    "character_count",
                    0,
                )
                or 0
            ),
            analysis_date=str(
                data.get(
                    "analysis_date",
                    "",
                )
                or datetime.now().isoformat(
                    timespec="seconds"
                )
            ),
            metadata=dict(
                data.get(
                    "metadata",
                    {},
                )
                or {}
            ),
        )