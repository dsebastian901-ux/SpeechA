"""
============================================================
MRS Speech Analytics Professional
Servicio: Dashboard
============================================================
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from app.models.analytics_model import AnalyticsModel
from app.services.analytics_service import AnalyticsService


class DashboardService:
    """
    Servicio encargado de preparar los indicadores
    generales del Dashboard.

    Los datos se obtienen exclusivamente de los análisis
    previamente guardados en:

        04_Reportes/Analytics

    No vuelve a transcribir ni analizar las llamadas.
    """

    # =========================================================
    # RESUMEN GENERAL
    # =========================================================

    @classmethod
    def get_dashboard_data(
        cls,
        project_path: str | Path,
    ) -> Dict[str, Any]:
        """
        Carga todos los Analytics del proyecto y genera
        la información necesaria para el Dashboard.
        """

        analyses = AnalyticsService.load_project_analyses(
            project_path
        )

        return {
            "total_calls": len(analyses),
            "average_compliance": cls.calculate_average_compliance(
                analyses
            ),
            "sentiments": cls.get_sentiment_distribution(
                analyses
            ),
            "call_reasons": cls.get_reason_distribution(
                analyses
            ),
            "compliance": cls.get_compliance_distribution(
                analyses
            ),
            "top_keywords": cls.get_top_keywords(
                analyses
            ),
            "total_words": cls.calculate_total_words(
                analyses
            ),
            "analyses": analyses,
        }

    # =========================================================
    # CUMPLIMIENTO PROMEDIO
    # =========================================================

    @staticmethod
    def calculate_average_compliance(
        analyses: List[AnalyticsModel],
    ) -> float:
        """
        Calcula el porcentaje promedio de cumplimiento.
        """

        if not analyses:
            return 0.0

        scores = [
            float(
                getattr(
                    analysis,
                    "compliance_score",
                    0.0,
                )
                or 0.0
            )
            for analysis in analyses
        ]

        if not scores:
            return 0.0

        return round(
            sum(scores) / len(scores),
            2,
        )

    # =========================================================
    # SENTIMIENTOS
    # =========================================================

    @staticmethod
    def get_sentiment_distribution(
        analyses: List[AnalyticsModel],
    ) -> Dict[str, int]:
        """
        Devuelve cantidad de llamadas por sentimiento.
        """

        result = {
            "positivo": 0,
            "neutral": 0,
            "negativo": 0,
        }

        for analysis in analyses:

            sentiment = str(
                getattr(
                    analysis,
                    "sentiment",
                    "",
                )
                or ""
            ).strip().lower()

            if sentiment in result:
                result[sentiment] += 1
            else:
                result["neutral"] += 1

        return result

    # =========================================================
    # MOTIVOS
    # =========================================================

    @staticmethod
    def get_reason_distribution(
        analyses: List[AnalyticsModel],
    ) -> Dict[str, int]:
        """
        Agrupa las llamadas por motivo detectado.
        """

        counter = Counter()

        for analysis in analyses:

            reason = str(
                getattr(
                    analysis,
                    "call_reason",
                    "",
                )
                or "No identificado"
            ).strip()

            if not reason:
                reason = "No identificado"

            counter[
                reason
            ] += 1

        return dict(
            counter.most_common()
        )

    # =========================================================
    # ESTADO DE CUMPLIMIENTO
    # =========================================================

    @staticmethod
    def get_compliance_distribution(
        analyses: List[AnalyticsModel],
    ) -> Dict[str, int]:
        """
        Agrupa los resultados de cumplimiento.
        """

        result = {
            "cumple": 0,
            "parcial": 0,
            "no_cumple": 0,
        }

        for analysis in analyses:

            status = str(
                getattr(
                    analysis,
                    "compliance_status",
                    "",
                )
                or ""
            ).strip().lower()

            if status in result:
                result[status] += 1
            else:
                result["no_cumple"] += 1

        return result

    # =========================================================
    # PALABRAS CLAVE
    # =========================================================

    @staticmethod
    def get_top_keywords(
        analyses: List[AnalyticsModel],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene las palabras clave más frecuentes
        entre todos los análisis.
        """

        counter = Counter()

        for analysis in analyses:

            keywords = getattr(
                analysis,
                "keywords",
                [],
            ) or []

            for keyword in keywords:

                clean_keyword = str(
                    keyword
                    or ""
                ).strip().lower()

                if not clean_keyword:
                    continue

                counter[
                    clean_keyword
                ] += 1

        return [
            {
                "keyword": keyword,
                "count": count,
            }
            for keyword, count in counter.most_common(
                limit
            )
        ]

    # =========================================================
    # TOTAL DE PALABRAS
    # =========================================================

    @staticmethod
    def calculate_total_words(
        analyses: List[AnalyticsModel],
    ) -> int:
        """
        Suma el total de palabras procesadas.
        """

        total = 0

        for analysis in analyses:

            try:
                total += int(
                    getattr(
                        analysis,
                        "word_count",
                        0,
                    )
                    or 0
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return total

    # =========================================================
    # MOTIVO PRINCIPAL
    # =========================================================

    @classmethod
    def get_main_reason(
        cls,
        analyses: List[AnalyticsModel],
    ) -> str:
        """
        Devuelve el motivo más frecuente.
        """

        distribution = cls.get_reason_distribution(
            analyses
        )

        if not distribution:
            return "Sin datos"

        return next(
            iter(distribution)
        )

    # =========================================================
    # SENTIMIENTO PRINCIPAL
    # =========================================================

    @classmethod
    def get_main_sentiment(
        cls,
        analyses: List[AnalyticsModel],
    ) -> str:
        """
        Devuelve el sentimiento más frecuente.
        """

        distribution = cls.get_sentiment_distribution(
            analyses
        )

        if not distribution:
            return "Sin datos"

        return max(
            distribution,
            key=distribution.get,
        )

    # =========================================================
    # VERIFICACIÓN DE DATOS
    # =========================================================

    @classmethod
    def has_dashboard_data(
        cls,
        project_path: str | Path,
    ) -> bool:
        """
        Indica si el proyecto tiene Analytics guardados.
        """

        return (
            AnalyticsService.count_project_analyses(
                project_path
            )
            > 0
        )