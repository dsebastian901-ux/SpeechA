"""
============================================================
MRS Speech Analytics Professional
Servicio: Reportes
============================================================
"""

from __future__ import annotations

import csv
import json

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.models.analytics_model import AnalyticsModel
from app.services.analytics_service import AnalyticsService


class ReportService:
    """
    Servicio encargado de preparar y exportar reportes
    basados en los Analytics previamente guardados.

    No vuelve a transcribir ni analizar llamadas.
    """

    # =========================================================
    # DATOS GENERALES DEL REPORTE
    # =========================================================

    @classmethod
    def get_report_data(
        cls,
        project_path: str | Path,
    ) -> Dict[str, Any]:
        """
        Carga todos los Analytics del proyecto y devuelve
        un resumen consolidado más el detalle por llamada.
        """

        analyses = AnalyticsService.load_project_analyses(
            project_path
        )

        return {
            "generated_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "total_calls": len(analyses),
            "average_compliance": cls.calculate_average_compliance(
                analyses
            ),
            "sentiment_distribution": cls.get_sentiment_distribution(
                analyses
            ),
            "reason_distribution": cls.get_reason_distribution(
                analyses
            ),
            "compliance_distribution": cls.get_compliance_distribution(
                analyses
            ),
            "calls": cls.build_call_rows(
                analyses
            ),
        }

    # =========================================================
    # CUMPLIMIENTO PROMEDIO
    # =========================================================

    @staticmethod
    def calculate_average_compliance(
        analyses: List[AnalyticsModel],
    ) -> float:
        if not analyses:
            return 0.0

        scores = []

        for analysis in analyses:
            try:
                score = float(
                    getattr(
                        analysis,
                        "compliance_score",
                        0.0,
                    )
                    or 0.0
                )
            except (
                TypeError,
                ValueError,
            ):
                score = 0.0

            scores.append(
                score
            )

        if not scores:
            return 0.0

        return round(
            sum(scores) / len(scores),
            2,
        )

    # =========================================================
    # DISTRIBUCIÓN DE SENTIMIENTO
    # =========================================================

    @staticmethod
    def get_sentiment_distribution(
        analyses: List[AnalyticsModel],
    ) -> Dict[str, int]:
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
    # DISTRIBUCIÓN DE MOTIVOS
    # =========================================================

    @staticmethod
    def get_reason_distribution(
        analyses: List[AnalyticsModel],
    ) -> Dict[str, int]:
        result: Dict[str, int] = {}

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

            result[
                reason
            ] = result.get(
                reason,
                0,
            ) + 1

        return dict(
            sorted(
                result.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )

    # =========================================================
    # DISTRIBUCIÓN DE CUMPLIMIENTO
    # =========================================================

    @staticmethod
    def get_compliance_distribution(
        analyses: List[AnalyticsModel],
    ) -> Dict[str, int]:
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
                result[
                    status
                ] += 1
            else:
                result[
                    "no_cumple"
                ] += 1

        return result

    # =========================================================
    # DETALLE POR LLAMADA
    # =========================================================

    @classmethod
    def build_call_rows(
        cls,
        analyses: List[AnalyticsModel],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        for analysis in analyses:
            rows.append(
                {
                    "audio_file": str(
                        getattr(
                            analysis,
                            "audio_file",
                            "",
                        )
                        or ""
                    ),
                    "call_reason": str(
                        getattr(
                            analysis,
                            "call_reason",
                            "",
                        )
                        or "No identificado"
                    ),
                    "sentiment": str(
                        getattr(
                            analysis,
                            "sentiment",
                            "",
                        )
                        or "neutral"
                    ),
                    "compliance_status": str(
                        getattr(
                            analysis,
                            "compliance_status",
                            "",
                        )
                        or ""
                    ),
                    "compliance_score": cls._safe_float(
                        getattr(
                            analysis,
                            "compliance_score",
                            0.0,
                        )
                    ),
                    "word_count": cls._safe_int(
                        getattr(
                            analysis,
                            "word_count",
                            0,
                        )
                    ),
                    "summary": str(
                        getattr(
                            analysis,
                            "summary",
                            "",
                        )
                        or ""
                    ),
                    "keywords": ", ".join(
                        [
                            str(keyword)
                            for keyword in (
                                getattr(
                                    analysis,
                                    "keywords",
                                    [],
                                )
                                or []
                            )
                        ]
                    ),
                    "analysis_date": str(
                        getattr(
                            analysis,
                            "analysis_date",
                            "",
                        )
                        or ""
                    ),
                }
            )

        return rows

    # =========================================================
    # DIRECTORIO DE REPORTES
    # =========================================================

    @staticmethod
    def get_reports_directory(
        project_path: str | Path,
    ) -> Path:
        """
        Devuelve:

            proyecto/04_Reportes/Exportados
        """

        project_directory = Path(
            project_path
        ).expanduser().resolve()

        reports_directory = (
            project_directory
            / "04_Reportes"
            / "Exportados"
        )

        reports_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return reports_directory

    # =========================================================
    # EXPORTAR JSON
    # =========================================================

    @classmethod
    def export_json(
        cls,
        project_path: str | Path,
    ) -> Path:
        """
        Genera un reporte consolidado en JSON.
        """

        data = cls.get_report_data(
            project_path
        )

        reports_directory = cls.get_reports_directory(
            project_path
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_path = (
            reports_directory
            / f"reporte_analytics_{timestamp}.json"
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )

        return output_path

    # =========================================================
    # EXPORTAR CSV
    # =========================================================

    @classmethod
    def export_csv(
        cls,
        project_path: str | Path,
    ) -> Path:
        """
        Genera un CSV con una fila por llamada analizada.
        """

        data = cls.get_report_data(
            project_path
        )

        rows = data.get(
            "calls",
            [],
        ) or []

        reports_directory = cls.get_reports_directory(
            project_path
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_path = (
            reports_directory
            / f"reporte_llamadas_{timestamp}.csv"
        )

        fieldnames = [
            "audio_file",
            "call_reason",
            "sentiment",
            "compliance_status",
            "compliance_score",
            "word_count",
            "summary",
            "keywords",
            "analysis_date",
        ]

        with output_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for row in rows:
                writer.writerow(
                    {
                        field: row.get(
                            field,
                            "",
                        )
                        for field in fieldnames
                    }
                )

        return output_path

    # =========================================================
    # UTILIDADES
    # =========================================================

    @staticmethod
    def _safe_float(
        value,
    ) -> float:
        try:
            return round(
                float(
                    value
                    or 0.0
                ),
                2,
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0.0

    @staticmethod
    def _safe_int(
        value,
    ) -> int:
        try:
            return max(
                int(
                    value
                    or 0
                ),
                0,
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0