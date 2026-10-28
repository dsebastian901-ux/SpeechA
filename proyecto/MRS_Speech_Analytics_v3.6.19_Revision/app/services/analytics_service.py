"""
============================================================
MRS Speech Analytics Professional
Servicio: Analytics de llamadas
============================================================
"""

from __future__ import annotations

import json
import re

from collections import Counter
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from app.models.analytics_model import AnalyticsModel
from app.models.transcriptions import TranscriptionModel
from app.services.conversation_evidence import assess_recado, assess_privacy, evidence_units, recipient_statement, payment_places, agent_statement, holder_confirmation, payment_commitment, sentence_evidence, completed_payment
from app.services.payment_instruction_validation import wrong_bank_instructions, transfer_instructions, only_negated_transfers, future_transfer_discussion
from app.services.installment_validation import installment_plan, installment_dates
from app.services.asr_amount_recovery import validated_entries
from app.services.mora_payment_policy import payment_policy, two_installment_window, LIQUIDATION_MORAS
from app.services.amount_review_service import amount_review_status
from app.services.account_source_validation import validate_account_source
from app.services.financial_review_service import apply_financial_review


class AnalyticsService:
    """
    Servicio encargado de analizar transcripciones y
    administrar la persistencia de los resultados.

    Funciones principales:
    - Generar resumen.
    - Detectar motivo de llamada.
    - Detectar sentimiento.
    - Extraer palabras clave.
    - Calcular cumplimiento básico.
    - Guardar Analytics en JSON.
    - Cargar Analytics previamente guardados.
    - Listar análisis del proyecto.
    """

    ENGINE_REVISION = "3.6.19-r20"

    @staticmethod
    def shared_quality_decision(metadata, score, minimum_score=80, duration_seconds=None, base_classification=None):
        """Puerta de aprobación común: lote, solo audios y análisis individual."""
        metadata = metadata if isinstance(metadata, dict) else {}
        checks = metadata.get("quality_checks") or {}
        penalties = metadata.get("penalties") or []
        failures = metadata.get("critical_failures") or []
        status = metadata.get("status_validation") or {}
        negotiation = metadata.get("negotiation_validation") or {}
        reasons = []
        if negotiation.get("liquidation_offer_review_required"):
            reasons.append("Posible liquidación total sin atribución u oferta confirmada; revisar audio")
        account = metadata.get("account_source_validation") or {}
        if account.get("review_required"):
            reasons.append(account.get("reason") or "Datos de cuenta inconsistentes; revisar nombre de salida")
        recovery = metadata.get("amount_recovery_validation") or {}
        if recovery.get("review_required"):
            reasons.append("Importe recuperado por lecturas adicionales de audio; conserva revisión de evidencia")
        financial = metadata.get("financial_review_validation") or {}
        if financial.get("review_required"):
            reasons.append(financial.get("reason") or "Confirmación financiera pendiente de revisión")
        if metadata.get("quality_contact_type") == "CONTACTO NO DETERMINADO":
            reasons.append("Interlocutor sin identificar; requiere revisión")
        critical = any(isinstance(f, dict) and f.get("invalidates") is True for f in failures)
        if critical:
            reasons.append("Incumplimiento crítico confirmado")
        privacy = metadata.get("privacy_validation") or {}
        if privacy.get("confirmed_disclosure"):
            critical = True
            reasons.append(privacy.get("reason") or "Divulgación confirmada a un tercero")
        elif privacy.get("review_required"):
            reasons.append(privacy.get("reason") or "Posible divulgación pendiente de atribución")
        card = metadata.get("card_validation") or {}
        if card.get("result") == "TARJETA INCORRECTA" or str(card.get("result") or "").startswith("REVISAR -"):
            reasons.append(card.get("reason") or "Referencia de tarjeta pendiente de validación")
        for penalty in penalties:
            if not isinstance(penalty, dict):
                continue
            if penalty.get("id") in {"PEN_GROSERIA_SIN_ATRIBUCION", "PEN_QUEJA_MALTRATO"}:
                reasons.append(str(penalty.get("reason") or "Trato al cliente requiere revisión"))
            if penalty.get("id") == "PEN_CONV_LUGARES":
                reasons.append("Faltan dos lugares de pago autorizados en convenio")
            if penalty.get("id") == "PEN_SIN_INTENTO_NEGOCIACION":
                reasons.append("No se confirmó intento de negociación con el titular")
        if status.get("excel_status") and status.get("matches") is None:
            reasons.append("Estatus de Excel sin coincidencia confirmada; requiere revisión")
        if status.get("valid") is False:
            status_reasons = [str(r) for r in status.get("reasons", []) if r]
            reasons.extend(status_reasons or ["Estatus pendiente de validación"])
        if any(isinstance(p, dict) and p.get("id") in {"PEN_CONV_FRAUDE", "PEN_CONV_TRANSFER_REV"} for p in penalties):
            reasons.append("Método o datos de pago requieren revisión de seguridad")
        if (metadata.get("convenio_payment_validation") or {}).get("applies") and not (metadata.get("convenio_payment_validation") or {}).get("minimum_places_met") and not negotiation.get("payment_confirmation_case"):
            reasons.append("Convenio sin dos lugares de pago autorizados confirmados")
        if checks.get("queja_maltrato_detectada"):
            reasons.append("Queja de maltrato requiere revisión")
        if negotiation.get("valid") is False or negotiation.get("review_required"):
            reasons.extend(str(r) for r in negotiation.get("reasons", []) if r)
            if not negotiation.get("reasons"):
                reasons.append("Negociación pendiente de validación")
        if checks.get("groseria_bloquea_aprobacion"):
            reasons.append("Lenguaje ofensivo requiere revisión")
        treatment = metadata.get("treatment_validation") or {}
        if treatment.get("confrontation_review_required"):
            reasons.append("Confrontación sin hablante confirmado; requiere revisión")
        if treatment.get("hostile_interlocutor_review_required"):
            reasons.append("Hostilidad del interlocutor requiere validación")
        if (metadata.get("call_end_validation") or {}).get("review_required"):
            reasons.append("Silencio o finalización sin responsable confirmado; revisar audio")
        if duration_seconds is not None and float(duration_seconds) < 60:
            reasons.append("Duración inferior a 60 segundos")
        duration = metadata.get("duration_validation") or {}
        if duration.get("valid") is False:
            reasons.append(duration.get("reason") or "Duración fuera del rango permitido")
        score_ok = float(score or 0) >= float(minimum_score)
        exception = metadata.get("hostile_interlocutor_exception") or {}
        exception_confirmed = all(exception.get(k) is True for k in
            ("audio_verified", "interlocutor_hostile_or_lascivious", "prevented_script", "agent_professional"))
        # La validación de hostilidad solo resuelve groserías del interlocutor.
        # No perdona privacidad, maltrato previo, referencias ni faltas financieras.
        non_hostility_reasons = [r for r in reasons if r not in {
            "Lenguaje ofensivo requiere revisión", "Hostilidad del interlocutor requiere validación"}]
        if exception_confirmed:
            hostile_penalty_reasons = {str(p.get("reason") or "Trato al cliente requiere revisión")
                for p in penalties if isinstance(p, dict) and p.get("id") == "PEN_GROSERIA_SIN_ATRIBUCION"}
            non_hostility_reasons = [r for r in non_hostility_reasons if r not in hostile_penalty_reasons]
        base = base_classification or {}
        if critical:
            category = "FALLA_GRAVE"
        elif exception_confirmed and score_ok and not non_hostility_reasons:
            category = "APROBADO_CON_EXCEPCION"
        elif reasons:
            category = "REVISAR"
        elif not score_ok:
            category = "NO_APROBADO_MENOR_80"
        elif base.get("estatus_autorizado") is False:
            category = "APROBADO_SIN_ETIQUETAR"
        elif base.get("estatus_autorizado") is True and base.get("tiene_nombre_final") is False:
            category = "REVISAR"
            reasons.append("Falta nombre final para reetiquetar")
        else:
            category = "APROBADO"
        return {"clasificacion": category, "aprobado": category == "APROBADO",
                "score": round(float(score or 0), 2), "puntaje_minimo": minimum_score,
                "cumple_puntaje": score_ok,
                "motivo": ("Excepción por hostilidad validada en audio; gestor profesional" if category == "APROBADO_CON_EXCEPCION" else " | ".join(dict.fromkeys(reasons))) if reasons or category == "APROBADO_CON_EXCEPCION" else
                          ("Cumple reglas de aprobación" if score_ok else "Puntaje inferior al mínimo")}

    # =========================================================
    # STOPWORDS
    # =========================================================

    STOPWORDS = {
        "a",
        "al",
        "algo",
        "algunas",
        "algunos",
        "ante",
        "antes",
        "como",
        "con",
        "contra",
        "cual",
        "cuando",
        "de",
        "del",
        "desde",
        "donde",
        "durante",
        "e",
        "el",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "era",
        "es",
        "esa",
        "esas",
        "ese",
        "eso",
        "esos",
        "esta",
        "estaba",
        "estamos",
        "estan",
        "estar",
        "este",
        "esto",
        "estos",
        "fue",
        "ha",
        "hacia",
        "han",
        "hasta",
        "hay",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "mas",
        "me",
        "mi",
        "mis",
        "muy",
        "no",
        "nos",
        "o",
        "para",
        "pero",
        "por",
        "porque",
        "que",
        "se",
        "si",
        "sin",
        "sobre",
        "su",
        "sus",
        "tambien",
        "te",
        "tiene",
        "tienen",
        "tu",
        "un",
        "una",
        "uno",
        "unos",
        "unas",
        "usted",
        "ustedes",
        "y",
        "ya",
        "yo",
    }

    # =========================================================
    # PALABRAS DE SENTIMIENTO
    # =========================================================

    POSITIVE_WORDS = {
        "bien",
        "bueno",
        "buena",
        "excelente",
        "gracias",
        "agradezco",
        "perfecto",
        "perfecta",
        "correcto",
        "correcta",
        "solucionado",
        "solucionada",
        "ayuda",
        "amable",
        "satisfecho",
        "satisfecha",
        "feliz",
        "claro",
        "clara",
    }

    NEGATIVE_WORDS = {
        "mal",
        "malo",
        "mala",
        "problema",
        "queja",
        "molesto",
        "molesta",
        "enojado",
        "enojada",
        "cancelar",
        "cancelacion",
        "error",
        "fraude",
        "cargo",
        "cobro",
        "reclamo",
        "reclamacion",
        "inconforme",
        "insatisfecho",
        "insatisfecha",
        "demora",
        "fallo",
    }

    # =========================================================
    # ANÁLISIS PRINCIPAL
    # =========================================================

    @classmethod
    def analyze_transcription(
        cls,
        transcription: TranscriptionModel,
        operational_context: Optional[Dict] = None,
    ) -> AnalyticsModel:
        """
        Ejecuta el análisis local de una transcripción.
        """

        if transcription is None:
            raise ValueError(
                "No se recibió una transcripción para analizar."
            )

        # Conservar saltos de línea: pueden delimitar roles de una transcripción revisada.
        text = str(getattr(transcription, "text", "") or "").strip()

        if not text:
            raise ValueError(
                "La transcripción no contiene texto para analizar."
            )

        analysis = AnalyticsModel()

        # -----------------------------------------------------
        # ARCHIVO DE AUDIO
        # -----------------------------------------------------

        analysis.audio_file = str(
            getattr(
                transcription,
                "file_name",
                "",
            )
            or ""
        )

        # -----------------------------------------------------
        # ARCHIVO DE TRANSCRIPCIÓN
        # -----------------------------------------------------

        json_path = str(
            getattr(
                transcription,
                "json_path",
                "",
            )
            or ""
        )

        txt_path = str(
            getattr(
                transcription,
                "txt_path",
                "",
            )
            or ""
        )

        analysis.transcription_file = (
            json_path
            or txt_path
            or ""
        )

        # -----------------------------------------------------
        # MÉTRICAS
        # -----------------------------------------------------

        analysis.calculate_text_metrics(
            text
        )

        # -----------------------------------------------------
        # RESUMEN
        # -----------------------------------------------------

        analysis.summary = cls.generate_summary(
            text
        )

        # -----------------------------------------------------
        # MOTIVO
        # -----------------------------------------------------

        analysis.call_reason = cls.detect_call_reason(
            text
        )

        # -----------------------------------------------------
        # SENTIMIENTO
        # -----------------------------------------------------

        analysis.sentiment = cls.detect_sentiment(
            text
        )

        # -----------------------------------------------------
        # PALABRAS CLAVE
        # -----------------------------------------------------

        analysis.keywords = cls.extract_keywords(
            text
        )

        # -----------------------------------------------------
        # CUMPLIMIENTO
        # -----------------------------------------------------

        enriched_context = dict(operational_context or {})
        enriched_context["_segments"] = list(getattr(transcription, "segments", []) or [])
        enriched_context["_duration_seconds"] = float(getattr(transcription, "duration_seconds", 0.0) or 0.0)
        enriched_context["_amount_recovery"] = (getattr(transcription, "metadata", {}) or {}).get("recuperacion_importes")
        financial_source = dict(getattr(transcription, "metadata", {}) or {})
        financial_source.setdefault("archivo", transcription.file_name)
        financial_source.setdefault("texto", transcription.text)
        financial_source.setdefault("segmentos", transcription.segments)
        enriched_context["_financial_source"] = financial_source
        enriched_context["_financial_review"] = financial_source.get("financial_audio_review")

        compliance = cls.calculate_basic_compliance(
            text,
            operational_context=enriched_context,
        )

        analysis.set_compliance_score(
            compliance["score"]
        )

        # -----------------------------------------------------
        # OBSERVACIONES
        # -----------------------------------------------------

        analysis.observations = list(
            compliance.get(
                "observations",
                [],
            )
        )

        # -----------------------------------------------------
        # FECHA
        # -----------------------------------------------------

        analysis.analysis_date = datetime.now().isoformat(
            timespec="seconds"
        )

        # -----------------------------------------------------
        # METADATOS
        # -----------------------------------------------------

        analysis.metadata = {
            "engine_revision": cls.ENGINE_REVISION,
            "source_language": str(
                getattr(
                    transcription,
                    "detected_language",
                    "",
                )
                or ""
            ),
            "duration_seconds": float(
                getattr(
                    transcription,
                    "duration_seconds",
                    0.0,
                )
                or 0.0
            ),
            "readable_duration": str(
                getattr(
                    transcription,
                    "readable_duration",
                    "",
                )
                or ""
            ),
            "model_name": str(
                getattr(
                    transcription,
                    "model_name",
                    "",
                )
                or ""
            ),
        }

        analysis.metadata["quality_contact_type"] = compliance.get(
            "contact_type", "CONTACTO NO DETERMINADO"
        )
        analysis.metadata["contact_validation"] = compliance.get("contact_validation", {})
        analysis.metadata["quality_blocks"] = compliance.get("blocks", {})
        analysis.metadata["quality_checks"] = compliance.get("checks", {})
        analysis.metadata["operational_context"] = compliance.get(
            "operational_context", {}
        )
        analysis.metadata["manual_rules"] = compliance.get(
            "manual_rules", []
        )
        analysis.metadata["critical_failures"] = compliance.get(
            "critical_failures", []
        )
        analysis.metadata["penalties"] = compliance.get(
            "penalties", []
        )
        analysis.metadata["treatment_validation"] = compliance.get(
            "treatment_validation", {}
        )
        analysis.metadata["call_end_validation"] = compliance.get(
            "call_end_validation", {}
        )
        analysis.metadata["status_validation"] = compliance.get(
            "status_validation", {}
        )
        analysis.metadata["convenio_payment_validation"] = compliance.get(
            "convenio_payment_validation", {}
        )
        analysis.metadata["card_validation"] = compliance.get(
            "card_validation", {}
        )
        analysis.metadata["payment_reference_validation"] = compliance.get("payment_reference_validation", {})
        analysis.metadata["privacy_validation"] = compliance.get("privacy_validation", {})
        exception = (operational_context or {}).get("hostile_interlocutor_exception") or (getattr(transcription, "metadata", {}) or {}).get("hostile_interlocutor_exception")
        if isinstance(exception, dict):
            analysis.metadata["hostile_interlocutor_exception"] = {
                key: exception.get(key) is True for key in
                ("audio_verified", "interlocutor_hostile_or_lascivious", "prevented_script", "agent_professional")}
        analysis.metadata["negotiation_validation"] = compliance.get(
            "negotiation_validation", {}
        )
        data = dict(transcription.metadata or {})
        data.setdefault("archivo", transcription.file_name)
        data.setdefault("texto", transcription.text)
        data.setdefault("segmentos", transcription.segments)
        analysis.metadata["amount_recovery_validation"] = amount_review_status(data, data.get("amount_audio_review"))
        analysis.metadata["account_source_validation"] = validate_account_source(operational_context or {})
        analysis.metadata["financial_review_validation"] = (compliance.get("negotiation_validation") or {}).get("financial_review", {})
        analysis.metadata["final_result"] = compliance.get(
            "final_result", "REVISAR"
        )
        decision = cls.shared_quality_decision(analysis.metadata, analysis.compliance_score,
                                               duration_seconds=enriched_context["_duration_seconds"])
        analysis.metadata["shared_classification"] = decision
        analysis.metadata["final_result"] = decision["clasificacion"]

        return analysis

    # =========================================================
    # RESUMEN
    # =========================================================

    @classmethod
    def generate_summary(
        cls,
        text: str,
        max_sentences: int = 2,
    ) -> str:
        """
        Genera un resumen básico tomando las primeras
        oraciones relevantes.
        """

        clean_text = cls._normalize_spaces(
            text
        )

        if not clean_text:
            return ""

        sentences = re.split(
            r"(?<=[.!?])\s+",
            clean_text,
        )

        sentences = [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

        if not sentences:
            return clean_text[:500]

        selected = sentences[
            :max_sentences
        ]

        return " ".join(
            selected
        ).strip()

    # =========================================================
    # MOTIVO DE LLAMADA
    # =========================================================

    @classmethod
    def detect_call_reason(
        cls,
        text: str,
    ) -> str:
        """
        Detecta el motivo principal mediante palabras clave.
        """

        normalized = cls._normalize_for_analysis(
            text
        )

        reason_patterns = {
            "Cobranza": [
                "cobranza",
                "cobro",
                "pago",
                "adeudo",
                "deuda",
                "vencido",
                "saldo pendiente",
                "promesa de pago",
            ],
            "Aclaración": [
                "aclaracion",
                "aclarar",
                "cargo",
                "movimiento",
                "estado de cuenta",
                "no reconozco",
                "desconozco",
            ],
            "Queja": [
                "queja",
                "reclamo",
                "molesto",
                "molesta",
                "inconforme",
                "mal servicio",
                "no estoy de acuerdo",
            ],
            "Cancelación": [
                "cancelar",
                "cancelacion",
                "dar de baja",
                "baja del servicio",
                "ya no quiero",
            ],
            "Soporte": [
                "soporte",
                "problema tecnico",
                "no funciona",
                "falla",
                "error",
                "acceso",
                "contrasena",
                "aplicacion",
            ],
            "Información": [
                "informacion",
                "consultar",
                "consulta",
                "requisitos",
                "horario",
                "precio",
                "costo",
                "detalle",
            ],
        }

        scores: Dict[str, int] = {}

        for reason, patterns in reason_patterns.items():

            score = 0

            for pattern in patterns:

                if pattern in normalized:
                    score += 1

            scores[
                reason
            ] = score

        if not scores:
            return "No identificado"

        best_reason = max(
            scores,
            key=scores.get,
        )

        if scores[
            best_reason
        ] <= 0:
            return "No identificado"

        return best_reason

    # =========================================================
    # SENTIMIENTO
    # =========================================================

    @classmethod
    def detect_sentiment(
        cls,
        text: str,
    ) -> str:
        """
        Detecta sentimiento mediante ocurrencias positivas
        y negativas.
        """

        tokens = cls._tokenize(
            text
        )

        positive_score = sum(
            1
            for token in tokens
            if token in cls.POSITIVE_WORDS
        )

        negative_score = sum(
            1
            for token in tokens
            if token in cls.NEGATIVE_WORDS
        )

        if positive_score > negative_score:
            return "positivo"

        if negative_score > positive_score:
            return "negativo"

        return "neutral"

    # =========================================================
    # PALABRAS CLAVE
    # =========================================================

    @classmethod
    def extract_keywords(
        cls,
        text: str,
        limit: int = 10,
    ) -> List[str]:
        """
        Obtiene las palabras más frecuentes,
        eliminando palabras comunes.
        """

        tokens = cls._tokenize(
            text
        )

        filtered = [
            token
            for token in tokens
            if (
                len(token) >= 3
                and token not in cls.STOPWORDS
            )
        ]

        if not filtered:
            return []

        counter = Counter(
            filtered
        )

        return [
            word
            for word, _count in counter.most_common(
                limit
            )
        ]

    # =========================================================
    # CUMPLIMIENTO
    # =========================================================


    @staticmethod
    def _parse_context_date(value):
        """Convierte fechas del Excel/contexto a date sin asumir formatos ambiguos."""
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        raw = str(value).strip()
        if not raw:
            return None

        raw = raw.split(" ")[0]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                pass
        return None

    @classmethod
    def _extract_payment_promise_date(cls, text, call_date_value=None, _details=False):
        """
        Extrae la fecha de compromiso más probable.

        A diferencia de la versión anterior, no devuelve la primera fecha
        encontrada. Reúne las menciones de fecha y prioriza la ÚLTIMA mención
        asociada a contexto de pago/acuerdo/cierre. Esto reduce falsos positivos
        cuando el gestor ofrece varias alternativas y el cliente acepta la final.
        """
        base = cls._parse_context_date(call_date_value)
        if base is None:
            return None

        normalized = cls._normalize_for_analysis(
            cls._normalize_spaces(text)
        )

        months = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "setiembre": 9, "octubre": 10,
            "noviembre": 11, "diciembre": 12,
        }
        weekdays = {
            "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3,
            "viernes": 4, "sabado": 5, "domingo": 6,
        }

        candidates = []

        def add_candidate(match, candidate):
            if candidate is None:
                return
            if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", match.group()):
                prefix = normalized[max(0, match.start()-65):match.start()]
                if not re.search(r"\b(?:el|pago|pagar|depositar|fecha|promesa|para|dia)\s+"
                                 r"(?:(?:es|sera|el|para|dia|de|pago)\s+){0,5}$", prefix):
                    return  # Fragmentos de teléfono no son fechas de promesa.
            left = max(0, match.start() - 100)
            right = min(len(normalized), match.end() + 100)
            context = normalized[left:right]
            if re.fullmatch(r"7[/-]11", match.group()) and not re.search(
                    r"(?:dia|fecha|para el|pagar el|pago el)\s*$", normalized[max(0,match.start()-25):match.start()]):
                return  # La tienda 7-11 no es una fecha de pago.

            near_left = max(0, match.start() - 55)
            near_right = min(len(normalized), match.end() + 55)
            near_context = normalized[near_left:near_right]
            payment_context = bool(re.search(
                r"\b(?:pago|pagar|pague|page|deposit|transfer|abono|"
                r"convenio|compromiso|queda|quedamos|acuerdo|liquid|"
                r"cantidad|monto|pesos|confirm)\w*\b", near_context))
            inability_context = bool(re.search(
                r"\b(?:no\s+(?:tengo|puedo|voy|podre|podria)\b.{0,24}(?:pagar|pago)|"
                r"sin\s+dinero|no\s+hay\s+dinero)\b", near_context))
            incidental_date = bool(re.search(
                r"\b(?:vence|vencimiento|fecha\s+limite|estado\s+de\s+cuenta|corte)\b",
                near_context)) and not bool(re.search(
                r"\b(?:pago|convenio|compromiso|queda|quedamos|confirm)\w*\b.{0,30}" + re.escape(match.group(0)),
                near_context))
            # v3.5.8: una fecha de visita/diligencia/recuperación NO es promesa de pago.
            visit_context = bool(re.search(
                r"\b(?:visita|domicilio|domiciliaria|diligencia|licenciad[oa]s?|abogad[oa]s?|"
                r"recuperacion|recuperar|bienes|muebles|folio\s+de\s+la\s+negativa|negativa\s+de\s+pago)\b",
                near_context))
            payment_context = payment_context and not inability_context and not incidental_date and not visit_context
            acceptance_context = bool(re.search(
                r"\b(?:esta bien|de acuerdo|correcto|si|sale|va|"
                r"queda|quedamos|confirm)\b",
                context,
            ))

            # Una fecha solo es utilizable si la propia llamada la vincula
            # con pago/convenio/compromiso. Fechas incidentales no se convierten
            # en promesas de pago.
            if not payment_context:
                return
            score = match.start() + len(normalized) * 2
            if acceptance_context:
                score += len(normalized)
            evidence = normalized[max(0, match.start()-55):min(len(normalized), match.end()+55)].strip()
            candidates.append((score, match.start(), candidate, match.group(0).strip(), evidence))

        # pasado mañana antes que mañana para evitar solapamiento.
        for m in re.finditer(r"\bpasado\s+manana\b", normalized):
            add_candidate(m, base + timedelta(days=2))

        for m in re.finditer(r"(?<!pasado\s)\bmanana\b", normalized):
            add_candidate(m, base + timedelta(days=1))

        for m in re.finditer(r"\bhoy\b", normalized):
            add_candidate(m, base)

        # 17 de agosto / 17 agosto / 17 de agosto de 2026
        month_pattern = (
            r"\b([0-3]?\d)\s+(?:de\s+)?"
            r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
            r"septiembre|setiembre|octubre|noviembre|diciembre)"
            r"(?:\s+(?:de\s+)?(\d{4}))?\b"
        )
        for m in re.finditer(month_pattern, normalized):
            day = int(m.group(1))
            month = months[m.group(2)]
            year = int(m.group(3)) if m.group(3) else base.year
            try:
                candidate = date(year, month, day)
                if not m.group(3) and candidate < base - timedelta(days=31):
                    candidate = date(year + 1, month, day)
                add_candidate(m, candidate)
            except ValueError:
                pass

        day_names = {"uno":1, "dos":2, "tres":3, "cuatro":4, "cinco":5, "seis":6,
                     "siete":7, "ocho":8, "nueve":9, "diez":10, "once":11, "doce":12,
                     "trece":13, "catorce":14, "quince":15, "dieciseis":16, "diecisiete":17,
                     "dieciocho":18, "diecinueve":19, "veinte":20, "veintiuno":21,
                     "veintidos":22, "veintitres":23, "veinticuatro":24, "veinticinco":25,
                     "veintiseis":26, "veintisiete":27, "veintiocho":28, "veintinueve":29,
                     "treinta":30, "treinta y uno":31}
        for m in re.finditer(r"\b("+"|".join(sorted(day_names, key=len, reverse=True))+
                             r")\s+de\s+("+"|".join(months)+r")\b", normalized):
            try:
                candidate = date(base.year, months[m[2]], day_names[m[1]])
                if candidate < base - timedelta(days=31):
                    candidate = candidate.replace(year=base.year+1)
                add_candidate(m, candidate)
            except ValueError:
                pass

        # dd/mm/yyyy, dd-mm-yyyy, dd/mm, dd-mm
        numeric_pattern = (
            r"\b([0-3]?\d)[/-]([01]?\d)(?:[/-](\d{2,4}))?\b"
        )
        for m in re.finditer(numeric_pattern, normalized):
            day = int(m.group(1))
            month = int(m.group(2))
            year_text = m.group(3)
            year = base.year
            if year_text:
                year = int(year_text)
                if year < 100:
                    year += 2000
            try:
                candidate = date(year, month, day)
                if not year_text and candidate < base - timedelta(days=31):
                    candidate = date(year + 1, month, day)
                add_candidate(m, candidate)
            except ValueError:
                pass

        weekday_pattern = (
            r"\b(?:el\s+|este\s+|proximo\s+)?"
            r"(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b"
        )
        for m in re.finditer(weekday_pattern, normalized):
            target = weekdays[m.group(1)]
            delta = (target - base.weekday()) % 7
            if delta == 0 and "proximo" in m.group(0):
                delta = 7
            add_candidate(m, base + timedelta(days=delta))

        if not candidates:
            return None

        # Mayor score = contexto de compromiso más fuerte y mención más tardía.
        candidates.sort(key=lambda item: (item[0], item[1]))
        selected = candidates[-1]
        return {"date": selected[2], "text": selected[3], "evidence": selected[4]} if _details else selected[2]

    @classmethod
    def _extract_payment_promise_date_details(cls, text, call_date_value=None):
        """Devuelve fecha + evidencia textual; nunca crea evidencia desde Excel."""
        return cls._extract_payment_promise_date(text, call_date_value, _details=True) or {
            "date": None, "text": "", "evidence": ""}

    # Tabla 04_Moras_Cortes contrastada con el manual operativo recibido (portada 2.0).
    # Bradescard conserva Asignación y Vencimiento; solo se deriva Fecha de Pago.
    CUT_PAYMENT_DAY = {3: 26, 5: 28, 8: 1, 10: 3, 11: 4, 15: 8, 19: 12, 20: 13, 23: 16, 25: 18, 28: 21}

    @classmethod
    def _extract_cut_from_context(cls, context: Dict) -> Optional[int]:
        # v3.6.16: Corte explícito del Excel tiene prioridad. Campaña queda
        # únicamente como compatibilidad con relaciones anteriores.
        raw_cut = str(context.get("corte") or "").strip()
        m = re.search(r"\b(3|5|8|10|11|15|19|20|23|25|28)\b", raw_cut)
        if m:
            return int(m.group(1))
        raw = str(context.get("campana") or "")
        m = re.search(r"\bCORTE\s*(3|5|8|10|11|15|19|20|23|25|28)\b", raw, re.I)
        return int(m.group(1)) if m else None

    @classmethod
    def _calculate_payment_date_from_cut(cls, context: Dict):
        cut = cls._extract_cut_from_context(context)
        day = cls.CUT_PAYMENT_DAY.get(cut)
        if not day:
            return cut, None
        call_dt = cls._parse_context_date(context.get("fecha"))
        assignment_dt = cls._parse_context_date(context.get("fecha_asignacion"))
        base = call_dt or assignment_dt
        if base is None:
            return cut, None
        from calendar import monthrange
        year, month = base.year, base.month
        # La tabla da el día de pago del periodo gestionado. No desplazarlo
        # automáticamente al mes siguiente por ser menor al número de corte.
        try:
            return cut, date(year, month, min(day, monthrange(year, month)[1]))
        except Exception:
            return cut, None

    @classmethod
    def calculate_basic_compliance(
        cls,
        text: str,
        operational_context: Optional[Dict] = None,
    ) -> Dict:
        """
        Motor de calidad y cumplimiento basado en el Manual Operativo
        Speech Analytics Bradescard v2.

        El contexto operacional puede contener:
        - estatus_grabacion
        - fecha_asignacion
        - vencimiento
        - asignacion
        - fecha
        - gestor
        - supervisor

        La función conserva compatibilidad con llamadas anteriores donde
        solo se enviaba el texto.
        """

        context = dict(operational_context or {})
        normalized = cls._normalize_for_analysis(text)

        def norm(value) -> str:
            return cls._normalize_for_analysis(str(value or ""))

        def any_of(patterns, source: Optional[str] = None) -> bool:
            haystack = normalized if source is None else norm(source)
            return any(norm(pattern) in haystack for pattern in patterns)

        def add_penalty(
            penalty_id: str,
            category: str,
            reason: str,
            points: int,
            invalidates: bool = False,
            rule_ids: Optional[List[str]] = None,
        ) -> None:
            nonlocal penalty_total
            entry = {
                "id": penalty_id,
                "category": category,
                "reason": reason,
                "points": int(points),
                "invalidates": bool(invalidates),
                "rule_ids": list(rule_ids or []),
            }
            if not any(p["id"] == penalty_id for p in penalties):
                penalties.append(entry)
                penalty_total += abs(int(points))
                if invalidates:
                    critical_failures.append(entry)

        # ---------------------------------------------------------
        # CONTEXTO EXCEL / OPERATIVO
        # ---------------------------------------------------------
        excel_status = re.sub(r"\s+", " ", str(context.get("estatus_grabacion") or "").strip().upper().replace("_", " ").replace("-", " "))
        canonical_excel_status = "MENSAJE CON FAMILIAR" if re.fullmatch(r"RECADO\s*REF\s*[12]", excel_status) else excel_status
        assignment = str(context.get("asignacion") or "").strip().upper()
        assignment_date = context.get("fecha_asignacion")
        limit_date = None
        due_date = context.get("vencimiento")
        call_date = context.get("fecha")
        campaign = context.get("campana")
        cut_applied, calculated_payment_date = cls._calculate_payment_date_from_cut(context)

        parsed_call_date = cls._parse_context_date(call_date)
        parsed_limit_date = calculated_payment_date
        parsed_due_date = cls._parse_context_date(due_date)
        promise_date_details = cls._extract_payment_promise_date_details(text, call_date)
        promise_date = promise_date_details.get("date")
        promise_date_text = promise_date_details.get("text") or ""
        promise_date_evidence = promise_date_details.get("evidence") or ""

        assignment_norm = (
            assignment.replace(" ", "")
            .replace("_", "")
            .replace("-", "")
        )

        # Homologa las moras usadas por el manual.
        mora_aliases = {
            "1": "1PV",
            "MORA1": "1PV",
            "1PV": "1PV",
            "1FLP": "1FLP",
            "1-FLP": "1FLP",
            "MORA1FLP": "1FLP",
            "2": "2PV",
            "MORA2": "2PV",
            "2PV": "2PV",
            "3": "3PV",
            "MORA3": "3PV",
            "3PV": "3PV",
            "3HN": "3HN",
            "4": "4PV",
            "4PV": "4PV",
            "5": "5PV",
            "5PV": "5PV",
            "6": "6PV",
            "6PV": "6PV",
            "C1": "C1",
            "C2": "C2",
            "C3": "C3",
            "C4": "C4",
            "B": "B",
            "A": "A",
        }
        mora = mora_aliases.get(assignment_norm, assignment)
        mora_policy = payment_policy(mora, parsed_call_date, parsed_due_date)
        if not mora_policy["uses_cut"] and mora in LIQUIDATION_MORAS:
            cut_applied, calculated_payment_date, parsed_limit_date = None, None, None

        # ---------------------------------------------------------
        # DETECCIÓN DE INTERLOCUTOR / ESTATUS
        # ---------------------------------------------------------
        segments = context.get("_segments") or []
        unknown_debtor = recipient_statement(text, segments,
            r"\b(?:no (?:lo|la) conozco|ni (?:lo|la) conozco|no conozco a|"
            r"no se quien es|nunca ha vivido aqui|numero (?:equivocado|incorrecto))\b")

        recado_assessment = assess_recado(text, context.get("_segments") or [])
        family = bool(recado_assessment["family"])
        spouse = any(re.search(r"\b(?:espos[oa]|marido|mujer)\b", e["phrase"])
                     for e in recado_assessment["family"])
        third_party = recipient_statement(text, segments,
            r"\b(?:soy (?:su )?(?:companero|companera|vecino|vecina|amigo|amiga|conocido|conocida|encargado de la casa|encargada de la casa)|es nuestro proveedor|lo conoci en una fiesta)\b")
        work_contact = recipient_statement(text, segments,
            r"\b(?:soy (?:su )?compan(er[oa]) de trabajo|(?:es|era) mi (?:trabajador|trabajadora|empleado|empleada)|trabaja (?:conmigo|para mi))\b")
        titular = recipient_statement(text, segments,
            r"\b(?:soy yo|(?:si )?soy (?:el |la )?titular|habla (?:el |la )titular)\b")
        contact_confirmation = holder_confirmation(text, segments)
        titular = titular or contact_confirmation["confirmed"]
        # La ausencia declarada confirma un tercero, no su parentesco. Una
        # entrega posterior al titular prevalece sobre esa respuesta inicial.
        intermediary_response = bool(not titular and recipient_statement(text, segments,
            r"^(?:(?:bueno|pues)[, ]+)?(?:(?:el|ella) )?(?:no se encuentra(?: aqui| en casa| en este momento)?|"
            r"no esta (?:aqui|en casa)|esta trabajando)[.!]?$"))
        third_party = third_party or intermediary_response

        if unknown_debtor:
            contact_type = "NO CONOCEN A DEUDOR"
            detected_status = "NO CONOCEN A DEUDOR"
        elif family:
            contact_type = "TERCERO / FAMILIAR"
            detected_status = ""
        elif work_contact:
            contact_type = "TERCERO / TRABAJO"
            detected_status = ""
        elif third_party:
            contact_type = "TERCERO"
            detected_status = ""
        elif titular:
            contact_type = "TITULAR"
            detected_status = ""
        else:
            contact_type = "CONTACTO NO DETERMINADO"
            detected_status = ""

        relationship = ""
        if spouse:
            relationship = "ESPOSO/A"
        elif family:
            relationship = "FAMILIAR"
        elif work_contact:
            relationship = "TRABAJO"
        elif third_party:
            relationship = "TERCERO"

        # ---------------------------------------------------------
        # SEÑALES GENERALES DEL MANUAL
        # ---------------------------------------------------------
        # Identificación del despacho MRS.
        # Regla v3.4.3: normaliza siglas con puntos/espacios y acepta MR cuando
        # aparece en un contexto inequívoco de identificación del despacho.
        # Ejemplo obligatorio: "corporativo M.R.E." -> CUMPLE.
        mrs_compact = re.sub(r"[^a-z0-9ñ]+", " ", normalized).strip()

        # Colapsa variantes de siglas que Whisper puede separar con puntos o
        # espacios: M.R.E. -> mre, M.R.S. -> mrs, M R S -> mrs.
        mrs_initialism_text = re.sub(
            r"\bm\s*[\.\-_ ]*\s*r\s*[\.\-_ ]*\s*([se])\b",
            lambda m: "mr" + m.group(1),
            normalized,
        )
        # Reconoce siglas adicionales del despacho pronunciadas letra por letra.
        # SMRS / S.M.R.S. / S M R S y SRM / S.R.M. / S R M.
        mrs_initialism_text = re.sub(
            r"\bs\s*[\.\-_ ]*\s*m\s*[\.\-_ ]*\s*r\s*[\.\-_ ]*\s*s\b",
            "smrs", mrs_initialism_text,
        )
        mrs_initialism_text = re.sub(
            r"\bs\s*[\.\-_ ]*\s*r\s*[\.\-_ ]*\s*m\b",
            "srm", mrs_initialism_text,
        )
        mrs_initialism_text = re.sub(r"[^a-z0-9ñ]+", " ", mrs_initialism_text).strip()

        mrs_known_variant = bool(re.search(
            r"\b(?:mrs|smrs|srm|mre|mrse|mrese|mres|mdrs|marrese|merrese|emere?se|mrc)\b",
            mrs_initialism_text,
        ))

        # Contextos que hacen inequívoca la referencia al despacho. MR solo
        # cuenta cuando está ligado a uno de estos contextos; no se acepta MR
        # aislado en cualquier parte de la conversación.
        mrs_context_pattern = (
            r"(?:corporativo(?:\s+juridico)?|despacho|juridico|consultor(?:es)?|consultoria|"
            r"le\s+habl(?:o|amos)|habl(?:o|amos)|le\s+llam(?:o|amos)|llam(?:o|amos)|"
            r"somos|por\s+parte\s+de)"
        )
        mr_token_pattern = r"mr[a-z0-9ñ]*"
        mrs_mr_context_variant = bool(
            re.search(
                rf"\b{mrs_context_pattern}\b.{{0,60}}\b{mr_token_pattern}\b",
                mrs_initialism_text,
            )
            or re.search(
                rf"\b{mr_token_pattern}\b.{{0,60}}\b(?:corporativo|despacho|juridico|consultores?|consultoria)\b",
                mrs_initialism_text,
            )
        )
        mrs_smr_context_variant = bool(re.search(
            r"\b(?:consultor(?:es)?|despacho|juridico|corporativo)\s+(?:de\s+)?smr\b",
            mrs_initialism_text))

        # Formas explícitas completas también son válidas. Para MR simple se
        # exige el contexto anterior.
        identifies_mrs_explicit = mrs_known_variant
        identifies_mrs_asr = mrs_known_variant or mrs_mr_context_variant or mrs_smr_context_variant
        identifies_mrs = bool(identifies_mrs_explicit or mrs_mr_context_variant or mrs_smr_context_variant)
        mrs_asr_variant = mrs_known_variant
        mrs_presentation_context = bool(re.search(mrs_context_pattern, mrs_initialism_text))

        represents_bradescard = any_of([
            "en representacion de bradescard",
            "en representacion al banco de bradescard",
            "en representacion a bradescard",
            "representamos a bradescard",
            "de parte de bradescard",
            "en representacion",
        ])
        false_bradescard_identity = any_of([
            "habla bradescard",
            "soy de bradescard",
            "llamo de bradescard",
            "le llamo de bradescard",
        ])
        advisor_name = any_of([
            "mi nombre es",
            "le atiende",
            "le saluda",
            "su servidor",
            "su servidora",
        ])

        asks_person = any_of([
            "puedo comunicar",
            "puede comunicar",
            "me comunica",
            "se encuentra",
            "hablo con",
            "tengo el gusto",
        ])
        relationship_validation = relationship != "" or any_of([
            "con quien tengo el gusto",
            "con quien tuve el gusto",
            "que parentesco",
            "es familiar",
            "es conocido",
            "es conocida",
        ])

        callback = any_of([
            "que se comunique",
            "se pueda comunicar",
            "pueda comunicarse",
            "comunicarse con",
            "marque al",
            "llame al",
            "numero de telefono",
            "telefono",
        ])
        leaves_message = any_of([
            "dejar un recado",
            "le puedo dejar un recado",
            "le dejo el recado",
            "recado",
            "mensaje",
        ])

        # RECADO REF1/REF2: análisis contextual del destinatario del recado.
        # "soy yo" puede responder a la identificación del REFERENTE, no del titular.
        recado_expected = canonical_excel_status == "MENSAJE CON FAMILIAR"
        recado_applies = recado_expected or (not excel_status and family)
        recado_family_evidence = [e["phrase"] for e in recado_assessment["family"]]
        # Distinguir "no vive aquí" de "no conozco"; el primero no niega parentesco.
        recado_unknown_explicit = bool(re.search(
            r"\b(?:no (?:lo|la) conozco|ni (?:lo|la) conozco|no se quien es|"
            r"nunca (?:lo|la) he conocido|numero equivocado)\b", normalized))
        # Negativas explícitas a tomar/transmitir el mensaje: no equivalen a recado válido.
        recado_refusal = bool(re.search(
            r"\b(?:yo tampoco voy a andar|no voy a andar)\b.{0,50}\b(?:buscando|pasando|mensaje)|"
            r"\b(?:no tengo (?:con que|donde) (?:anotar|apuntar)|no puedo anotar|"
            r"no tengo como anotarlo|no me interesa recibir el recado)\b",
            normalized,
        ))
        recado_declines = bool(re.search(
            r"\b(?:no (?:le|se) (?:voy a|puedo|quiero) (?:dar|pasar|mandar) (?:el )?(?:recado|mensaje)|"
            r"no soy (?:su )?mensajer[oa]|no tengo (?:como|forma de) (?:contactarl[oa]|avisarl[oa]))\b", normalized))
        recado_transmitted = bool(re.search(
            r"\b(?:le (?:voy a|puedo) (?:pasar|dar|mandar|hacer llegar) (?:el )?(?:recado|mensaje)|"
            r"(?:le|se lo) (?:comento|aviso|envio|mando|digo)|"
            r"en cuanto (?:lo|la) vea le (?:comento|digo|aviso)|"
            r"(?:diga(?:le)?|indiquele|mencionele|comentele|avis(?:e|ele)) (?:por favor )?que|"
            r"(?:le puedo dejar|le dejo|le voy a dejar|le voy a dictar) (?:un |el )?(?:numero|recado|mensaje)|"
            r"(?:le menciona que|le mencion[eo] que|es un numero para (?:que|aquellos)|"
            r"(?:indiquele|digale|mencionele) (?:a|al|a la) ))\b", normalized))
        recado_callback = bool(re.search(
            r"\b(?:que se comunique|que (?:nos )?llame|que (?:nos )?marque|"
            r"(?:se|pueda) comunicar con nosotros|numero (?:de telefono|de contacto|de atencion)|"
            r"tiene donde anotar|tenga donde anotar)\b", normalized))
        # Un rechazo explícito bloquea la aprobación aunque el gestor haya dictado un número.
        # "Le puedo dejar" es una solicitud del gestor, NO prueba aceptación del interlocutor.
        # Si el texto carece de confirmación, se conserva REVISAR (no se fabrica una aprobación).
        recado_recibido_explicito = bool(recado_assessment["acceptance"])
        recado_refusal = bool(recado_refusal or recado_assessment["refusal"])
        # La pregunta de si puede anotar no demuestra que se dictó un mensaje.
        recado_callback = bool(re.search(
            r"\b(?:que (?:se comunique|(?:nos |me )?(?:llame|marque))|"
            r"(?:se|pueda) comunicar con nosotros|numero (?:de telefono|de contacto|de atencion))\b",
            normalized))
        recado_real = bool(recado_callback and (recado_transmitted or leaves_message)
                           and not (recado_declines or recado_refusal)
                           and recado_recibido_explicito)
        if recado_real:
            detected_status = {"TERCERO / FAMILIAR": "MENSAJE CON FAMILIAR",
                               "TERCERO / TRABAJO": "MENSAJE EN TRABAJO",
                               "TERCERO": "MENSAJE CON TERCERO"}.get(contact_type, detected_status)
        if recado_applies:
            # La relación familiar explícita prevalece sobre "soy yo" (identidad del referente).
            if recado_family_evidence and not recado_unknown_explicit:
                family = True
                spouse = spouse or any('espos' in x or 'marido' in x for x in recado_family_evidence)
                contact_type = "TERCERO / FAMILIAR"
                relationship = "ESPOSO/A" if spouse else "FAMILIAR"
                detected_status = "MENSAJE CON FAMILIAR" if recado_real else ""
            elif contact_type == "TITULAR" and re.search(r"\b(?:referencia|numero de referencia|dejo (?:su|el) numero)\b", normalized):
                contact_type = "CONTACTO NO DETERMINADO"
                detected_status = ""
                relationship = ""

        # ---------------------------------------------------------
        # PROTECCIÓN DE DATOS: INFORMACIÓN FINANCIERA A TERCEROS
        # ---------------------------------------------------------
        # No se penalizan palabras aisladas como "saldo", "pago",
        # "acuerdo de pago" o "propuestas de pago". Whisper puede
        # producir falsos positivos (por ejemplo: "saldo policía").
        #
        # PEN003 requiere evidencia contextual concreta de mora,
        # adeudo o monto revelado al tercero.

        # Mora expresada de forma concreta:
        # "4 meses de atraso", "cuatro meses de atraso", etc.
        months_words = (
            r"(?:un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|"
            r"nueve|diez|once|doce)"
        )
        months_in_arrears = bool(
            re.search(
                rf"\b(?:\d+|{months_words})\s+mes(?:es)?\s+de\s+atraso\b",
                normalized,
            )
        )

        overdue_payments_disclosed = bool(
            re.search(
                r"\b(?:\d+\s+)?pago(?:s)?\s+vencid(?:o|os|a|as)\b",
                normalized,
            )
        )

        contract_default_disclosed = bool(
            re.search(
                r"\bincumplimiento\s+(?:al|del|de)\s+(?:el\s+)?contrato\b",
                normalized,
            )
        )

        # Divulgación explícita de mora/atraso a un tercero.
        # No se activa por la palabra "atraso" aislada: exige una construcción
        # que atribuya el atraso/incumplimiento al titular o a su cuenta/tarjeta.
        arrears_status_disclosed = bool(
            re.search(
                r"\b(?:"
                r"(?:ha|han|tiene|presenta|presentado|presenta\s+un|ha\s+presentado\s+un)"
                r".{0,35}\batraso\b|"
                r"\batraso\s+(?:con|en)\s+(?:el\s+)?pago\b|"
                r"\b(?:cuenta|tarjeta)\b.{0,30}\b(?:atrasad|vencid|moros)\w*\b"
                r")",
                normalized,
            )
        )

        # Monto/saldo/adeudo: se exige una construcción concreta.
        # Una aparición aislada de "saldo" NO activa PEN003.
        money_expression = r"(?:\$?\s*\d[\d,.\s]*|[a-z]+(?:\s+[a-z]+){0,5}\s+pesos?)"

        balance_amount_disclosed = bool(
            re.search(
                rf"\b(?:su\s+)?saldo\s+(?:es|de|por|asciende\s+a|pendiente\s+es|vencido\s+es)\s+{money_expression}",
                normalized,
            )
        )

        debt_amount_disclosed = bool(
            re.search(
                rf"\b(?:debe|adeudo\s+de|deuda\s+de|monto\s+de)\s+{money_expression}",
                normalized,
            )
        )

        # v3.5.5 · Definición operativa MRS de información sensible a terceros.
        # Solo bloquea por datos financieros cuantitativos (saldo/monto/pago mínimo/
        # convenio-liquidación) o por revelar el número COMPLETO de tarjeta.
        # La terminación de tarjeta, el atraso/mora, el recado, MRS y teléfono de
        # contacto NO son información sensible bajo esta regla.
        payment_minimum_amount_disclosed = bool(re.search(
            rf"\bpago\s+minimo\s+(?:es|de|por|asciende\s+a)?\s*{money_expression}",
            normalized,
        ))
        settlement_amount_disclosed = bool(re.search(
            rf"\b(?:convenio|liquidacion|liquidar|regularizar|ponerse\s+al\s+corriente)\b"
            rf".{{0,40}}\b(?:pagar|pago|importe|monto|pesos|cantidad|por)\s+{money_expression}",
            normalized,
        ))
        # 15-16 dígitos reales (admite espacios/guiones); no confundir con la frase
        # permitida "los 16 dígitos" ni con una terminación de 4 dígitos.
        # A card number is a disclosure only when the number is introduced as
        # a card/account/reference, not when it is a telephone or callback number.
        full_card_number_disclosed = False
        for card_match in re.finditer(r"(?<!\d)(?:\d[ -]?){14,15}\d(?!\d)", str(text or "")):
            prefix = str(text or "")[max(0, card_match.start()-90):card_match.start()].lower()
            if re.search(r"(?:tarjeta|plastico|cuenta|referencia)\s*(?:numero|no\.?|de|es|terminacion)?\s*$", prefix):
                full_card_number_disclosed = True
                break

        # Protección adicional: divulgar a un tercero el estado de mora, deuda,
        # negativa de pago o recuperación contractual también exige bloqueo.
        # No depende de que se haya dicho un importe numérico.
        third_party_debt_disclosure = bool(
            months_in_arrears or overdue_payments_disclosed or contract_default_disclosed
            or bool(re.search(r"\b(?:\d+|un|una|dos|tres|cuatro|cinco|seis)\s+(?:mensualidades|meses)\s+(?:vencid[ao]s?|que no paga)\b", normalized))
            or arrears_status_disclosed
            # Tercero informado expresamente de deuda o mensualidades, aunque no se mencione cifra.
            or re.search(r"\b(?:"
                         r"(?:tiene|cuenta con|presenta) (?:una |un )?deuda|"
                         r"(?:son|tiene|presenta) (?:las |sus )?mensualidades|"
                         r"(?:dos|tres|cuatro|cinco|seis|\d+) mensualidades|"
                         r"presenta (?:un |una )?(?:adeudo|deuda)|"
                         r"cubrir (?:el |su )?atraso|"
                         r"cuenta (?:que ha sido )?asignada (?:a |al )?(?:juridico|cobranza))\b", normalized)
            or re.search(r"\b(?:saldo pendiente|saldo vencido|deuda pendiente|adeudo pendiente|"
                         r"negativa de pago|recuperacion (?:del|de su|en el) saldo|"
                         r"respecto a su atraso|en relacion a su atraso|"
                         r"presenta (?:un )?(?:atraso|adeudo|saldo pendiente))\b", normalized)
        )

        financial_information = any([
            balance_amount_disclosed,
            debt_amount_disclosed,
            payment_minimum_amount_disclosed,
            settlement_amount_disclosed,
            full_card_number_disclosed,
            third_party_debt_disclosure,
        ])

        payment_purpose = any_of([
            "pago",
            "saldo",
            "adeudo",
            "deuda",
            "acuerdo de pago",
            "propuesta de pago",
            "convenio",
            "regularizar",
            "regularice",
        ])

        # ---------------------------------------------------------
        # REGLAS NO CONOCEN A DEUDOR
        # ---------------------------------------------------------
        arco_process = agent_statement(text, segments,
            r"\b(?:puede ejercer|para ejercer|solicitar|tramitar|ejercer|procedimiento|proceso|tramite)\b"
            r".{0,65}\b(?:derechos? (?:a )?arco|arco)\b")
        asks_line_tenure = any_of([
            "cuanto tiempo tiene con la linea",
            "cuanto tiempo lleva con la linea",
            "desde hace cuanto tiene la linea",
            "desde hace cuanto cuenta con la linea",
            "tiempo con la linea",
            "antiguedad de la linea",
            "hace cuanto tiene este numero",
            "hace cuanto tiene el numero",
        ])
        # v3.6.18: también cuenta la confirmación espontánea del tercero sobre
        # cuánto tiempo lleva con la línea; no es obligatorio que Whisper conserve
        # la pregunta exacta del gestor.
        confirms_line_tenure = bool(re.search(
            r"\b(?:yo\s+)?(?:tengo|llevo|cuento\s+con)\b.{0,35}\b(?:un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|\d+)\s+(?:ano|anos|año|años|mes|meses)\b.{0,45}\b(?:telefono|teléfono|linea|línea|numero|número)\b"
            r"|\b(?:desde\s+hace|hace)\s+(?:un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|\d+)\s+(?:ano|anos|año|años|mes|meses)\b.{0,45}\b(?:telefono|teléfono|linea|línea|numero|número)\b",
            normalized, re.I
        ))
        tenure_answer = bool(re.search(
            r"(?:cuanto tiempo.{0,50}(?:linea|numero)|desde hace cuanto.{0,50}(?:linea|numero))"
            r"[.?!,; ]{1,8}(?:(?:tengo|llevo|hace) )?(?:un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|\d+) (?:anos?|mes(?:es)?)\b",
            normalized))
        line_tenure_confirmed = bool(confirms_line_tenure or tenure_answer)

        asks_ine_or_line_proof = agent_statement(text, segments,
            r"\b(?:ine|identificacion oficial|comprobante de (?:la linea|telefono|propiedad de la linea))\b")
        gives_privacy_email = agent_statement(text, segments,
            r"\bprivacidad1?@bradesco\.com\.mx\b")

        no_conocen_valid = (
            unknown_debtor
            and arco_process
            and line_tenure_confirmed
            and asks_ine_or_line_proof
            and gives_privacy_email
        )

        # ---------------------------------------------------------
        # REGLAS DE NEGOCIACIÓN
        # ---------------------------------------------------------
        # v3.5.2 - atribución de liquidación más conservadora.
        # Frases en primera persona del titular (pagué/yo/quiero/creí...) son
        # antecedentes y NO una oferta del gestor. Evitamos patrones genéricos
        # como "para ... liquidar", que provocaban falsos positivos.
        holder_liquidation_report = bool(re.search(
            r"\b(?:yo\s+)?(?:pense|pensaba|crei|creia|entendi|entendia)\b.{0,100}\b(?:liquidar|liquide|liquidado|liquidacion)\b"
            r"|\b(?:yo\s+)?(?:ya\s+)?(?:la|lo)\s+(?:liquide|liquidado)\b"
            r"|\b(?:me\s+dijeron|me\s+habian\s+dicho|segun\s+yo)\b.{0,100}\b(?:liquidar|liquidado|liquidacion)\b"
            r"|\b(?:yo\s+)?pague\b.{0,100}\bpara\s+liquidar\b"
            r"|\b(?:yo\s+)?(?:quiero|queria|quise)\b.{0,80}\bliquidar\b",
            normalized,
        ))
        liquidation_offer_pattern = re.compile(
            r"(?P<payment>\bcon\s+(?:este|ese|el)\s+pago\b.{0,80}\b(?:liquida|liquidaria|liquidar)\b)"
            r"|(?P<directive>\b(?:usted\s+)?(?:puede|podra|debe|debera|tiene\s+que|tendria\s+que)\b.{0,80}\b(?:liquidar|liquida)\b)"
            r"|(?P<offer>\b(?:le\s+ofrecemos|le\s+podemos\s+ofrecer|la\s+opcion\s+es)\b.{0,100}\b(?:liquidar|liquidacion)\b)"
            r"|(?P<bare>\b(?:liquida|liquidaria)\s+(?:su\s+cuenta|la\s+cuenta|saldo\s+total|el\s+saldo\s+total)\b"
            r"|\b(?:tendria|tendra|dejaria|dejara)\s+(?:su|la)\s+cuenta\s+en\s+ceros\b)",
        )
        # «Finiquitar la deuda» expresa liquidación total, aunque la oferta
        # termine con una pregunta o quede partida entre ventanas de Whisper.
        settlement_pattern = (
            r"\b(?:se le esta ofreciendo|le (?:ofrecemos|ofrezco)|le podemos ofrecer)\b"
            r".{0,80}\b(?:descuento|opcion)\b.{0,45}\bpara\s+"
            r"(?:(?:finiquitar|fin de quitar) (?:la |su )?(?:deuda|cuenta)|liquidar (?:la |su )?cuenta|"
            r"liquidar lo que (?:ya )?es la cuenta)\b")
        explicit_settlement_offer = any(
            unit["speaker_role"] not in {"TITULAR", "TERCERO", "INTERLOCUTOR"}
            and not re.search(r"\b(?:me dijeron|me habian dicho|segun yo|crei|pense)\b", norm(unit["text"]))
            and agent_statement(unit["text"], (), settlement_pattern)
            for unit in sentence_evidence(text, segments))
        agent_liquidation_offer = explicit_settlement_offer
        liquidation_offer_evidence = []
        for unit in sentence_evidence(text, segments):
            if unit["speaker_role"] in {"TITULAR", "TERCERO", "INTERLOCUTOR"}:
                continue
            for clause in re.split(r"[;]|(?=¿)", unit["text"]):
                folded = norm(clause)
                for candidate in liquidation_offer_pattern.finditer(folded):
                    if re.search(r"\b(?:me dijeron|me habian dicho|segun yo|yo pague|yo quiero|crei|pense)\b", folded) or re.search(
                            r"\b(?:el cliente|la cliente|el titular|la titular|usted)\s+(?:dijo|dice|menciona|comenta|confirmo|me dijo)\b", folded):
                        continue
                    prefix = folded[max(0, candidate.start()-60):candidate.start()]
                    if re.search(r"\b(?:no|nunca|jamas)\s+(?:(?:se|le)\s+)?$", prefix) or re.search(
                            r"\bno\s+(?:puede|podra|debe|debera|liquida|liquidaria)\b", candidate.group()):
                        continue
                    # Cubrir lo vencido no equivale a liquidar la cuenta completa.
                    if re.match(r"\s+(?:lo que es\s+)?(?:(?:su|el|la)\s+)?(?:saldo vencido|mensualidad(?: vencida)?|pago (?:minimo|vencido)|lo vencido)\b",
                                folded[candidate.end():]):
                        continue
                    question = "?" in folded or "¿" in folded
                    # «Debe 1800 ... voy a liquidar» combina saldo e intención del
                    # cliente. El verbo deber seguido de un monto no es una orden.
                    owed_amount = candidate.lastgroup == "directive" and bool(re.match(
                        r"(?:usted\s+)?(?:debe|debera)\s+(?:\$?\s*\d|mil\b|dos\b|tres\b|cuatro\b|cinco\b|seis\b|siete\b|ocho\b|nueve\b|diez\b|once\b|doce\b|quince\b|veinte\b|treinta\b|cien\b|ciento\b|doscientos\b|trescientos\b|cuatrocientos\b|quinientos\b|seiscientos\b|setecientos\b|ochocientos\b|novecientos\b)",
                        candidate.group()))
                    personal_intent = bool(re.search(r"\b(?:voy (?:a|al)|quiero|queria|yo)\b.{0,35}\bliquidar\b", candidate.group()))
                    uncertain_claim = bool(re.search(r"\b(?:no creo|no creemos|no se si|no sabria si|tal vez|quizas|puede que)\b", prefix))
                    confirmed = not (question or owed_amount or personal_intent or uncertain_claim) and (candidate.lastgroup != "bare" or unit["speaker_role"] == "GESTOR")
                    liquidation_offer_evidence.append({"text": clause.strip(), "speaker_role": unit["speaker_role"],
                        "start": unit.get("start"), "end": unit.get("end"), "confirmed": confirmed,
                        "reason": "OFERTA_DIRECTA" if confirmed else "SALDO_E_INTENCION_PERSONAL" if owed_amount or personal_intent else "PREGUNTA_O_ENUNCIADO_SIN_ATRIBUCION"})
                    agent_liquidation_offer = agent_liquidation_offer or confirmed
        liquidation_offer_review_required = bool(liquidation_offer_evidence and not agent_liquidation_offer)
        holder_liquidation_report = holder_liquidation_report or bool(re.search(
            r"\b(?:voy (?:a|al) liquidar|yo liquido|liquidare)\b"
            r"|\bya les habia dicho\b[^.!?]{0,100}\bliquid(?:o|ar)\b", normalized))
        liquidation_words = agent_liquidation_offer
        liquidation_attribution = (
            "GESTOR" if agent_liquidation_offer
            else "TITULAR/ANTECEDENTE" if holder_liquidation_report
            else "NO DETERMINADO"
        )
        restricted_liquidation_moras = {"1PV", "1FLP", "2PV", "3PV"}
        liquidation_forbidden = (
            mora in restricted_liquidation_moras
            and liquidation_words
        )

        mentions_amount = bool(
            re.search(
                r"(?:\$|pesos?\b|monto\b|cantidad\b|pago de\b)",
                normalized,
            )
        ) or bool(
            re.search(r"\b\d{2,}(?:[.,]\d{1,2})?\b", normalized)
        )

        # ---------------------------------------------------------
        # PAGO YA REALIZADO / CONFIRMACION DE PAGO
        # ---------------------------------------------------------
        # Si el cliente informa que el pago ya fue efectuado, no existe una
        # nueva promesa que requiera monto/fecha/compromiso de convenio.
        payment_already_made = any_of([
            "ya pague",
            "ya pagué",
            "ya hice el pago",
            "ya realice el pago",
            "ya realicé el pago",
            "pague ayer",
            "pagué ayer",
            "pague hoy",
            "pagué hoy",
            "hice el pago ayer",
            "hice el pago hoy",
            "ya se pago",
            "ya se pagó",
            "pago realizado",
            "pago efectuado",
            "ya realizo su pago",
            "ya realizó su pago",
            "realice mi pago",
            "realicé mi pago",
            "ya mande el comprobante",
            "ya mandé el comprobante",
            "ya mando el comprobante",
            "ya mandó el comprobante",
            "mande el comprobante",
            "mandé el comprobante",
            "mando el comprobante",
            "mandó el comprobante",
            "pague por transferencia",
            "pagué por transferencia",
            "ya lo habia hecho",
            "ya lo había hecho",
            "yo ya lo habia hecho",
            "yo ya lo había hecho",
            "yo mande el pago",
            "yo mandé el pago",
            "ya habia mandado el pago",
            "ya había mandado el pago",
            "ya se habia reflejado",
            "ya se había reflejado",
            "lo hizo el dia",
            "lo hizo el día",
            "realizo el pago el dia",
            "realizó el pago el día",
            "hizo el pago el dia",
            "hizo el pago el día",
        ]) or bool(
            # Tolerancia a errores comunes de ASR de Whisper:
            # "pagué" -> "pague" y "pagé" -> "page".
            re.search(
                # IMPORTANTE: no aceptar "pague" aislado. En español puede ser
                # subjuntivo/futuro ("si quieren que les pague") y no prueba
                # que exista un pago realizado. Se exige marcador temporal de
                # pasado/realización.
                r"\b(?:ya\s+pagu?e|pagu?e\s+(?:ayer|hoy))\b",
                normalized,
            )
        ) or bool(
            # Evidencia contextual de pago ya efectuado.
            # Se exige una referencia concreta a comprobante/captura + pago/transferencia
            # para no confundir una propuesta futura con un pago realizado.
            re.search(
                r"\b(?:ya\s+)?(?:mande|mando|envie|envio)\b.{0,80}"
                r"\b(?:comprobante|captura)\b",
                normalized,
            )
            and any_of(["pago", "transferencia", "deposito", "depósito"])
        )

        payment_registration = any_of([
            "ingresar este dato",
            "ingreso este dato",
            "registrar el pago",
            "registro el pago",
            "registrarlo en el sistema",
            "ingresarlo al sistema",
            "para que ya no le generen mas llamadas",
            "para que ya no le generen más llamadas",
            "ya no le generen mas llamadas",
            "ya no le generen más llamadas",
        ])

        # v3.5.8 · pago previo estructurado. Un pago histórico puede coexistir
        # con una NUEVA promesa en la misma llamada; no debe anularla.
        completed_payment_confirmation = completed_payment(text, segments)
        completed_payment_matches = list(re.finditer(
            r"\b(?:ya\s+(?:pague|page|hice|realice)|pague\s+(?:ayer|hoy)|"
            r"hice\s+el\s+pago|realice\s+(?:mi|el|un)\s+pago|"
            r"pague\s+(?:(?:\$?\s*)?\d{1,3}(?:[.,]\d{3})*|(?:un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|mil|cien|ciento|doscientos|trescientos|cuatrocientos|quinientos|seiscientos|setecientos|ochocientos|novecientos)(?:\s+y?\s*(?:\w+)){0,4})(?:\s*pesos?)?.{0,35}(?:hoy|el\s+dia\s+de\s+hoy)|"
            r"(?:lo|el\s+pago)\s+hizo\s+el\s+dia|"
            r"(?:realizo|hizo)\s+el\s+pago\s+el\s+dia|"
            r"ya\s+se\s+(?:hizo|pago)|pago\s+(?:realizado|efectuado)|"
            r"depositamos|ya (?:pudo|puedo|realizo|ha realizado|ha podido|hizo)\b[^?!]{0,95}\b(?:pago|pado)|"
            r"tengo\s+registrado\s+(?:un\s+)?reporte\s+de\s+pago)\b", normalized))
        # Extraer importes históricos solo de declaraciones ya acreditadas;
        # las instrucciones futuras no pueden aportar pagos ni complementos.
        completed_payment_matches = [m for m in completed_payment_matches if any(
            u["text_start"] < m.end() and u["text_end"] > m.start()
            for u in completed_payment_confirmation["evidence"])]
        additional_payment_starts = set()
        for unit in completed_payment_confirmation["evidence"]:
            start, end = unit["text_start"], unit["text_end"]
            if any(m.start() < end and m.end() > start for m in completed_payment_matches):
                continue
            fragment = normalized[start:end]
            match = re.compile(re.escape(fragment)).match(normalized, start) if fragment else None
            if match:
                completed_payment_matches.append(match)
                additional_payment_starts.add(start)
        completed_payment_matches.sort(key=lambda m: m.start())
        payment_already_made = bool(payment_already_made or completed_payment_matches)
        prior_payment_evidence = []
        prior_payment_amounts = []
        prior_payment_spans = []

        def _parse_prior_payment_number(token):
            raw = str(token or "").strip().replace("$", "").replace(" ", "")
            try:
                # 3,900 / 3.900 = miles; 3900 / 3900.00 = formato normal.
                if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", raw):
                    return float(re.sub(r"[.,]", "", raw))
                if "," in raw and "." in raw:
                    return float(raw.replace(",", ""))
                if "," in raw:
                    parts = raw.split(",")
                    if len(parts) == 2 and len(parts[1]) in (1, 2):
                        return float(raw.replace(",", "."))
                    return float(raw.replace(",", ""))
                return float(raw)
            except Exception:
                return None

        # v3.6.11: pago previo = evento, no coincidencia de regex. Las distintas frases
        # "ya pagué / hice mi pago / pago realizado" de un mismo tramo no deben sumar
        # dos veces la misma cantidad. Además 3,900 debe conservarse como 3900, no 900.
        for pm in completed_payment_matches:
            response_event = any(u.get("method") == "RESPUESTA_A_PAGO_REALIZADO" and
                                 u["text_start"] < pm.end() and u["text_end"] > pm.start()
                                 for u in completed_payment_confirmation["evidence"])
            a=pm.start() if response_event or pm.start() in additional_payment_starts else max(0, pm.start()-70)
            b=min(len(normalized), pm.end()+150)
            # Si el contexto se solapa ampliamente con un pago previo ya procesado,
            # se considera el mismo evento y no se vuelve a sumar.
            if any(not (b < sa or a > sb) for sa, sb in prior_payment_spans):
                continue
            ctx=normalized[a:b]
            prior_payment_evidence.append(ctx.strip())
            candidates=[]
            for am in re.finditer(r"(?:\$\s*)?(\d{1,3}(?:[.,]\d{3})+|\d{2,7}(?:[.,]\d{1,2})?)(?:\s*pesos?)?", ctx):
                val=_parse_prior_payment_number(am.group(1))
                if val is None or not (10 <= val <= 9999999):
                    continue
                # Excluir teléfono/WhatsApp/referencia/terminación cercanos.
                before=ctx[max(0,am.start()-55):am.start()]
                if re.search(r"(?:telefono|teléfono|whatsapp|referencia|terminacion|terminación|digitos|dígitos|folio)\s*(?:es|:|numero|número)?\s*$", before):
                    continue
                candidates.append((am.start(), val))
            # v3.6.18: pagos previos expresados con palabras ("pagué mil pesos").
            if True:
                word_map = {"un":1,"uno":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9,
                            "diez":10,"once":11,"doce":12,"trece":13,"catorce":14,"quince":15,"veinte":20,"treinta":30,"cuarenta":40,"cincuenta":50,
                            "cien":100,"ciento":100,"doscientos":200,"trescientos":300,"cuatrocientos":400,"quinientos":500,"seiscientos":600,"setecientos":700,"ochocientos":800,"novecientos":900}
                wm = re.search(r"\b((?:(?:un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|veinte|treinta|cuarenta|cincuenta|cien|ciento|doscientos|trescientos|cuatrocientos|quinientos|seiscientos|setecientos|ochocientos|novecientos|mil|y)\s*){1,7})pesos?\b", ctx)
                if wm:
                    total_w=0; current_w=0
                    for w in wm.group(1).split():
                        if w == "y": continue
                        if w == "mil": total_w += (current_w or 1)*1000; current_w=0
                        elif w in word_map: current_w += word_map[w]
                    val=float(total_w+current_w)
                    if val >= 10:
                        candidates.append((wm.start(), val))
                if response_event:
                    number_words = "|".join(sorted([*word_map, "mil", "y"], key=len, reverse=True))
                    for am in re.finditer(r"\b(?:por|de)\s+((?:(?:"+number_words+r")\s*){1,7})(?=pesos?\b|[.,!?]|$)", ctx):
                        total_w, current_w = 0, 0
                        for word in am[1].split():
                            if word == "mil":
                                total_w += (current_w or 1)*1000; current_w=0
                            elif word in word_map:
                                current_w += word_map[word]
                        if total_w+current_w >= 10:
                            candidates.append((am.start(1), float(total_w+current_w)))
            if candidates:
                # Prioriza la cantidad más próxima a la expresión de pago realizado.
                rel_pm=max(0, pm.start()-a)
                _, val=min(candidates, key=lambda x: abs(x[0]-rel_pm))
                prior_payment_amounts.append(val)
                prior_payment_spans.append((a,b))
        prior_payment_total = sum(prior_payment_amounts) if prior_payment_amounts else None

        promise_is_future = bool(promise_date and parsed_call_date and promise_date > parsed_call_date)
        prior_cue_in_promise = bool(re.search(
            r"\b(?:ya\s+(?:pague|page|hice|realice)|pague\s+(?:ayer|hoy)|(?:lo|el\s+pago)\s+hizo\s+el\s+dia|(?:realizo|hizo)\s+el\s+pago\s+el\s+dia|ya\s+se\s+(?:hizo|pago)|pago\s+(?:realizado|efectuado))\b",
            norm(promise_date_evidence)))
        commitment_confirmation = payment_commitment(text, segments)
        payment_already_made = completed_payment_confirmation["confirmed"]
        explicit_new_promise = bool(
            promise_date and promise_date_evidence and (promise_is_future or not prior_cue_in_promise)
            and commitment_confirmation["accepted"]
        )
        payment_confirmation_case = bool(payment_already_made and not explicit_new_promise)
        # Solo se elimina la fecha cuando la llamada es exclusivamente confirmación
        # de pago previo. Si después existe convenio/promesa explícita, se conserva.
        if payment_confirmation_case:
            promise_date = None
            promise_date_text = ""
            promise_date_evidence = ""

        confirms_payment_date = any_of([
            "pago manana",
            "pagar manana",
            "el lunes",
            "el martes",
            "el miercoles",
            "el jueves",
            "el viernes",
            "el sabado",
            "el domingo",
            "queda para el dia",
            "confirmo su compromiso",
            "confirmamos su pago",
            "fecha de pago",
        ]) or bool(
            re.search(
                r"\b(?:0?[1-9]|[12]\d|3[01])[/-](?:0?[1-9]|1[0-2])(?:[/-]\d{2,4})?\b",
                normalized,
            )
        )

        # Coherencia interna: una fecha de promesa extraída es evidencia
        # suficiente para no penalizar simultáneamente "sin fecha".
        if promise_date is not None and not payment_confirmation_case:
            confirms_payment_date = True

        confirms_commitment = bool(commitment_confirmation["accepted"])

        regularization_wording = any_of([
            "se pone al corriente",
            "regulariza su cuenta",
            "queda al corriente",
        ])
        monthly_due_wording = any_of([
            "cubre mensualidad vencida",
            "cubrira el pago vencido",
            "mensualidad vencida",
        ])
        partial_payment = any_of([
            "pago parcial",
            "abono parcial",
            "solo una parte",
            "pago incompleto",
        ])
        partial_explanation = any_of([
            "no regulariza la cuenta",
            "no queda al corriente",
            "solo disminuye el saldo",
            "sera solo un abono",
            "su pago solo es parcial",
        ])
        # En un pago parcial, "no liquida" es una aclaración, no una oferta de liquidación.
        if partial_payment and partial_explanation and re.search(r"\bno\s+(?:liquida|liquidar|queda\s+en\s+ceros)\b", normalized):
            liquidation_words = False
            liquidation_forbidden = False
            liquidation_attribution = "NO DETERMINADO"

        # RN007: en moras altas no debe presentarse la liquidación como
        # reactivación/recuperación del crédito. El manual no asigna aquí
        # una penalización PEN específica, por lo que obliga a REVISAR
        # sin inventar descuento de score.
        credit_reactivation_wording = any_of([
            "reactivar su credito",
            "reactiva su credito",
            "reactivacion del credito",
            "recuperar su credito",
            "recupera su credito",
            "volver a tener credito",
            "volver a utilizar su credito",
            "volver a usar su credito",
            "podra volver a comprar",
            "puede volver a comprar",
            "podria volver a comprar",
            "nuevamente tener credito",
            "adquirir nuevamente credito",
            "solicitar nuevamente credito",
            "volver a solicitar credito",
            "volver a adquirir su credito",
            "volver a adquirir el credito",
            "adquirir su credito",
        ])

        high_mora_credit_reactivation = bool(
            mora in {
                "3HN", "4PV", "5PV", "6PV",
                "C1", "C2", "C3", "C4", "B", "A",
            }
            and credit_reactivation_wording
        )

        # Contradicción de efecto: además de "se pone al corriente", detecta
        # cuando se habla de liquidar y posteriormente se explica que el pago
        # solo cubre vencido, deja saldo o mantiene mensualidades vigentes.
        non_liquidation_effect_wording = any_of([
            "se pone al corriente",
            "regulariza su cuenta",
            "queda al corriente",
            "cubre mensualidad vencida",
            "cubre el pago vencido",
            "solo cubre",
            "unicamente cubre",
            "únicamente cubre",
            "queda saldo",
            "le queda saldo",
            "resta saldo",
            "saldo restante",
            "mensualidad vigente",
            "mensualidades vigentes",
            "queda pendiente",
            "resta pendiente",
        ])

        # Control cualitativo para moras de liquidación.
        # Si la misma llamada presenta el pago como liquidación y también
        # como simple puesta al corriente/regularización, se manda a revisión
        # sin inventar una penalización que no exista en el Manual.
        high_mora_liquidation = mora in LIQUIDATION_MORAS
        liquidation_effect_asr_variant = bool(
            re.search(
                r"\b(?:"
                r"le\s+quidas?\s+al\s+(?:do)?vencido|"
                r"cubre\s+(?:lo\s+)?vencido|"
                r"queda\s+(?:el|al)\s+corriente|"
                r"queda\s+el\s+corriente\s+nada\s+mas|"
                r"paga\s+meses?\s+lo\s+que\s+le\s+reste"
                r")\b",
                normalized,
            )
        )

        # v3.5.0 · "liquidar saldo vencido" NO equivale a liquidar la cuenta.
        # En 4PV/5PV/6PV/C1-C4/A/B es correcto liquidar/cubrir el saldo vencido
        # para regularizar el atraso, siempre sujeto a monto y fechas aplicables.
        # Solo conservamos el conflicto cuando el lenguaje apunta a liquidación
        # TOTAL de la cuenta y simultáneamente se describe un efecto parcial.
        overdue_liquidation_assignments = {
            "4PV", "5PV", "6PV", "C1", "C2", "C3", "C4", "B", "A"
        }
        overdue_liquidation_wording = any_of([
            "liquidar saldo vencido",
            "liquida saldo vencido",
            "liquidacion del saldo vencido",
            "liquidar el saldo vencido",
            "liquida el saldo vencido",
            "liquidar vencido",
            "liquidar lo vencido",
            "cubrir saldo vencido",
            "cubre saldo vencido",
            "cubrir el saldo vencido",
            "cubre el saldo vencido",
            "cubrir lo vencido",
            "cubre lo vencido",
        ]) or bool(
            re.search(
                r"\b(?:liquid(?:ar|a|acion)|cubrir|cubre)\b.{0,35}\b(?:saldo\s+)?vencid[oa]s?\b",
                normalized,
            )
        )
        total_liquidation_wording = explicit_settlement_offer or any_of([
            "liquidacion total",
            "liquidar saldo total",
            "liquida saldo total",
            "liquidar el saldo total",
            "liquidar la cuenta",
            "liquida la cuenta",
            "liquidar su cuenta",
            "liquida su cuenta",
            "quedar en ceros",
            "queda en ceros",
            "saldo en cero",
            "cancelacion del adeudo",
        ])
        overdue_liquidation_valid_context = bool(
            mora in overdue_liquidation_assignments
            and overdue_liquidation_wording
            and not total_liquidation_wording
        )

        liquidation_regularization_conflict = bool(
            high_mora_liquidation
            and liquidation_words
            and not overdue_liquidation_valid_context
            and total_liquidation_wording
            and (
                non_liquidation_effect_wording
                or liquidation_effect_asr_variant
            )
        )

        visit_management_context = bool(re.search(
            r"\b(?:visita|domicilio|domiciliaria|diligencia|licenciad[oa]s?|abogad[oa]s?|recuperacion|recuperar)\b", normalized))
        prohibited_visit_wording = bool(re.search(
            r"\b(?:embarg\w*|retir\w*|quit\w*|recog\w*)\b.{0,45}\b(?:bienes|muebles|casa|vehiculo|propiedad)\b|"
            r"\b(?:bienes|muebles)\b.{0,45}\b(?:retir\w*|quit\w*|recog\w*|embarg\w*)\b", normalized))
        if mora in {"1PV", "2PV"}:
            visit_instruction = re.compile(
                r"\b(?:vamos a|voy a|se va a|se puede|procederemos a)\s+"
                r"(?:realizar|generar|presentar|efectuar|hacer|programar|agendar)\s+(?:una?\s+)?"
                r"(?:visita|diligencia|cobro)\b.{0,60}\b(?:domicilio|domiciliaria|casa|recuperacion)\b|"
                r"\b(?:se realizara|se programara|se generara|se presentara|realizaremos|programaremos|enviaremos)\s+(?:una?\s+)?"
                r"(?:visita|diligencia|cobro)\b.{0,60}\b(?:domicilio|domiciliaria|casa|recuperacion)\b|"
                r"\b(?:iremos|acudiremos)\s+a\s+(?:su\s+)?(?:domicilio|casa)\b")
            prohibited_visit_wording = prohibited_visit_wording or any(
                not re.search(r"\bno\s*$", normalized[max(0, m.start()-8):m.start()])
                for m in visit_instruction.finditer(normalized))
        # Una visita nunca confirma por sí misma una promesa de pago.
        visit_only_management = bool(visit_management_context and not promise_date_evidence)

        # ---------------------------------------------------------
        # PENALIZACIONES SEGÚN MATRIZ
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # TRATO, CONFRONTACION Y FINALIZACION DE LLAMADA
        # ---------------------------------------------------------
        # Estas reglas son conservadoras: solo atribuyen falta grave cuando
        # existe evidencia textual suficientemente explícita. En señales
        # ambiguas se solicita revisión, evitando culpar al gestor por el
        # comportamiento del titular o por un corte técnico.
        confrontation_patterns = [
            "mentirosa", "mentiroso",
            "sabes escuchar", "sabe escuchar", "aprende como funciona una tarjeta",
            "me esta poniendo muchas trabas", "si te molesta que te generen las llamadas",
            "si no quiere pagar es su problema",
            "usted fue quien se endeudo",
            "usted se endeudo",
            "pues pague",
            "no me importa",
            "es su problema",
            "haga lo que quiera",
            "a mi no me interesa",
            "escuchame tonta",
            "escucheme tonta",
            "eres tonta",
            "es tonta",
            "si eres una deudora",
            "eres una deudora",
            "usted es una deudora",
        ]
        confrontation_details = [dict(unit, phrase=phrase)
            for unit in sentence_evidence(text, context.get("_segments") or [])
            for phrase in confrontation_patterns if re.search(r"(?<!\w)" + re.escape(norm(phrase)) + r"(?!\w)", norm(unit["text"]))]
        confrontation_evidence = list(dict.fromkeys(e["phrase"] for e in confrontation_details))
        confrontation_review = any(e["speaker_role"] == "NO DETERMINADO" for e in confrontation_details)
        hostile_interlocutor_review = any(e["speaker_role"] in {"TITULAR", "TERCERO", "INTERLOCUTOR"} for e in confrontation_details)
        # Insultos/directivas hostiles explícitas: sin diarización no siempre es seguro
        # atribuir el hablante, pero nunca deben pasar silenciosamente como APROBADA.
        insult_patterns = [
            "tonta", "tonto", "idiota", "estupida", "estupido",
            "pendeja", "pendejo", "chingando", "chingada", "chingado",
            "pinche vieja", "pinche viejo", "pinche", "cabron", "cabrona",
            "mierda", "hijo de puta", "hija de puta", "vete a la chingada",
            "puta", "puto", "chingar", "chinga tu madre", "jodete", "vete al carajo",
            "quiero acostarme contigo", "quiero tener sexo contigo", "quiero cogerte",
        ]
        insult_evidence = [p for p in insult_patterns if re.search(r"(?<!\w)" + re.escape(norm(p)) + r"s?(?!\w)", normalized)]
        offensive_language_evidence = [dict(unit, phrase=phrase)
            for unit in evidence_units(text, context.get("_segments") or [])
            for phrase in insult_evidence if norm(phrase) in norm(unit["text"])]
        # No inferir autor de groserías desde texto sin diarización.
        # Se bloquea la aprobación en cualquier caso; la responsabilidad queda por verificar.
        reported_mistreatment_patterns = [
            "me trataron mal", "me han tratado mal", "me trato mal",
            "me maltrataron", "me han maltratado", "me insultaron",
            "me hablaron feo", "me faltaron al respeto", "me gritaron",
            "ustedes me tratan mal", "su compañera me trato mal",
            "su compañero me trato mal", "la gestora me trato mal",
            "me ofendieron", "me agredieron", "me estaban ofendiendo",
            "el gestor me insulto", "su gestor me agredio", "me hablo de forma grosera",
        ]
        mistreatment_report_evidence = [p for p in reported_mistreatment_patterns if norm(p) in normalized]
        gestor_confrontation = any(e["speaker_role"] == "GESTOR" for e in confrontation_details)
        confrontation_evidence = list(dict.fromkeys(confrontation_evidence + insult_evidence))

        # Confrontación contextual: una llamada puede ser confrontativa aun sin
        # insultos literales. Se exige una combinación conservadora de:
        # (1) resistencia/angustia reiterada del titular,
        # (2) presión o encuadre adversarial de cobranza y
        # (3) ausencia posterior de una reconducción conciliadora.
        # Esto cubre casos como "no tengo dinero" + "negativa" + insistencia
        # en el pago, sin convertir automáticamente la molestia del cliente en
        # una falta del gestor.
        holder_distress_patterns = [
            "no tengo dinero", "de donde quieren que lo saque",
            "de donde quieres que lo saque", "me tienen que esperar",
            "apenas si tengo para comer", "darle comer a mis hijos",
            "ya les dije que no tengo",
        ]
        pressure_patterns = [
            "negativa que presenta", "negativa que presenten",
            "se le esta solicitando su pago", "se les esta solicitando su pago",
            "no podemos seguir",
        ]
        holder_distress_evidence = [p for p in holder_distress_patterns if norm(p) in normalized]
        pressure_evidence = [p for p in pressure_patterns if norm(p) in normalized]

        interruption_patterns = [
            "dejeme hablar", "dejeme terminar", "me deja hablar",
            "no me interrumpa", "puedo hablar", "me permite hablar",
            "no me deja hablar",
        ]
        interruption_evidence = [p for p in interruption_patterns if norm(p) in normalized]
        repeated_interruption_review = len(interruption_evidence) >= 2 or any_of([
            "no me deja hablar", "usted no me deja hablar",
        ])

        explicit_agent_hangup = any_of([
            "le voy a colgar", "voy a colgar la llamada",
            "le cuelgo", "procedo a colgar", "terminare la llamada",
        ])
        explicit_holder_hangup = any_of([
            "voy a colgar", "ya le voy a colgar", "te voy a colgar",
            "yo le cuelgo",
        ]) and not explicit_agent_hangup

        segments = context.get("_segments") or []
        duration_seconds = float(context.get("_duration_seconds") or 0.0)
        last_segment_end = 0.0
        if segments:
            try:
                ends=[]
                for seg in segments:
                    if isinstance(seg, dict):
                        value=seg.get("end", seg.get("fin", 0.0))
                    else:
                        value=getattr(seg, "end", 0.0)
                    if value is not None:
                        ends.append(float(value or 0.0))
                last_segment_end=max(ends) if ends else 0.0
            except Exception:
                last_segment_end = 0.0
        # Si no llegaron segmentos utilizables, no convertir toda la duración en
        # "silencio final"; queda no determinado en lugar de falso abandono.
        trailing_silence = max(0.0, duration_seconds - last_segment_end) if duration_seconds and last_segment_end > 0 else 0.0
        asks_after_silence = bool(re.search(r"\b(?:bueno|oiga|hola|me escucha|sigue ahi)\b", normalized[-220:]))
        explicit_farewell = bool(re.search(r"\b(?:hasta luego|buen dia|buena tarde|gracias por su tiempo|que tenga buen dia|nos vemos)\b", normalized[-260:]))
        abandonment_review = trailing_silence >= 12.0 and asks_after_silence and not explicit_farewell

        if explicit_agent_hangup:
            call_end_result = "CUELGA GESTOR - GRAVE"
        elif abandonment_review:
            call_end_result = "SILENCIO FINAL - RESPONSABLE NO DETERMINADO"
        elif explicit_holder_hangup:
            call_end_result = "CUELGA TITULAR - PASA"
        elif explicit_farewell:
            call_end_result = "CIERRE NORMAL"
        elif trailing_silence >= 12.0:
            call_end_result = "NO DETERMINADO - REVISION"
        else:
            call_end_result = "CIERRE NORMAL/NO DETERMINADO"

        # Conciliación: se evalúa semánticamente; no exige una frase literal única.
        conciliation_patterns = [
            "comprendo lo que me indica", "entiendo lo que me indica",
            "entiendo que", "comprendo que", "permita verificar",
            "permitame verificar", "permita revisar", "permitame revisar",
            "vamos a aclarar", "vamos a revisarlo", "quiero ayudarle",
            "podemos revisarlo", "permita validar", "permitame validar",
        ]
        conciliation_evidence = [p for p in conciliation_patterns if norm(p) in normalized]
        conciliatory_management = bool(conciliation_evidence)

        contextual_confrontation = bool(
            len(holder_distress_evidence) >= 2
            and pressure_evidence
            and not conciliatory_management
        )
        if contextual_confrontation:
            # Señal de revisión, no prueba de agresión del gestor.
            confrontation_evidence = list(dict.fromkeys(
                confrontation_evidence
                + ["CONFRONTACION CONTEXTUAL / FALTA DE CONCILIACION"]
                + holder_distress_evidence[:3]
                + pressure_evidence[:3]
            ))

        # Sin diarización no atribuimos automáticamente el solapamiento al gestor.
        # Las peticiones reiteradas de poder hablar, sin una reconducción conciliadora,
        # quedan como tensión no controlada para revisión.
        uncontrolled_tension = bool(repeated_interruption_review and not conciliatory_management)
        if gestor_confrontation:
            treatment_state = "CONFRONTACION DEL GESTOR"
        elif uncontrolled_tension:
            treatment_state = "TENSION NO CONTROLADA / FALTA DE CONCILIACION"
        elif interruption_evidence or conciliatory_management:
            treatment_state = "TENSION CONTROLADA" if conciliatory_management else "SIN CONFRONTACION DETECTADA"
        else:
            treatment_state = "SIN CONFRONTACION DETECTADA"

        treatment_validation = {
            "offensive_language_evidence": offensive_language_evidence,
            "confrontation": treatment_state,
            "confrontation_details": confrontation_details,
            "confrontation_review_required": confrontation_review,
            "hostile_interlocutor_review_required": hostile_interlocutor_review,
            "confrontation_evidence": confrontation_evidence,
            "interruptions": "POSIBLES INTERRUPCIONES REITERADAS - REVISION" if repeated_interruption_review else ("INTERRUPCION OCASIONAL - SIN PENALIZACION" if interruption_evidence else "SIN INDICIOS"),
            "interruption_evidence": interruption_evidence,
            "conciliation": "CONCILIACION DETECTADA" if conciliatory_management else "SIN EVIDENCIA CLARA DE CONCILIACION",
            "conciliation_evidence": conciliation_evidence,
            "uncontrolled_tension": uncontrolled_tension,
            "contextual_confrontation": contextual_confrontation,
            "holder_distress_evidence": holder_distress_evidence,
            "pressure_evidence": pressure_evidence,
            "voice_tone_rule": "AGRESIVIDAD/CONFRONTACION CONFIRMADA DEL GESTOR = FALLA GRAVE BLOQUEANTE",
            "voice_tone_limit": "La transcripcion sola no atribuye tono acustico ni solapamiento de hablantes; señales ambiguas pasan a revision.",
        }
        call_end_validation = {
            "result": call_end_result,
            "trailing_silence_seconds": round(trailing_silence, 2),
            "explicit_agent_hangup": explicit_agent_hangup,
            "explicit_holder_hangup": explicit_holder_hangup,
            "abandonment_review": abandonment_review,
            "review_required": abandonment_review,
        }

        # ---------------------------------------------------------
        # CONVENIOS: COMPROBANTE WHATSAPP Y LUGARES DE PAGO
        # ---------------------------------------------------------
        # Regla operativa MRS/Bradescard. Solo se evalúa para estatus CONVENIO.
        # La detección de posible fraude exige contexto de instrucción de pago
        # atribuible al gestor; una mención aislada del titular no dispara alerta.
        is_convenio = excel_status == "CONVENIO"
        # Los lugares de pago también se revisan en llamadas de cobranza donde
        # el gestor instruye o solicita realizar un pago, aunque el estatus Excel
        # no sea literalmente CONVENIO (por ejemplo 1PV).

        whatsapp_receipt_patterns = [
            "comprobante por whatsapp", "comprobante de pago por whatsapp",
            "envie su comprobante por whatsapp", "envia su comprobante por whatsapp",
            "mande su comprobante por whatsapp", "manda su comprobante por whatsapp",
            "comparta su comprobante por whatsapp", "comparte su comprobante por whatsapp",
            "whatsapp para que comparta su comprobante", "whatsapp para que envie su comprobante",
            "linea de whatsapp", "linea de validacion",
        ]
        # V4: tolerancia a las formas reales observadas en Whisper.
        # Ejemplos del lote de prueba: "número de WhatsApp para que pueda mandar
        # su comprobante de pago" y "reporte de pago por WhatsApp".
        whatsapp_receipt_evidence = [p for p in whatsapp_receipt_patterns if norm(p) in normalized]

        whatsapp_receipt_regexes = [
            # comprobante / ticket / ficha + WhatsApp, en cualquier orden cercano
            r"\b(?:comprobante|ticket|ficha|captura)\b.{0,100}\b(?:whatsapp|whats app|guasap|wasap)\b",
            r"\b(?:whatsapp|whats app|guasap|wasap)\b.{0,140}\b(?:comprobante|ticket|ficha|captura)\b",
            # reporte de pago por WhatsApp (forma exacta encontrada en la llamada 4)
            r"\b(?:reporte|reportar|reporteme|rep[oó]rteme)\b.{0,60}\b(?:pago|deposito|abono)\b.{0,80}\b(?:whatsapp|whats app|guasap|wasap)\b",
            # número/línea de WhatsApp seguido de petición de mandar evidencia (llamada 3)
            r"\b(?:numero|linea)\b.{0,35}\b(?:whatsapp|whats app|guasap|wasap)\b.{0,140}\b(?:mandar|mande|enviar|envie|compartir|comparta)\b.{0,70}\b(?:comprobante|ticket|ficha|captura|reporte)\b",
            # petición de mandar comprobante seguida del canal WhatsApp
            r"\b(?:mandar|mande|enviar|envie|compartir|comparta)\b.{0,70}\b(?:comprobante|ticket|ficha|captura|reporte)\b.{0,140}\b(?:whatsapp|whats app|guasap|wasap)\b",
        ]
        for rx in whatsapp_receipt_regexes:
            m = re.search(rx, normalized, flags=re.IGNORECASE | re.DOTALL)
            if m:
                ev = re.sub(r"\s+", " ", m.group(0)).strip()
                if ev and ev not in whatsapp_receipt_evidence:
                    whatsapp_receipt_evidence.append(ev)

        requests_receipt_whatsapp = bool(whatsapp_receipt_evidence)

        authorized_payment_places = {
            "FARMACIAS DEL AHORRO": ["farmacias del ahorro", "farmacia del ahorro"],
            "7-ELEVEN": ["7 eleven", "seven eleven", "7-11", "7/11", "7 y 11"],
            "CHEDRAUI": ["chedraui"],
            "WOOLWORTH": ["woolworth"],
            "TIENDAS DEL SOL": ["tiendas del sol", "tienda del sol", "del sol"],
            "CIRCLE K": ["circle k", "circulo k"],
            "KIOSKO": ["kiosko", "kiosco"],
            "TIENDAS NETO": ["tiendas neto", "tienda neto", "neto"],
            "ABARREY": ["abarrey", "abarrey"],
            "7/24 MIX": ["7 24 mix", "7/24 mix", "724 mix"],
            "FARMACIAS YZA": ["farmacias yza", "farmacia yza"],
            "FARMACIAS ROMA": ["farmacias roma", "farmacia roma"],
            "TIENDAS 3B": ["tiendas 3b", "tienda 3b"],
            "TIENDAS SIX": ["tiendas six", "tienda six", "tiendas 6", "tienda 6"],
            # IMPORTANTE: mencionar solamente el banco NO acredita un lugar de pago
            # autorizado. Para bancos se exige el convenio/servicio correcto.
            "SANTANDER": ["convenio 3411", "convenio numero 3411", "convenio número 3411"],
            "BBVA": ["convenio 1042378", "convenio numero 1042378", "convenio número 1042378"],
            "BANAMEX": ["pago de servicio 4626", "servicio 4626", "convenio 4626"],
            # Tiendas de origen autorizadas (regla operativa MRS/Bradescard)
            "C&A": ["c&a", "c y a", "cy a", "ce y a"],
            "CUIDADO CON EL PERRO": ["cuidado con el perro"],
            "MALAYERBA": ["malayerba", "mala yerba"],
            "BODEGA AURRERA": ["bodega aurrera"],
            "MI BODEGA AURRERA": ["mi bodega aurrera"],
            "BODEGA AURRERA EXPRESS": ["bodega aurrera express", "bodega express"],
            "PROMODA": ["promoda"],
            "SUBURBIA": ["suburbia"],
        }
        place_evidence = payment_places(text, context.get("_segments") or [], authorized_payment_places)
        detected_payment_places = [e["place"] for e in place_evidence]
        payment_place_evidence = [e["text"] for e in place_evidence]

        # Transferencia desde cualquier banco hacia la cuenta autorizada de Bradescard
        # en Santander cuenta 014320655030560466. Se toleran espacios en ASR.
        digits_only = re.sub(r"\D", "", text or "")
        authorized_transfer_account = "014320655030560466" in digits_only
        transfer_wording = any_of([
            "transferencia", "transferir", "transferencia bancaria",
            "desde otro banco", "desde cualquier banco",
        ])
        transfer_beneficiary = any_of([
            "beneficiario bradescard mexico", "bradescard mexico s de rl",
            "bradescard mexico",
        ])
        transfer_reference = any_of([
            "16 digitos de su tarjeta", "16 digitos de la tarjeta",
            "dieciseis digitos de su tarjeta", "nombre completo",
        ])
        authorized_transfer = bool(transfer_wording and authorized_transfer_account)
        transfer_instruction_evidence = transfer_instructions(text, segments)
        authorized_transfer_instruction = any("014320655030560466" in re.sub(r"\D", "", e["text"])
                                              for e in transfer_instruction_evidence)
        authorized_transfer = bool(authorized_transfer and authorized_transfer_instruction)
        if authorized_transfer:
            detected_payment_places.append("TRANSFERENCIA A SANTANDER BRADESCARD")
            payment_place_evidence.append("transferencia a cuenta Santander autorizada")

        # Contextos explícitamente riesgosos. No se marca fraude por una mención aislada
        # de un banco/tienda: debe aparecer como instrucción de pago/depósito/transferencia.
        payment_instruction_context = bool(re.search(
            r"\b(?:pague|pagar|pago|deposite|depositar|deposito|transfiera|transferir|transferencia|puede pagar|realice el pago|haga el pago)\b",
            normalized,
        ))
        unauthorized_patterns = [
            "cuenta personal", "cuenta del gestor", "cuenta de la gestora",
            "cuenta del asesor", "cuenta de la asesora", "cuenta de mrs",
            "cuenta del despacho", "deposito a nombre del gestor",
            "deposito a nombre de la gestora", "deposito a un tercero",
            "pago en efectivo al gestor", "pago en efectivo a la gestora",
            "pago en efectivo al despacho", "spei a cuenta personal",
        ]
        unauthorized_payment_evidence = [p for p in unauthorized_patterns if norm(p) in normalized]

        # Bancos: no basta mencionar BBVA/Bancomer, Santander o Banamex.
        # Debe darse el convenio autorizado. Si el gestor presenta una numeración
        # como "cuenta" para depositar/pagar en esos bancos y no corresponde al
        # convenio autorizado, se considera método/dato bancario no autorizado.
        bank_variants = {
            "BBVA": ["bbva", "bancomer", "vancomer", "van comer", "banco bancomer", "banco en ver"],
            "SANTANDER": ["santander"],
            "BANAMEX": ["banamex", "citibanamex", "citi banamex"],
        }
        bank_authorized_tokens = {
            "BBVA": "1042378",
            "SANTANDER": "3411",
            "BANAMEX": "4626",
        }
        bank_mentioned = {
            bank: any(norm(v) in normalized for v in variants)
            for bank, variants in bank_variants.items()
        }
        wrong_bank_data = wrong_bank_instructions(
            text, context.get("_segments") or [], bank_variants, bank_authorized_tokens,
            "014320655030560466")
        for entry in wrong_bank_data:
            unauthorized_payment_evidence.append(
                f"{entry['bank']}: instrucción explícita de pago a una cuenta/numeración no autorizada")

        unauthorized_payment_method = bool(
            payment_instruction_context and (unauthorized_payment_evidence or wrong_bank_data)
        )

        bank_destination_context = bool(re.search(
            r"\b(?:clabe|cuenta bancaria|numero de cuenta|cuenta de destino|cuenta personal)\b", normalized))
        new_transfer_discussion = future_transfer_discussion(text, segments)
        reported_transfer_only = bool(payment_confirmation_case and not transfer_instruction_evidence
                                      and not bank_destination_context and not new_transfer_discussion)
        transfer_data_review = bool(not unauthorized_payment_method and (
            (transfer_instruction_evidence and not authorized_transfer_instruction)
            or (transfer_wording and not authorized_transfer_account and payment_instruction_context
                and not reported_transfer_only and not only_negated_transfers(text))))

        convenio_payment_validation = {
            "applies": is_convenio,
            "requests_receipt_whatsapp": requests_receipt_whatsapp,
            "whatsapp_evidence": whatsapp_receipt_evidence,
            "authorized_places_detected": detected_payment_places,
            "authorized_places_count": len(set(detected_payment_places)),
            "payment_place_evidence": payment_place_evidence,
            "payment_place_details": place_evidence,
            "minimum_places_required": 2,
            "minimum_places_met": len(set(detected_payment_places)) >= 2,
            "unauthorized_payment_method": unauthorized_payment_method,
            "unauthorized_evidence": unauthorized_payment_evidence,
            "wrong_bank_data": wrong_bank_data,
            "bank_mentioned": bank_mentioned,
            "possible_fraud": unauthorized_payment_method,
            "transfer_detected": transfer_wording,
            "authorized_transfer_account_detected": authorized_transfer_account,
            "transfer_beneficiary_detected": transfer_beneficiary,
            "transfer_reference_detected": transfer_reference,
            "transfer_data_review": transfer_data_review,
            "transfer_instruction_evidence": transfer_instruction_evidence,
            "authorized_transfer_instruction_confirmed": authorized_transfer_instruction,
            "reported_transfer_only": reported_transfer_only,
            "future_transfer_discussion": new_transfer_discussion,
            "authorized_transfer_account": "014320655030560466",
            "authorized_transfer_bank": "Santander",
            "authorized_transfer_beneficiary": "Bradescard México S. de R.L.",
            "authorized_transfer_reference": "16 dígitos de la tarjeta y nombre completo",
        }

        # v3.6.16 · VALIDACIÓN DE TARJETA PARA PAGO.
        # Solo se valida cuando la llamada contiene una referencia explícita a tarjeta/
        # terminación. Los dígitos detectados aquí nunca participan como montos.
        expected_card_digits = re.sub(r"\D", "", str(context.get("numero_de_tarjeta") or ""))
        card_mentions = []
        # Terminación explícita: aceptar exactamente 4 dígitos cercanos.
        for cm in re.finditer(
            r"(?:terminacion|terminación|termina\s+en|ultimos?\s+(?:cuatro|4)\s+digitos?|"
            r"últimos?\s+(?:cuatro|4)\s+dígitos?).{0,25}?(\d{4})\b", normalized, re.I):
            card_mentions.append({"digits": cm.group(1), "evidence": cm.group(0).strip()})
        # Número completo: solo secuencias de 13 a 19 dígitos, con o sin espacios/guiones,
        # asociadas explícitamente a tarjeta o a la instrucción de 16 dígitos.
        for cm in re.finditer(
            r"(?:numero\s+de\s+(?:la\s+)?tarjeta|número\s+de\s+(?:la\s+)?tarjeta|"
            r"(?:los\s+)?16\s+digitos?(?:\s+de\s+(?:la\s+)?tarjeta)?|"
            r"dieciseis\s+digitos?(?:\s+de\s+(?:la\s+)?tarjeta)?).{0,25}?"
            r"([0-9](?:[0-9\s.\-]{11,30}[0-9]))", normalized, re.I):
            digits = re.sub(r"\D", "", cm.group(1) or "")
            if 13 <= len(digits) <= 19:
                card_mentions.append({"digits": digits, "evidence": cm.group(0).strip()})


        # v3.6.18: si Whisper deja 5-12 dígitos inmediatamente después de
        # "terminación/termina en", no recortamos cuatro dígitos y no declaramos
        # tarjeta incorrecta: la evidencia es ambigua y debe revisarse.
        ambiguous_card_mentions = []
        for cm in re.finditer(
            r"(?:terminacion|terminación|termina\s+en|ultimos?\s+(?:cuatro|4)\s+digitos?|últimos?\s+(?:cuatro|4)\s+dígitos?).{0,25}?(\d{5,12})\b",
            normalized, re.I):
            ambiguous_card_mentions.append({"digits": cm.group(1), "evidence": cm.group(0).strip()})

        card_validation = "NO SE PROPORCIONO TARJETA"
        card_validation_reason = "No se detectó un número/terminación de tarjeta proporcionado en la llamada."
        card_detected = ""
        card_evidence = ""
        if ambiguous_card_mentions:
            chosen = ambiguous_card_mentions[-1]
            card_detected = chosen["digits"]
            card_evidence = chosen["evidence"]
            card_validation = "REVISAR - NUMERO NO CONFIABLE"
            card_validation_reason = "Whisper detectó más de 4 dígitos en una terminación de tarjeta; no se declara discrepancia hasta revisión."
        elif card_mentions:
            # Priorizar la mención más larga y, a igualdad, la última de la llamada.
            chosen = max(enumerate(card_mentions), key=lambda x: (len(x[1]["digits"]), x[0]))[1]
            card_detected = chosen["digits"]
            card_evidence = chosen["evidence"]
            if not expected_card_digits:
                card_validation = "REVISAR - TARJETA SIN DATO DE ORIGEN"
                card_validation_reason = "Se detectó tarjeta/terminación en llamada, pero el Excel no contiene Número de Tarjeta para comparar."
            elif 13 <= len(card_detected) <= 19:
                if card_detected == expected_card_digits:
                    card_validation = "TARJETA CORRECTA"
                    card_validation_reason = "El número completo mencionado coincide con la tarjeta registrada en Excel."
                else:
                    card_validation = "TARJETA INCORRECTA"
                    card_validation_reason = "El número completo mencionado no coincide con la tarjeta registrada en Excel."
            elif len(card_detected) == 4:
                if expected_card_digits.endswith(card_detected):
                    card_validation = "TARJETA CORRECTA"
                    card_validation_reason = "La terminación mencionada coincide con la tarjeta registrada en Excel."
                else:
                    card_validation = "TARJETA INCORRECTA"
                    card_validation_reason = "La terminación mencionada no coincide con la tarjeta registrada en Excel."
            else:
                card_validation = "REVISAR - NUMERO NO CONFIABLE"
                card_validation_reason = "Se detectó una secuencia asociada a tarjeta, pero no tiene 4 dígitos de terminación ni longitud de tarjeta completa."

        # v3.6.19: secuencias de 8 grupos de dos dígitos en contexto de referencia.
        # Se conservan como evidencia independiente y no se convierten en montos.
        from app.services.payment_reference_validation import find_reference
        payment_reference_validation = find_reference(text, expected_card_digits)
        # Candidatos ASR: bloqueo preventivo a revisión, no fraude confirmado sin audio.
        if payment_reference_validation["incorrect"]:
            candidate = payment_reference_validation["incorrect"][0]
            card_detected = candidate["digits"]
            card_evidence = candidate["evidence"]
            card_validation = "REVISAR - REFERENCIA DISTINTA"
            card_validation_reason = "Referencia dictada diferente a tarjeta de Excel; verificar audio original."
        elif payment_reference_validation["ambiguous"]:
            card_validation = "REVISAR - NUMERO NO CONFIABLE"
            card_validation_reason = "Dictación de referencia incompleta o con repeticiones; no se inventan 16 dígitos. Verificar audio."
            card_evidence = payment_reference_validation["ambiguous"][0]["evidence"]
        elif payment_reference_validation["detected"]:
            candidate = payment_reference_validation["detected"][0]
            card_detected, card_evidence = candidate["digits"], candidate["evidence"]
            if len(expected_card_digits) != 16:
                card_validation = "REVISAR - TARJETA SIN DATO DE ORIGEN"
                card_validation_reason = "La referencia tiene 16 dígitos, pero falta una tarjeta Excel válida para cotejar."
            else:
                card_validation = "TARJETA CORRECTA"
                card_validation_reason = "Los 16 dígitos transcritos coinciden con Excel; no implica verificación acústica."


        card_validation_data = {
            "expected_card_last4": expected_card_digits[-4:] if len(expected_card_digits) >= 4 else "",
            "detected_card_digits": card_detected,
            "evidence": card_evidence,
            "result": card_validation,
            "reason": card_validation_reason,
        }


        penalties: List[Dict] = []
        critical_failures: List[Dict] = []
        penalty_total = 0

        if gestor_confrontation:
            add_penalty(
                "PEN_TRATO_CONFRONTACION", "Trato",
                "Se detectó lenguaje explícitamente confrontativo atribuible a la gestión; requiere revisión grave.",
                100, True, ["TRATO001"],
            )
        # Bloqueos independientes del puntaje: no confundir grosería del titular
        # con agresión confirmada del gestor.
        if insult_evidence:
            add_penalty(
                "PEN_GROSERIA_SIN_ATRIBUCION", "Trato",
                "Grosería detectada en conversación. Bloquea aprobación; verificar emisor en audio.",
                0, False, ["TRATO003"],
            )
        if any(e["speaker_role"] == "GESTOR" for e in offensive_language_evidence):
            add_penalty(
                "PEN_GROSERIA_GESTOR", "Trato",
                "Lenguaje ofensivo atribuido explícitamente al gestor en la transcripción; bloquea aprobación.",
                100, True, ["TRATO003"],
            )
        if mistreatment_report_evidence:
            add_penalty(
                "PEN_QUEJA_MALTRATO", "Trato",
                "El titular reporta maltrato. Bloquea aprobación hasta verificar la queja.",
                0, False, ["TRATO004"],
            )
        if repeated_interruption_review:
            add_penalty(
                "PEN_TRATO_INTERRUPCION", "Trato",
                "Se detectan posibles interrupciones reiteradas; sin diarización se envía a revisión y no se atribuye automáticamente agresión al gestor.",
                25, False, ["TRATO002"],
            )
        if explicit_agent_hangup:
            add_penalty(
                "PEN_CUELGA_GESTOR", "Finalización",
                "Se detecta evidencia explícita de que el gestor anuncia/finaliza la llamada; falta grave.",
                100, True, ["FIN001"],
            )
        if abandonment_review:
            add_penalty(
                "PEN_ABANDONO_GESTOR", "Finalización",
                "Silencio final prolongado; no confirma abandono del gestor. Revisar audio y quién dejó de responder.",
                0, False, ["FIN002"],
            )

        if not identifies_mrs:
            add_penalty(
                "PEN001",
                "Identificación",
                "No se detectó identificación como MRS.",
                20,
                False,
                ["LEG001", "FRA001", "RN001"],
            )

        if false_bradescard_identity:
            add_penalty(
                "PEN002",
                "Identificación",
                "El gestor parece identificarse como Bradescard y no como representante.",
                100,
                True,
                ["LEG005", "FP001", "FP002", "FP003"],
            )

        if unknown_debtor and not arco_process:
            add_penalty(
                "PEN_ARCO_OMISION", "Protección de Datos",
                "Interlocutor confirma desconocer al titular y no se detecta el proceso de derechos ARCO obligatorio.",
                100, True, ["ARCO001"],
            )

        protected_third_statuses = {
            "MENSAJE CON FAMILIAR",
            "MENSAJE CON TERCERO",
            "MENSAJE EN TRABAJO",
            "RECADO REF 1",
            "RECADO REF 2",
            "RECADO REF1",
            "RECADO REF2",
            "NO CONOCEN A DEUDOR",
        }
        # Excel identifies the expected workflow, not the actual person speaking.
        # In a recado, an unverified recipient remains protected; only positive
        # evidence that the speaker is the cardholder can override that assumption.
        expected_third_party = excel_status in protected_third_statuses
        observed_third_party = detected_status in protected_third_statuses
        is_third_party_contact = bool(observed_third_party or (expected_third_party and not titular))

        # No convertir automaticamente la etiqueta Excel en prueba de que
        # la persona que habla es un tercero. Si el interlocutor no esta
        # determinado, el riesgo exige REVISION, no una falta grave probada.
        # Confirmación contextual de un tercero aun cuando Whisper no transcriba
        # un parentesco: petición de comunicar con el titular seguida de ausencia,
        # o declaración explícita de que la persona es referencia del titular.
        third_party_dialogue = bool(
            re.search(r"\b(?:me (?:podria|puede) comunicar|se encuentra|esta (?:el|la) senor|busco (?:a|al))\b", normalized)
            and re.search(r"\b(?:no (?:esta|se encuentra)|no vive aqui|salio|no esta aqui)\b", normalized)
        )
        reference_recipient = bool(re.search(
            r"\b(?:lo|la|le) dejo como (?:numero de )?referencia|"
            r"\b(?:usted (?:es|esta) como (?:su )?referencia|"
            r"(?:su|el) numero (?:fue|esta) (?:registrado|dejado) como referencia)", normalized
        ))
        third_party_confirmed = bool(
            observed_third_party or family or third_party or work_contact
            or third_party_dialogue or reference_recipient
            or contact_type in ("TERCERO / FAMILIAR", "TERCERO / TRABAJO", "TERCERO", "NO CONOCEN A DEUDOR")
        )
        privacy_validation = assess_privacy(
            text, context.get("_segments") or [],
            third_party_confirmed=third_party_confirmed,
            expected_third_party=expected_third_party,
            titular=titular,
            legacy_financial=bool(financial_information or payment_reference_validation["detected"]),
        )
        uncertain_disclosure = privacy_validation["review_required"]
        if privacy_validation["confirmed_disclosure"]:
            add_penalty(
                "PEN003",
                "Protección de Datos",
                "Se divulgó a un tercero información de deuda, mora, negativa de pago, saldo o tarjeta; requiere bloqueo de aprobación.",
                100,
                True,
                ["LEG003", "LEG004", "RN019", "FP004", "FP005", "FP006"],
            )


        if liquidation_forbidden:
            add_penalty(
                "PEN004",
                "Negociación",
                f"Se detectó liquidación en asignación {mora}, donde no está permitida.",
                100,
                True,
                ["RN005", "RN006", "RM010", "FP007", "FP008", "FP009"],
            )

        requires_new_negotiation_validation = (
            is_convenio and not payment_confirmation_case
        )

        # v3.5.8 · trabajo de cobranza: si se contacta al TITULAR debe existir
        # intento real de negociación, salvo reporte de pago ya realizado que
        # cubra el mínimo (o cuyo monto no pueda determinarse con seguridad).
        negotiation_attempt = bool(
            explicit_settlement_offer
            or (promise_date_evidence and not payment_confirmation_case)
            or re.search(r"\b(?:cuanto\s+puede\s+pagar|que\s+cantidad\s+puede|"
                         r"que\s+dia\s+puede\s+pagar|cuando\s+puede\s+pagar|"
                         r"propuesta\s+de\s+pago|opcion\s+de\s+pago|convenio|"
                         r"reestructura|pago\s+minimo|liquidar|abono|parcialidad)\b", normalized)
        )
        try:
            minimum_for_attempt = float(str(context.get("pago_minimo") or "").replace(",", ""))
        except (TypeError, ValueError):
            minimum_for_attempt = None
        # v3.6.14: "cubre el mínimo" solo puede afirmarse cuando existen
        # AMBOS valores comparables. Si el monto previo o el mínimo no están
        # disponibles, el resultado debe permanecer indeterminado/False.
        prior_payment_covers_minimum = bool(
            payment_already_made
            and prior_payment_total is not None
            and minimum_for_attempt is not None
            and prior_payment_total + 0.009 >= minimum_for_attempt
        )
        missing_collection_attempt = bool(
            contact_type == "TITULAR"
            and not negotiation_attempt
            and not prior_payment_covers_minimum
        )
        if missing_collection_attempt:
            add_penalty(
                "PEN_SIN_INTENTO_NEGOCIACION", "Negociación",
                "Se contactó al titular y no se detectó intento real de negociación. Si existe pago previo insuficiente, debe gestionarse el restante.",
                15, False, ["COB001"],
            )

        # v3.6.11: un convenio de Excel que en realidad es SOLO confirmación de un pago
        # ya realizado no requiere volver a ofrecer lugares de pago. Sí debe pedirse
        # comprobante cuando corresponda, pero no se penaliza como nueva negociación.
        if is_convenio and (not payment_confirmation_case) and not requests_receipt_whatsapp:
            add_penalty(
                "PEN_CONV_WHATSAPP", "Cierre",
                "En convenio con nueva gestión de pago no se detectó solicitud del comprobante de pago por WhatsApp.",
                10, False, ["CONV001"],
            )
        if is_convenio and (not payment_confirmation_case) and len(set(detected_payment_places)) < 2:
            add_penalty(
                "PEN_CONV_LUGARES", "Negociación",
                f"En convenio con nueva gestión de pago se detectaron {len(set(detected_payment_places))} lugares/formas de pago autorizados; se requieren al menos 2.",
                20, False, ["CONV002"],
            )
        # CONV002: dos lugares obligatorios EXCLUSIVAMENTE en CONVENIO.
        # En otros estatus no se genera PEN_PAGO_SIN_LUGAR.
        if unauthorized_payment_method:
            add_penalty(
                "PEN_CONV_FRAUDE", "Seguridad / Fraude",
                "GRAVE - POSIBLE FRAUDE: el gestor proporciona un lugar, cuenta o método de pago no autorizado.",
                100, True, ["CONV003"],
            )
        if transfer_data_review:
            add_penalty(
                "PEN_CONV_TRANSFER_REV", "Seguridad / Fraude",
                "REVISAR - DATOS DE TRANSFERENCIA NO CONFIRMADOS: se menciona transferencia, pero no se confirmó con claridad la cuenta Santander autorizada.",
                0, False, ["CONV004"],
            )

        if requires_new_negotiation_validation and not confirms_payment_date:
            add_penalty(
                "PEN007",
                "Negociación",
                "No se detectó confirmación de fecha de pago.",
                20,
                False,
                ["RN004", "FRA006", "RM008"],
            )

        if requires_new_negotiation_validation and not mentions_amount:
            add_penalty(
                "PEN008",
                "Negociación",
                "No se detectó confirmación del monto negociado.",
                20,
                False,
                ["RL005", "RM008", "RM012"],
            )

        if requires_new_negotiation_validation and not confirms_commitment:
            add_penalty(
                "PEN009",
                "Cierre",
                "No se detectó confirmación clara del compromiso de pago.",
                10,
                False,
                ["RL011", "FRA006"],
            )

        if is_convenio and contact_type not in {"TITULAR", "CONTACTO NO DETERMINADO"}:
            add_penalty(
                "PEN010",
                "Protección de Datos",
                "Se detectó negociación con un interlocutor que no parece ser titular.",
                50,
                True,
                ["FRA003"],
            )

        threats = any_of([
            "lo vamos a embargar",
            "la vamos a embargar",
            "lo vamos a demandar",
            "la vamos a demandar",
            "va a ir a la carcel",
            "le vamos a quitar sus bienes",
            "le vamos a quitar su casa",
        ]) or prohibited_visit_wording
        if threats:
            add_penalty(
                "PEN012",
                "Respeto / Amenazas",
                "Se detectó una amenaza prohibida por el manual.",
                100,
                True,
                ["FP011", "FP012", "FP013", "FP014", "FP015"],
            )

        if partial_payment and not partial_explanation:
            add_penalty(
                "PEN015",
                "Negociación",
                "Se detectó pago parcial sin aclarar que no regulariza la cuenta.",
                30,
                False,
                ["RM003", "RM009", "RN025", "FRA007"],
            )

        # ---------------------------------------------------------
        # ESTATUS: evidencia de la conversación, no copiar el Excel.
        # Se preserva la identificación original de terceros/familiares.
        # ---------------------------------------------------------
        status_detection_confidence = "NO DETERMINADA"
        status_evidence = ""
        status_evidence_method = "SIN_EVIDENCIA"
        if contact_type == "TITULAR" and not detected_status:
            agreement_evidence = bool(re.search(
                r"\b(?:gener(?:o|amos|are|amos)\s+(?:su\s+|el\s+)?convenio|"
                r"su\s+convenio\s+quedaria|quedamos\s+en\s+(?:tres|dos|3|2)\s+pagos|"
                r"confirmo\s+(?:su\s+)?convenio)\b", normalized
            ))
            refusal_evidence = recipient_statement(text, segments,
                r"\b(?:no\s+voy\s+a\s+pagar|no\s+le\s+voy\s+a\s+pagar|"
                r"no\s+pienso\s+pagar|me\s+niego\s+a\s+pagar)\b")
            no_date_evidence = recipient_statement(text, segments,
                r"\b(?:no\s+se\s+cuando\s+(?:pueda|voy\s+a)\s+pagar|"
                r"no\s+puedo\s+(?:dar|confirmar)\s+(?:una\s+)?fecha|"
                r"no\s+tengo\s+fecha|lo\s+voy\s+a\s+revisar)\b")
            if (agreement_evidence or promise_date is not None) and confirms_commitment and not payment_confirmation_case:
                detected_status = "CONVENIO"
                status_detection_confidence = "ALTA"
                status_evidence = commitment_confirmation["evidence"]
                status_evidence_method = "COMPROMISO_ACEPTADO_CON_FECHA"
            elif refusal_evidence and not confirms_commitment:
                detected_status = "NEGATIVA DE PAGO"
                status_detection_confidence = "ALTA"
                status_evidence_method = "NEGATIVA_EXPLICITA_DEL_INTERLOCUTOR"
            elif (no_date_evidence or commitment_confirmation["declined"] or commitment_confirmation.get("conditional")) and not payment_confirmation_case and not explicit_new_promise and not confirms_commitment:
                detected_status = "NO DEFINE FECHA DE PAGO"
                status_detection_confidence = "ALTA"
                status_evidence = commitment_confirmation["evidence"]
                status_evidence_method = "SIN_COMPROMISO_FIRME_RESPUESTA_EXPLICITA"
            elif payment_confirmation_case and not confirms_commitment:
                detected_status = "PAGO REPORTADO / ACLARACION"
                status_detection_confidence = "MEDIA"
                status_evidence_method = "PAGO_ANTERIOR_REPORTADO"
        elif detected_status:
            status_detection_confidence = "ALTA" if contact_type == "NO CONOCEN A DEUDOR" else "MEDIA"

        # ---------------------------------------------------------
        # VALIDACIÓN ESPECÍFICA DEL ESTATUS EXCEL
        # ---------------------------------------------------------
        status_validation = {
            "excel_status": excel_status,
            "detected_status": detected_status,
            "contact_type": contact_type,
            "relationship": relationship,
            "matches": None,
            "valid": True,
            "reasons": [],
            "detection_confidence": status_detection_confidence,
            "evidence_method": status_evidence_method,
            "evidence": status_evidence,
        }

        if excel_status:
            if excel_status == "NO CONOCEN A DEUDOR":
                status_validation["matches"] = detected_status == "NO CONOCEN A DEUDOR"

                if not unknown_debtor:
                    status_validation["valid"] = False
                    status_validation["reasons"].append(
                        "El interlocutor no confirma que desconoce al titular."
                    )
                if family or third_party or work_contact:
                    status_validation["valid"] = False

                    if relationship:
                        status_validation["reasons"].append(
                            f"El interlocutor confirma conocer al titular y se identifica como {relationship.lower()}; "
                            "el estatus NO CONOCEN A DEUDOR no corresponde."
                        )
                    elif family:
                        status_validation["reasons"].append(
                            "El interlocutor confirma conocer al titular y se identifica como familiar; "
                            "el estatus NO CONOCEN A DEUDOR no corresponde."
                        )
                    elif work_contact:
                        status_validation["reasons"].append(
                            "El interlocutor confirma conocer al titular mediante un contacto de trabajo; "
                            "el estatus NO CONOCEN A DEUDOR no corresponde."
                        )
                    else:
                        status_validation["reasons"].append(
                            "El interlocutor confirma conocer al titular; "
                            "el estatus NO CONOCEN A DEUDOR no corresponde."
                        )
                if not arco_process:
                    status_validation["valid"] = False
                    status_validation["reasons"].append(
                        "No se detectó el proceso ARCO."
                    )
                if not line_tenure_confirmed:
                    status_validation["valid"] = False
                    status_validation["reasons"].append(
                        "No se detectó confirmación del tiempo que el interlocutor tiene con la línea."
                    )

                # Evidencia adicional del manual.
                status_validation["arco_process"] = arco_process
                status_validation["line_tenure_confirmed"] = line_tenure_confirmed
                status_validation["privacy_email"] = gives_privacy_email
                status_validation["ine_or_line_proof"] = asks_ine_or_line_proof
                if not asks_ine_or_line_proof:
                    status_validation["reasons"].append("No se detectó solicitud de identificación o comprobante de titularidad de línea.")
                if not gives_privacy_email:
                    status_validation["reasons"].append("No se detectó el correo de privacidad para derechos ARCO.")
                status_validation["valid"] = bool(no_conocen_valid)

            elif detected_status:
                status_validation["matches"] = canonical_excel_status == detected_status
                # RECADO REF1/REF2 exige familiar identificado Y recado real.
                # La sola relación familiar no prueba que se dejó el mensaje.
                if canonical_excel_status == "MENSAJE CON FAMILIAR" and status_validation["matches"]:
                    if not (recado_family_evidence and recado_real):
                        status_validation["valid"] = False
                        status_validation["review_required"] = True
                        status_validation["reasons"].append(
                            "Falta evidencia conjunta de familiar y recado efectivamente transmitido."
                        )
                if not status_validation["matches"]:
                    # No declarar MAL_DICTAMINADO con evidencia media/ambigua.
                    # La discrepancia se registra y se remite a revisión.
                    status_validation["valid"] = False
                    status_validation["review_required"] = status_detection_confidence != "ALTA"
                    status_validation["reasons"].append(
                        f"Estatus Excel ({excel_status}) distinto del detectado ({detected_status}); "
                        + ("evidencia alta." if status_detection_confidence == "ALTA" else "confirmar audio antes de declarar mal dictaminado.")
                    )

        if recado_applies:
            status_validation["recado_evidence"] = {
                "family_phrases": recado_family_evidence[:8],
                "message_transmitted": recado_transmitted,
                "callback_information": recado_callback,
                "recipient_declines": bool(recado_declines or recado_refusal),
                "recipient_acceptance_evidence": recado_recibido_explicito,
                "evidence": recado_assessment,
                "confirmed_recado": bool(recado_family_evidence and recado_real and not recado_unknown_explicit),
            }
            if not recado_family_evidence or not recado_real:
                status_validation["valid"] = False
                status_validation["review_required"] = True
                if not recado_family_evidence:
                    status_validation["reasons"].append("No se confirmó parentesco con el titular; verificar audio.")
                if not recado_real:
                    status_validation["reasons"].append("No se confirmó transmisión efectiva del recado; verificar audio.")
            if recado_family_evidence and recado_real and not recado_unknown_explicit:
                status_validation["matches"] = True
                status_validation["valid"] = True
                status_validation["review_required"] = False
                status_validation["reasons"] = []
                status_validation["detected_status"] = "MENSAJE CON FAMILIAR"
                status_validation["contact_type"] = "TERCERO / FAMILIAR"
                status_validation["relationship"] = relationship
                status_validation["detection_confidence"] = "MEDIA"

        # No interpretar falta de evidencia como coincidencia válida.
        # Con Excel y estatus no detectable: revisión, nunca mal dictaminado automático.
        if contact_type in {"TERCERO", "TERCERO / FAMILIAR", "TERCERO / TRABAJO"} and not recado_real:
            status_validation["valid"] = False
            status_validation["review_required"] = True
            status_validation["evidence_method"] = "TERCERO_SIN_RECADO_CONFIRMADO"
            status_validation["reasons"].append("Tercero identificado sin recado efectivamente confirmado; revisar conversación.")
        if excel_status and status_validation["matches"] is None:
            status_validation["valid"] = False
            status_validation["review_required"] = True
            status_validation["reasons"].append(
                "Estatus de Excel sin evidencia suficiente para confirmar coincidencia; revisar conversación."
            )

        # ---------------------------------------------------------
        # VALIDACIÓN DE NEGOCIACIÓN
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # v3.5.5 · VALIDACIÓN MATEMÁTICA DE SALDOS / MONTOS
        # ---------------------------------------------------------
        def parse_money_value(raw):
            try:
                if raw is None or str(raw).strip() == "":
                    return None
                value = str(raw).strip().replace("$", "").replace(" ", "")
                # Formato MX común: 5,400.00 / 5400 / 5400.00
                if "," in value and "." in value:
                    value = value.replace(",", "")
                elif "," in value:
                    parts = value.split(",")
                    if len(parts[-1]) in (1, 2):
                        value = value.replace(".", "").replace(",", ".")
                    else:
                        value = value.replace(",", "")
                elif "." in value:
                    # v3.6.11: separadores de miles producidos por ASR.
                    # 7.200 => 7200. También corrige el artefacto observado 7.2000 => 7200
                    # cuando Whisper agrega un cero final. Decimales de 1-2 posiciones se conservan.
                    parts = value.split(".")
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        frac = parts[1]
                        if len(frac) == 3:
                            value = parts[0] + frac
                        elif len(frac) == 4 and frac.endswith("0"):
                            value = parts[0] + frac[:3]
                return float(value)
            except Exception:
                return None

        def spanish_number_value(words):
            units = {"cero":0,"un":1,"uno":1,"una":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9,
                     "diez":10,"once":11,"doce":12,"trece":13,"catorce":14,"quince":15,"dieciseis":16,"diecisiete":17,"dieciocho":18,"diecinueve":19,
                     "veinte":20,"veintiuno":21,"veintidos":22,"veintitres":23,"veinticuatro":24,"veinticinco":25,"veintiseis":26,"veintisiete":27,"veintiocho":28,"veintinueve":29}
            tens = {"treinta":30,"cuarenta":40,"cincuenta":50,"sesenta":60,"setenta":70,"ochenta":80,"noventa":90}
            hundreds = {"cien":100,"ciento":100,"doscientos":200,"trescientos":300,"cuatrocientos":400,"quinientos":500,"seiscientos":600,"setecientos":700,"ochocientos":800,"novecientos":900}
            total=0; current=0; used=False
            for w in norm(words).split():
                if w == "y": continue
                if w in units: current += units[w]; used=True
                elif w in tens: current += tens[w]; used=True
                elif w in hundreds: current += hundreds[w]; used=True
                elif w in ("mil", "miles"):
                    total += (current or 1)*1000; current=0; used=True
                else: return None
            return float(total+current) if used else None

        def monetary_mentions(source):
            found=[]

            # v3.6.4: no convertir identificadores/referencias en dinero.
            # Ejemplo real: "los 16 dígitos de la tarjeta" NO son un pago de $16.
            # También protege terminaciones, teléfonos, convenios, cuentas y referencias.
            non_money_reference_re = re.compile(
                r"(?:digitos?|dígitos?|terminacion|terminación|folio|nip|codigo|código|"
                r"(?:numero|número)\s+(?:de\s+)?(?:tarjeta|cuenta|telefono|teléfono|referencia|convenio)|"
                r"(?:referencia|convenio|clabe|telefono|teléfono)\s*(?:numero|número|es|:)?)"
            )

            def is_non_money_reference(start, end, evidence):
                raw = str(evidence or "").lower()
                # Si el importe viene explícitamente acompañado de pesos o $, prevalece
                # como dinero, aun cuando en la oración también se mencione una tarjeta.
                if "$" in raw or "peso" in raw:
                    return False

                before = source[max(0, start-90):start].lower()
                after = source[end:min(len(source), end+90)].lower()

                # v3.6.11 · BLOQUEO ESTRUCTURAL DE IDENTIFICADORES.
                # No depende de que exista o no una palabra financiera cerca. Si la cifra
                # pertenece sintácticamente a terminación/tarjeta/referencia/teléfono,
                # jamás entra al conjunto de cantidades monetarias.
                direct_before = before[-70:]
                direct_after = after[:70]
                if re.search(
                    r"(?:terminacion|terminación|termina\s+en|ultimos?\s+(?:4|cuatro)\s+digitos?|"
                    r"(?:numero|número)\s+(?:de\s+)?(?:tarjeta|cuenta|telefono|teléfono|referencia|folio|convenio)|"
                    r"referencia|folio|clabe|telefono|teléfono|whatsapp)\s*(?:es|:|numero|número)?\s*$",
                    direct_before,
                ):
                    return True
                if re.match(r"^\s*(?:digitos?|dígitos?)\s+(?:de\s+)?(?:la\s+)?tarjeta\b", direct_after):
                    return True

                # Caso típico: "los 16 dígitos de la tarjeta".
                if re.search(r"\b(?:los\s+)?$", direct_before) and re.match(
                    r"^\s*(?:digitos?|dígitos?)\s+(?:de\s+)?(?:la\s+)?tarjeta\b",
                    direct_after,
                ):
                    return True

                nearby = (before + " " + after).lower()
                return bool(non_money_reference_re.search(nearby))

            # cifras seguidas de pesos o con signo de moneda
            # v3.6.4: el token monetario debe TERMINAR en dígito. Así una coma/punto
            # de puntuación (ej. "7," en una frase) no se incorpora como parte del monto.
            for m in re.finditer(r"(?:\$\s*)?(\d(?:[\d,.]*\d)?)(?:\s*pesos?)?", source):
                token=m.group(1)
                # Evita años, teléfonos y referencias largas.
                digits=re.sub(r"\D", "", token)
                if 1 <= len(digits) <= 7:
                    if is_non_money_reference(m.start(), m.end(), m.group(0)):
                        continue
                    val=parse_money_value(token)
                    if val is not None and val > 0:
                        found.append((m.start(),m.end(),val,m.group(0)))
            # v3.6.18 · ASR híbrido: "mil 216 pesos" = 1216, "dos mil 150" = 2150.
            hybrid_map={"un":1,"uno":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9}
            for m in re.finditer(r"\b(?:(un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)\s+)?mil\s+(\d{1,3})\s+pesos?\b", source):
                thousands=hybrid_map.get(m.group(1),1)
                val=float(thousands*1000+int(m.group(2)))
                found.append((m.start(),m.end(),val,m.group(0)))
            number_words=r"(?:un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|dieci\w+|veinti\w+|veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|doscientos|trescientos|cuatrocientos|quinientos|seiscientos|setecientos|ochocientos|novecientos|mil|miles|y)"
            for m in re.finditer(rf"\b({number_words}(?:\s+{number_words}){{0,7}})\s+pesos?\b", source):
                val=spanish_number_value(m.group(1))
                if val is not None and val > 0:
                    found.append((m.start(),m.end(),val,m.group(0)))
            # «mil 900 pesos» aporta 1900, no otros 900 adicionales.
            return sorted([m for m in found if not any(
                other[0] <= m[0] and other[1] >= m[1] and
                (other[0] < m[0] or other[1] > m[1]) for other in found)], key=lambda x:x[0])

        minimum_expected = parse_money_value(context.get("pago_minimo"))
        total_expected = parse_money_value(context.get("saldo_total"))
        source_norm = normalized
        money_mentions = monetary_mentions(source_norm)

        # v3.6.1 · NORMALIZACIÓN DE MILES DICTADOS POR ASR
        # Faster-Whisper puede escribir "4.2" cuando en la llamada se dice
        # "cuatro mil doscientos" / "cuatro dos" en contexto de cobranza.
        # Solo escalamos cuando el valor literal NO alcanza el mínimo, el valor x1000
        # sí cae dentro del rango financiero de la cuenta y no parece un precio con
        # centavos explícitos ($4.20 / 4.20 pesos). Esto evita multiplicar decimales reales.
        def normalize_asr_thousands(mention):
            start, end, value, evidence = mention
            raw = str(evidence or "").strip().lower()
            compact = raw.replace(" ", "")
            numeric = re.sub(r"[^0-9.,]", "", compact)
            if not numeric or minimum_expected is None or total_expected is None:
                return mention + (False, value)
            if value >= minimum_expected:
                return mention + (False, value)
            # No reinterpretar importes con signo $ ni la palabra pesos: suelen ser
            # cantidades decimales explícitas. La corrección está dirigida a ASR oral.
            if "$" in raw or "peso" in raw:
                return mention + (False, value)
            # 4.2 / 4,2 => 4200. También admite 4.08 => 4080 cuando el rango lo confirma.
            if not re.fullmatch(r"\d{1,2}[.,]\d{1,2}", numeric):
                return mention + (False, value)
            scaled = value * 1000.0
            if minimum_expected - 0.009 <= scaled <= total_expected + 0.009:
                return (start, end, scaled, evidence, True, value)
            return mention + (False, value)

        money_mentions = [normalize_asr_thousands(mm) for mm in money_mentions]
        data_inconsistency = bool(minimum_expected and total_expected and minimum_expected > total_expected)
        regularization_claim = bool(regularization_wording or non_liquidation_effect_wording or any_of([
            "con eso regulariza", "con eso regularizaria", "sale de cobranza", "salga de cobranza",
            "pone al corriente", "queda al corriente"
        ]))
        financial_claim = bool(regularization_claim or total_liquidation_wording or liquidation_words)

        # v3.5.9: SALDO INFORMADO != MONTO NEGOCIADO.
        # Un importe solo se considera negociado cuando está ligado a una acción de pago,
        # convenio, abono, parcialidad, regularización o liquidación. Una cifra que aparece
        # únicamente junto a "saldo" no confirma el monto de la negociación.
        negotiation_anchor_re = re.compile(
            r"\b(?:pagar|pague|paga|pago|abono|abonar|parcial|parcialidad|convenio|"
            r"propuesta|acuerdo|regulariza|regularizar|corriente|liquida|liquidar|liquidacion|"
            r"cubrir|cubre|finiquitar|finiquito|cantidad\s+de|monto\s+de|pago\s+minimo|minimo\s+que|mínimo\s+que)\b"
        )
        balance_anchor_re = re.compile(
            r"\b(?:saldo(?!\s+(?:pasado|anterior)\b)(?:\s+total|\s+pendiente)?|total\s+adeudado|adeudo\s+total)\b"
        )
        negotiation_positions = [m.start() for m in negotiation_anchor_re.finditer(source_norm)]
        balance_positions = [m.start() for m in balance_anchor_re.finditer(source_norm)]
        # v3.6.11: identificadores nunca son montos negociados. Esta protección se aplica
        # también en la fase de atribución, no solo al extraer cifras.
        identifier_anchor_re = re.compile(
            r"\b(?:terminacion|terminación|termina\s+en|ultimos?\s+(?:4|cuatro)\s+digitos?|"
            r"digitos?\s+de\s+la\s+tarjeta|dígitos?\s+de\s+la\s+tarjeta|"
            r"numero\s+de\s+tarjeta|número\s+de\s+tarjeta|referencia|folio|"
            r"telefono|teléfono|whatsapp|clabe|cuenta)\b"
        )
        identifier_positions = [m.start() for m in identifier_anchor_re.finditer(source_norm)]

        detected_claim_amount = None
        detected_claim_evidence = ""
        detected_amount_role = "NO DETERMINADO"
        detected_amount_raw = None
        amount_asr_normalized = False
        detected_balance_amount = None
        detected_balance_evidence = ""
        balance_amount_candidates = []
        amount_candidates = []

        def in_prior_payment_context(mm):
            # Ventana corta alrededor de la frase histórica. No reutilizar la
            # ventana amplia de extracción, porque puede abarcar una propuesta nueva.
            return any(max(0, pm.start()-45) <= mm[0] <= pm.end()+75 for pm in completed_payment_matches)

        for mm in money_mentions:
            # v3.6.11: si la cifra está inmediatamente precedida por una terminación,
            # referencia, tarjeta, teléfono, WhatsApp, convenio, etc., se descarta como
            # monto aunque exista una palabra "pago" cercana. Ej.: "terminación 1509".
            if explicit_new_promise and in_prior_payment_context(mm):
                continue

            prior_identifier = [pos for pos in identifier_positions if pos <= mm[0]]
            identifier_distance = (mm[0] - max(prior_identifier)) if prior_identifier else 10**9
            if identifier_distance <= 85 and not ("$" in str(mm[3]) or "peso" in str(mm[3]).lower()):
                continue

            # v3.6.5: atribución DIRECCIONAL. No usar la palabra "pago" que aparece
            # DESPUÉS de una cifra para reclasificar un saldo previo como monto negociado.
            # Caso real: "saldo pendiente de 7.200 pesos. 7.200, ok? ... el pago...".
            # Ambas menciones de 7.200 pertenecen al saldo informado.
            prior_pay = [pos for pos in negotiation_positions if pos <= mm[0]]
            prior_balance = [pos for pos in balance_positions if pos <= mm[0]]
            pay_distance = (mm[0] - max(prior_pay)) if prior_pay else 10**9
            balance_distance = (mm[0] - max(prior_balance)) if prior_balance else 10**9
            balance_intro = re.search(
                r"\b(?:saldo(?:\s+(?:total|pendiente|vencid[oa]))?|monto de atraso)"
                r"(?:\s+(?:por|la|cantidad|de|es|asciende|a)){0,7}\s*$",
                source_norm[max(0,mm[0]-110):mm[0]])

            # El saldo domina mientras siga siendo el contexto precedente más cercano.
            # Se amplía a 120 caracteres para cubrir repeticiones de confirmación
            # inmediatamente posteriores: "saldo ... 7.200. 7.200, ok?".
            if balance_intro or (balance_distance <= 120 and balance_distance <= pay_distance):
                balance_amount_candidates.append((balance_distance, mm))
                continue
            if pay_distance <= 120:
                # v3.6.11 · no basta con que exista la palabra "pago" hasta 120 caracteres
                # antes. Se puntúa el contexto LOCAL y se priorizan importes plausibles.
                # Esto evita que día/fecha/tienda/terminación desplacen al monto real.
                local_before = source_norm[max(0, mm[0]-70):mm[0]]
                local_after = source_norm[mm[1]:min(len(source_norm), mm[1]+55)]
                local = local_before + " " + str(mm[3]).lower() + " " + local_after
                evidence_raw = str(mm[3] or "").lower()
                strong_phrase = bool(re.search(
                    r"(?:pago|pagar|pague|abono|abonar|cubrir|cubre|liquidar|liquidacion|"
                    r"convenio|propuesta|acuerdo|cantidad|monto)\s+(?:de\s+)?(?:\$\s*)?$",
                    local_before[-45:],
                )) or bool(re.match(r"^\s*(?:pesos|para\s+(?:hoy|mañana|el\s+dia))\b", local_after))
                explicit_currency = ("$" in evidence_raw or "peso" in evidence_raw)
                in_expected_range = bool(
                    (minimum_expected is None or mm[2] + 0.009 >= minimum_expected) and
                    (total_expected is None or mm[2] <= total_expected + 0.009)
                )
                # Números típicos no monetarios: 7-Eleven / 7 11, horas y días sueltos.
                store_or_calendar = bool(re.search(
                    r"(?:7[\s-]*(?:eleven|11)|\b(?:dia|día|fecha|hora|horario|corte|terminacion|terminación)\b)",
                    local,
                )) and not explicit_currency
                if store_or_calendar:
                    continue

                # v3.6.14 · CARGOS/ANUALIDADES INFORMATIVOS != MONTO NEGOCIADO.
                # Ej.: "pago de 85 pesos al mes ... anualidad" explica un cargo
                # recurrente; no debe desplazar a la propuesta posterior de $800.
                recurring_charge_info = bool(re.search(
                    r"(?:anualidad|membresia|membresía|cargo\s+(?:mensual|anual)|"
                    r"(?:\d+|pesos?).{0,18}(?:al|por)\s+mes|cada\s+mes)",
                    local,
                ))
                recurring_commitment = bool(re.search(
                    r"(?:pagar|cubrir|abonar).{0,35}(?:hoy|mañana|antes\s+de|"
                    r"se\s+compromete|queda\s+en|acuerda|confirma)",
                    local,
                ))
                if recurring_charge_info and not recurring_commitment:
                    continue

                # v3.6.11 · DIFERENCIA/RESTANTE INFORMATIVO != NUEVO MONTO NEGOCIADO.
                # Frases como "te faltaron 20 pesos", "hay una diferencia de 85" o
                # "el remanente es 52" describen una diferencia de cuenta. Solo pasan
                # a monto negociado cuando, en el mismo contexto local, existe una acción
                # explícita de cubrir/pagar ESA diferencia como nuevo compromiso.
                informational_difference = bool(re.search(
                    r"(?:te\s+falt(?:a|an|aron)|le\s+falt(?:a|an|aron)|faltante|diferencia|"
                    r"restante|remanente|resto\s+por\s+cubrir)",
                    local,
                ))
                difference_commitment = bool(re.search(
                    r"(?:pagar|pague|paga|cubrir|cubra|abonar|abone)\s+(?:lo\s+que\s+)?"
                    r"(?:falta|faltante|diferencia|restante|remanente)|"
                    r"(?:faltante|diferencia|restante|remanente).{0,35}(?:hoy|mañana|antes\s+de|"
                    r"se\s+compromete|queda\s+en|acuerda|confirma)",
                    local,
                ))
                if informational_difference and not difference_commitment:
                    continue

                confidence = 0
                if strong_phrase: confidence += 4
                if explicit_currency: confidence += 4
                if in_expected_range: confidence += 5
                if pay_distance <= 45: confidence += 2
                # v3.6.14: privilegiar el importe de la propuesta/aceptación
                # concreta sobre importes históricos o explicativos.
                if re.search(r"(?:pago\s+minimo|minimo\s+que|mínimo\s+que|"
                             r"puede\s+realizar|serian|serían|pagar(?:ia|ía|ias|ías)?|"
                             r"confirmo|confirmó|confirma|quedaria|quedaría)", local):
                    confidence += 5
                if re.search(r"(?:confirm(?:o|ó|a)|queda(?:mos)?|entonces|de\s+acuerdo|ok|"
                             r"el\s+dia|el\s+día|hoy|mañana|sabado|sábado|viernes)", local):
                    confidence += 4
                if promise_date_evidence and str(mm[3]).lower() in norm(promise_date_evidence):
                    confidence += 7
                confidence += min(3, int((mm[0] / max(1, len(source_norm))) * 4))
                # Un monto por debajo del mínimo sin moneda/frase explícita es ambiguo:
                # no debe bloquear una llamada ni ganar sobre un monto plausible posterior.
                weak_below_min = bool(
                    minimum_expected is not None and mm[2] + 0.009 < minimum_expected and
                    not explicit_currency and not strong_phrase
                )
                if not weak_below_min and confidence >= 4:
                    amount_candidates.append((confidence, -pay_distance, mm))

        # v3.6.16 · NEGOCIACIÓN MULTIPAGO / PRIORIZACIÓN DEL COMPROMISO ACTUAL.
        multi_payment_amounts = []
        multi_payment_total = None
        multi_payment_detected = False
        if amount_candidates:
            ordered_candidates = sorted(amount_candidates, key=lambda x: x[2][0])
            seen_spans = set()
            for conf, negdist, mm in ordered_candidates:
                key = (mm[0], mm[1])
                if key in seen_spans:
                    continue
                seen_spans.add(key)
                val = float(mm[2])
                if val > 0 and (total_expected is None or val <= total_expected + 0.009):
                    multi_payment_amounts.append(val)

            sequence_wording = bool(re.search(
                r"\b(?:pago\s+inicial|primer\s+pago|segundo\s+pago|tercer\s+pago|"
                r"(?:dos|tres|2|3)\s+pagos|pagos?\s+(?:semanales|quincenales)|"
                r"hoy.{0,80}(?:mañana|manana|(?:el\s+)?dia\s+\d{1,2})|"
                r"(?:dia|día)\s+\d{1,2}.{0,80}(?:dia|día)\s+\d{1,2})\b",
                source_norm))
            distinct = []
            for v in multi_payment_amounts:
                if not any(abs(v-u) < 0.01 for u in distinct):
                    distinct.append(v)
            if minimum_expected is not None and sequence_wording and len(distinct) >= 2:
                total_multi = sum(distinct)
                if total_multi + 0.009 >= minimum_expected and (total_expected is None or total_multi <= total_expected + 0.009):
                    multi_payment_detected = True
                    multi_payment_amounts = distinct
                    multi_payment_total = total_multi

            # v3.6.18 · PAGO PREVIO + COMPLEMENTO FUTURO.
            # Caso: "ya pagué 1000 hoy" + "1216 mañana para regularizar".
            # El pago ya realizado no debe competir como una nueva promesa, pero sí
            # debe sumarse al complemento comprometido para validar la regularización.
            if (minimum_expected is not None and not multi_payment_detected
                    and prior_payment_total is not None and prior_payment_total > 0
                    and payment_already_made):
                future_candidates = []
                for x in amount_candidates:
                    val = float(x[2][2])
                    if val <= 0:
                        continue
                    # Evita volver a sumar el mismo pago histórico cuando el ASR lo
                    # repite durante la confirmación del comprobante.
                    if any(abs(val-u) < 0.01 for u in prior_payment_amounts):
                        local = source_norm[max(0, x[2][0]-65):min(len(source_norm), x[2][1]+80)]
                        if re.search(r"(?:dio|pago|pagó|pague|pagué).{0,30}(?:hoy|ayer|ya)|comprobante", local):
                            continue
                    future_candidates.append(x)
                if not future_candidates:
                    # El complemento puede haberse etiquetado antes como "restante"
                    # informativo. Si después queda ligado explícitamente a mañana/fecha
                    # y a pagar/cubrir/confirmar, se recupera como compromiso futuro.
                    last_prior_end = max((pm.end() for pm in completed_payment_matches), default=0)
                    for mm in money_mentions:
                        if mm[0] <= last_prior_end:
                            continue
                        local = source_norm[max(0,mm[0]-90):min(len(source_norm),mm[1]+110)]
                        if re.search(r"(?:mañana|manana|el\s+dia|el\s+día|a\s+mas\s+tardar|a\s+más\s+tardar)", local) and re.search(r"(?:pago|pagar|realiza|cubrir|daria|daría|confirm)", local):
                            if not any(abs(float(mm[2])-u) < 0.01 for u in prior_payment_amounts):
                                future_candidates.append((10,0,mm))
                if future_candidates:
                    # Preferir el compromiso futuro más cercano a mañana/fecha/restante.
                    viable_future = [x for x in future_candidates
                                       if float(prior_payment_total) + float(x[2][2]) + 0.009 >= minimum_expected
                                       and (total_expected is None or float(prior_payment_total) + float(x[2][2]) <= total_expected + 0.009)]
                    pool_future = viable_future or future_candidates
                    best_future = max(pool_future, key=lambda x: (x[0], x[2][0]))
                    complement = float(best_future[2][2])
                    combined = float(prior_payment_total) + complement
                    if (combined + 0.009 >= minimum_expected
                            and (total_expected is None or combined <= total_expected + 0.009)):
                        multi_payment_detected = True
                        multi_payment_amounts = [float(prior_payment_total), complement]
                        multi_payment_total = combined

            if minimum_expected is not None and not multi_payment_detected:
                valid_individual = [x for x in amount_candidates
                                    if x[2][2] + 0.009 >= minimum_expected
                                    and (total_expected is None or x[2][2] <= total_expected + 0.009)]
                if valid_individual:
                    # Una propuesta válida posterior no puede ser desplazada por un abono
                    # inicial/histórico menor. Se mantiene la de mayor confianza.
                    best_valid = max(valid_individual, key=lambda x: (x[0], x[2][0]))
                    amount_candidates.append((best_valid[0] + 20, best_valid[1], best_valid[2]))
        if balance_amount_candidates:
            _, balance_best = min(balance_amount_candidates, key=lambda x: x[0])
            detected_balance_amount = balance_best[2]
            detected_balance_evidence = balance_best[3]

        if amount_candidates:
            # Mayor confianza primero; a igualdad, el ancla de pago más cercana.
            _, _, best = max(amount_candidates, key=lambda x: (x[0], x[1]))
            detected_claim_amount = best[2]
            detected_claim_evidence = best[3]
            amount_asr_normalized = bool(best[4]) if len(best) > 4 else False
            detected_amount_raw = best[5] if len(best) > 5 else best[2]
            if partial_payment:
                detected_amount_role = "PAGO PARCIAL"
            elif total_liquidation_wording or liquidation_words:
                detected_amount_role = "LIQUIDACION"
            elif regularization_claim:
                detected_amount_role = "REGULARIZACION"
            else:
                detected_amount_role = "PAGO NEGOCIADO"
        recovered_amounts = validated_entries(text, segments, context.get("_amount_recovery"))
        if len(recovered_amounts) == 1:
            recovered = recovered_amounts[0]
            detected_claim_amount = float(recovered["amount"])
            detected_amount_raw = detected_claim_amount
            detected_claim_evidence = (
                f"ASR adicional {recovered['inicio']:g}–{recovered['fin']:g}s: "
                + " | ".join(a["texto"] for a in recovered["attempts"]))
            detected_amount_role = "OFERTA RECUPERADA ASR - REVISAR"
            amount_asr_normalized = False
        plan = installment_plan(source_norm, money_mentions)
        accepted_mentions = monetary_mentions(norm(commitment_confirmation["evidence"])) if confirms_commitment else []
        accepted_amounts = {float(m[2]) for m in accepted_mentions}
        if plan["amounts"] and accepted_amounts and not accepted_amounts.issubset(set(plan["amounts"])):
            plan["review_required"] = True
            plan["conflicts"].append({"accepted_amounts": sorted(accepted_amounts), "plan_amounts": plan["amounts"]})
        detected_balance_amount, detected_balance_evidence, plan, financial_review = apply_financial_review(
            context.get("_financial_source"), context.get("_financial_review"),
            detected_balance_amount, detected_balance_evidence, plan)
        if plan["amounts"]:
            multi_payment_detected = True
            multi_payment_amounts = plan["amounts"]
            multi_payment_total = plan["total"]
        elif confirms_commitment:
            if len(accepted_amounts) == 1:
                detected_claim_amount = next(iter(accepted_amounts))
                detected_claim_evidence = accepted_mentions[-1][3]
                detected_amount_raw = detected_claim_amount
                detected_amount_role = "PAGO NEGOCIADO"
                amount_asr_normalized = False
                multi_payment_detected = False
                multi_payment_amounts = []
                multi_payment_total = None

        # Una liquidación total en parcialidades debe cuadrar con el saldo total.
        # Para regularización por mínimo, el saldo total NO es el importe exigible.
        multi_payment_balance_mismatch = bool(
            multi_payment_detected and multi_payment_total is not None
            and total_expected is not None
            and (total_liquidation_wording or liquidation_words)
            and not (mora in LIQUIDATION_MORAS and minimum_expected is not None
                     and minimum_expected <= multi_payment_total <= total_expected)
            and abs(multi_payment_total - total_expected) > 0.01
        )
        if multi_payment_detected and multi_payment_total is not None:
            detected_claim_amount = multi_payment_total
            detected_claim_evidence = " + ".join(f"{v:g}" for v in multi_payment_amounts)
            detected_amount_raw = multi_payment_total
            amount_asr_normalized = False
            detected_amount_role = "NEGOCIACION MULTIPAGO"

        elif detected_balance_amount is not None and detected_claim_amount is None:
            # Existe dinero en la llamada, pero solo atribuible al saldo informado.
            detected_amount_role = "SALDO INFORMADO"
            detected_claim_evidence = detected_balance_evidence

        amount_validation = "NO APLICA"
        amount_reason = ""
        amount_invalid = False
        amount_review = False
        explicit_partial_exception = bool(partial_payment and partial_explanation)
        # Las aclaraciones negativas obligatorias ("no queda al corriente",
        # "no liquida") no deben convertirse ellas mismas en una afirmación positiva.
        positive_effect_for_partial = bool(re.search(
            r"(?<!no\s)(?:se\s+pone\s+al\s+corriente|queda\s+al\s+corriente|regulariza(?:r)?\s+(?:su\s+)?cuenta|liquida(?:r)?\s+(?:su\s+|la\s+)?cuenta|queda\s+en\s+ceros)",
            source_norm,
        ))

        balance_validation = "NO APLICA"
        balance_reason = ""
        if detected_balance_amount is not None and total_expected is not None:
            if detected_balance_amount > total_expected + 0.009:
                balance_validation = "SALDO INFORMADO INCORRECTO - EXCEDE SALDO TOTAL"
                balance_reason = (f"Saldo informado {detected_balance_amount:g} excede el saldo total de Excel "
                                  f"{total_expected:g} por {detected_balance_amount-total_expected:g}.")
            elif detected_balance_amount + 0.009 < total_expected:
                balance_validation = "SALDO INFORMADO DIFERENTE AL SALDO TOTAL"
                balance_reason = (f"Saldo informado {detected_balance_amount:g} difiere del saldo total de Excel "
                                  f"{total_expected:g} por {detected_balance_amount-total_expected:g}.")
            else:
                balance_validation = "SALDO INFORMADO CORRECTO"
                balance_reason = f"Saldo informado {detected_balance_amount:g} coincide con el saldo total de Excel {total_expected:g}."

        if data_inconsistency:
            amount_validation = "REVISAR - DATOS DE ORIGEN INCONSISTENTES"
            amount_reason = f"Pago mínimo ({minimum_expected:g}) mayor que saldo total ({total_expected:g}); revisar Excel/origen antes de penalizar."
            amount_review = True
        elif plan["review_required"]:
            amount_validation = "REVISAR - PARCIALIDADES CON IMPORTES CONTRADICTORIOS"
            amount_reason = "Se mencionan importes distintos para la misma parcialidad; confirmar el acuerdo final en audio."
            amount_review = True
        elif detected_claim_amount is not None and total_expected is not None and detected_claim_amount > total_expected + 0.009:
            amount_validation = "INVALIDA - MONTO EXCEDE SALDO TOTAL"
            amount_reason = f"Monto negociado {detected_claim_amount:g} excede el saldo total {total_expected:g}."
            amount_invalid = True
        elif (mora in LIQUIDATION_MORAS and total_liquidation_wording and detected_claim_amount is not None
              and (minimum_expected is None or total_expected is None)):
            amount_validation = "REVISAR - REFERENCIA FINANCIERA INCOMPLETA"
            amount_reason = "Para cotejar la liquidación por mora se requieren pago_minimo y saldo_total de origen."
            amount_review = True
        elif detected_claim_amount is not None and minimum_expected is not None and detected_claim_amount + 0.009 < minimum_expected:
            if explicit_partial_exception and not positive_effect_for_partial:
                amount_validation = "VALIDA - PAGO PARCIAL EXPLICITO"
                amount_reason = f"Monto parcial {detected_claim_amount:g} menor al mínimo {minimum_expected:g}; permitido únicamente como abono parcial sin afirmar regularización ni liquidación."
            else:
                # v3.6.18: un importe aislado por debajo del mínimo no se convierte
                # en falla financiera bloqueante si no quedó confirmada una promesa
                # (fecha/compromiso). En ese escenario puede ser saldo, antecedente,
                # abono previo o ASR ambiguo y se envía a revisión.
                if not confirms_payment_date or not confirms_commitment:
                    amount_validation = "REVISAR - MONTO MENOR AL MINIMO SIN COMPROMISO CONFIRMADO"
                    amount_reason = f"Se detectó {detected_claim_amount:g}, menor al mínimo {minimum_expected:g}, pero no hay fecha y compromiso suficientemente confirmados para declarar una negociación inválida."
                    amount_review = True
                else:
                    amount_validation = "INVALIDA - MONTO MENOR AL MINIMO"
                    amount_reason = f"Monto negociado {detected_claim_amount:g} menor al pago mínimo requerido {minimum_expected:g}. Solo se permite si se identifica y explica expresamente como pago parcial sin regularizar ni liquidar."
                    amount_invalid = True
        elif detected_claim_amount is not None:
            # El usuario aclara que pago_minimo es la referencia para liquidar
            # en 3HN–A; no exigir el saldo total ni otro dato de autorización.
            if mora in LIQUIDATION_MORAS and minimum_expected is not None and total_expected is not None:
                amount_validation = "VALIDA - MINIMO DE LIQUIDACION SEGUN MORA"
                amount_reason = (f"En {mora}, pago_minimo de Excel ({minimum_expected:g}) es la referencia de liquidación; "
                                 f"la oferta de {detected_claim_amount:g} cubre el mínimo sin exceder el saldo total.")
            elif total_liquidation_wording and mora_policy["mode"] == "MORA_NO_CONFIGURADA":
                amount_validation = "REVISAR - MORA SIN POLITICA DE LIQUIDACION"
                amount_reason = "No se conoce la mora para determinar si el mínimo permite liquidar o solo cubrir mensualidad vencida."
                amount_review = True
            elif total_liquidation_wording and total_expected is not None and detected_claim_amount + 0.009 < total_expected:
                discount_wording = any_of(["descuento", "bonificacion", "bonificación", "quita"])
                if discount_wording:
                    amount_validation = "REVISAR - DESCUENTO NO VERIFICABLE"
                    amount_reason = f"Se ofrece liquidación por {detected_claim_amount:g} frente a saldo total {total_expected:g}; requiere validar descuento autorizado."
                    amount_review = True
                else:
                    amount_validation = "INVALIDA - LIQUIDACION TOTAL INSUFICIENTE"
                    amount_reason = f"Monto negociado {detected_claim_amount:g} está dentro del rango mínimo-total, pero no cubre el saldo total {total_expected:g} para afirmar liquidación total."
                    amount_invalid = True
            else:
                amount_validation = "VALIDA"
                if minimum_expected is not None and total_expected is not None:
                    amount_reason = f"Monto negociado {detected_claim_amount:g} se encuentra entre el pago mínimo {minimum_expected:g} y el saldo total {total_expected:g}."
                else:
                    amount_reason = f"Monto negociado identificado: {detected_claim_amount:g}."
        elif detected_claim_amount is None and balance_validation.startswith("SALDO INFORMADO INCORRECTO"):
            # v3.6.11: un saldo mal informado es una inconsistencia de información,
            # no una NEGOCIACIÓN INVÁLIDA si no existe monto negociado confirmado.
            amount_validation = balance_validation
            amount_reason = balance_reason
            amount_review = True
        elif requires_new_negotiation_validation and money_mentions:
            amount_validation = "REVISAR - MONTO NEGOCIADO NO CONFIRMADO"
            amount_reason = "Se detectaron importes en la llamada, pero no fue posible atribuir ninguno a una propuesta/compromiso de pago. Mencionar el saldo total no confirma el monto negociado."
            amount_review = True
        elif financial_claim and (minimum_expected or total_expected):
            amount_validation = "REVISAR - MONTO NO ATRIBUIBLE"
            amount_reason = "Hay una afirmación de regularización/liquidación, pero no se pudo atribuir con seguridad un monto negociado a esa afirmación."
            amount_review = True

        # Una propuesta válida no acredita que un saldo informado diferente
        # sea correcto. La discrepancia requiere revisión, sin convertirla en
        # una falla grave automática ni ocultarla detrás del nuevo importe.
        if balance_validation == "SALDO INFORMADO DIFERENTE AL SALDO TOTAL" and not amount_invalid:
            amount_review = True
            amount_validation = "REVISAR - SALDO INFORMADO DIFERENTE"
            amount_reason = balance_reason
        if (not amount_invalid and detected_claim_amount is None and agent_statement(text, segments,
                r"\b(?:se le esta ofreciendo|le ofrecemos|le ofrezco) un descuento\b")):
            amount_review = True
            amount_validation = "REVISAR - IMPORTE DEL DESCUENTO NO CONFIRMADO"
            amount_reason = "Se ofrece un descuento, pero no se confirmó un importe atribuible a esa propuesta."

        schedule_dates = installment_dates(source_norm, lambda fragment:
            cls._extract_payment_promise_date_details(fragment, call_date)) if plan["amounts"] and not payment_confirmation_case else []
        if len(schedule_dates) >= 2:
            last_installment = max(schedule_dates, key=lambda item: item["date"])
            promise_date = date.fromisoformat(last_installment["date"])
            promise_date_text = last_installment["text"]
            promise_date_evidence = last_installment["evidence"]
        installment_window = (two_installment_window(schedule_dates, parsed_call_date, parsed_due_date,
                              second_anchor="FIRST_PAYMENT") if mora_policy["uses_cut"]
                              else {"applies": False, "valid": False, "reasons": []})
        if installment_window.get("first_payment_valid"):
            mora_policy["window_end"] = installment_window["second_window_end"]
            mora_policy["installment_exception_source"] = "Usuario: primero dentro de tres días; segundo hasta siete días desde el primero, sin exceder vencimiento"
        negotiation_validation = {
            "mora_payment_policy": mora_policy,
            "installment_dates": schedule_dates,
            "installment_window": installment_window,
            "assignment": mora,
            "assignment_date": assignment_date,
            "limit_date": limit_date,
            "due_date": due_date,
            "call_date": call_date,
            "cut_applied": cut_applied,
            "calculated_payment_date": calculated_payment_date.isoformat() if calculated_payment_date else None,
            "promise_date": promise_date.isoformat() if promise_date else None,
            "promise_date_text": promise_date_text,
            "promise_date_evidence": promise_date_evidence,
            "promise_date_confirmed_from_call": bool(promise_date and promise_date_evidence and confirms_commitment),
            "commitment_evidence": commitment_confirmation,
            "installment_validation": plan,
            "financial_review": financial_review,
            "date_rule": None,
            "date_effect": None,
            "is_negotiation": requires_new_negotiation_validation,
            "payment_already_made": payment_already_made,
            "completed_payment_evidence": completed_payment_confirmation,
            "prior_payment_evidence": prior_payment_evidence,
            "prior_payment_amounts": prior_payment_amounts,
            "prior_payment_total": prior_payment_total,
            "prior_payment_covers_minimum": prior_payment_covers_minimum,
            "remaining_minimum_required": (max(0.0, minimum_expected - prior_payment_total) if minimum_expected is not None and prior_payment_total is not None else None),
            "negotiation_attempt_detected": negotiation_attempt,
            "missing_collection_attempt_penalty": missing_collection_attempt,
            "visit_management_detected": visit_management_context,
            "prohibited_visit_wording": prohibited_visit_wording,
            "payment_registration_detected": payment_registration,
            "payment_confirmation_case": payment_confirmation_case,
            "liquidation_detected": liquidation_words,
            "liquidation_attribution": liquidation_attribution,
            "liquidation_offer_review_required": liquidation_offer_review_required,
            "liquidation_offer_evidence": liquidation_offer_evidence,
            "holder_liquidation_report": holder_liquidation_report,
            "liquidation_allowed": mora not in restricted_liquidation_moras,
            "amount_confirmed": bool(detected_claim_amount is not None),
            "payment_date_confirmed": confirms_payment_date,
            "commitment_confirmed": confirms_commitment,
            "regularization_wording": regularization_wording,
            "monthly_due_wording": monthly_due_wording,
            "partial_payment": partial_payment,
            "partial_explanation": partial_explanation,
            "liquidation_regularization_conflict": liquidation_regularization_conflict,
            "overdue_liquidation_wording": overdue_liquidation_wording,
            "overdue_liquidation_valid_context": overdue_liquidation_valid_context,
            "total_liquidation_wording": total_liquidation_wording,
            "liquidation_effect_asr_variant": liquidation_effect_asr_variant,
            "credit_reactivation_wording": credit_reactivation_wording,
            "high_mora_credit_reactivation": high_mora_credit_reactivation,
            "monto_detectado": detected_claim_amount,
            "monto_transcrito": detected_amount_raw,
            "monto_normalizado_asr": bool(amount_asr_normalized),
            "evidencia_monto": detected_claim_evidence,
            "tipo_monto_detectado": detected_amount_role,
            "multipago_detectado": bool(multi_payment_detected),
            "montos_multipago": multi_payment_amounts if multi_payment_detected else [],
            "total_multipago": multi_payment_total,
            "saldo_informado_detectado": detected_balance_amount,
            "evidencia_saldo_informado": detected_balance_evidence,
            "validacion_saldo_informado": balance_validation,
            "motivo_validacion_saldo_informado": balance_reason,
            "pago_minimo_esperado": minimum_expected,
            "saldo_total_esperado": total_expected,
            "validacion_monto": amount_validation,
            "motivo_validacion_monto": amount_reason,
            "datos_saldo_inconsistentes": data_inconsistency,
            "amount_invalid": bool(amount_invalid),
            # v3.6.14: hard_invalid identifica exclusivamente una violación
            # financiera confirmada. Falta de fecha/monto o incertidumbre no son
            # por sí mismas NEGOCIACION_INVALIDA.
            "hard_invalid": False,
            "review_required": bool(amount_review),
            "valid": True,
            "reasons": [],
        }

        # v3.6.11 · una llamada que el propio motor NO identifica como nueva
        # negociación no puede terminar como NEGOCIACION_INVALIDA por un monto aislado.
        # En ese escenario el importe queda como evidencia informativa y, si hace falta,
        # pasa a REVISAR; la invalidez financiera solo bloquea una negociación real.
        if amount_invalid and not requires_new_negotiation_validation:
            amount_invalid = False
            amount_review = True
            negotiation_validation["amount_invalid"] = False
            negotiation_validation["review_required"] = True
            negotiation_validation["validacion_monto"] = "REVISAR - IMPORTE SIN NUEVA NEGOCIACION"
            negotiation_validation["motivo_validacion_monto"] = (
                "Se detectó un importe fuera del rango esperado, pero no se confirmó una nueva negociación. "
                "No corresponde clasificarlo como negociación inválida sin propuesta/compromiso de pago."
            )
            amount_reason = negotiation_validation["motivo_validacion_monto"]

        # v3.6.14 · Separación definitiva entre invalidez financiera y revisión.
        # hard_invalid solo se activa por una regla financiera confirmada.
        negotiation_validation["hard_invalid"] = bool(
            amount_invalid or liquidation_forbidden
        )

        if amount_invalid:
            negotiation_validation["valid"] = False
            negotiation_validation["reasons"].append(amount_reason)
        elif amount_review:
            negotiation_validation["valid"] = False
            negotiation_validation["reasons"].append(amount_reason)

        if liquidation_forbidden:
            negotiation_validation["valid"] = False
            negotiation_validation["reasons"].append(
                f"Liquidación prohibida para la asignación {mora}."
            )
        if liquidation_offer_review_required:
            negotiation_validation["valid"] = False
            negotiation_validation["review_required"] = True
            negotiation_validation["reasons"].append(
                "Posible liquidación total sin atribución u oferta confirmada; revisar audio.")
        if requires_new_negotiation_validation and detected_claim_amount is None:
            negotiation_validation["valid"] = False
            negotiation_validation["reasons"].append(
                "No se pudo confirmar un monto negociado atribuible a la propuesta/compromiso de pago."
            )
        if requires_new_negotiation_validation and not confirms_payment_date:
            negotiation_validation["valid"] = False
            negotiation_validation["reasons"].append(
                "No se pudo confirmar la fecha de pago."
            )
        # v3.6.11: la regla de pago parcial solo invalida una NUEVA negociación.
        # Un importe histórico/informativo o un pago ya realizado no debe activar
        # esta causa por sí solo.
        if requires_new_negotiation_validation and partial_payment and not partial_explanation:
            negotiation_validation["valid"] = False
            negotiation_validation["reasons"].append(
                "Pago parcial sin explicación obligatoria."
            )


        if liquidation_regularization_conflict:
            negotiation_validation["valid"] = False
            negotiation_validation["reasons"].append(
                "La llamada presenta el pago como liquidación y también con un "
                "efecto que deja saldo/cubre vencido/regulariza; requiere revisión."
            )

        if high_mora_credit_reactivation:
            negotiation_validation["valid"] = False
            negotiation_validation["reasons"].append(
                "RN007: en mora alta se detectó una referencia a reactivación, "
                "recuperación o nuevo uso del crédito; requiere revisión."
            )

        if (mora in LIQUIDATION_MORAS and not payment_confirmation_case
                and agent_statement(text, segments,
                    r"\b(?:se pone al corriente|queda al corriente|regulariza su cuenta|"
                    r"cubre (?:la |una |solo la )?mensualidad vencida)\b")):
            negotiation_validation["valid"] = False
            negotiation_validation["review_required"] = True
            negotiation_validation["reasons"].append(
                f"En {mora} el mínimo corresponde a liquidación; se describe un efecto de regularización o mensualidad vencida.")

        # ---------------------------------------------------------
        # RF001-RF014 · REGLAS DE FECHAS DEL MANUAL OPERATIVO
        # ---------------------------------------------------------
        rf_by_mora = {
            "1PV": "RF001",
            "1FLP": "RF002",
            "2PV": "RF003",
            "3PV": "RF004",
            "3HN": "RF005",
            "4PV": "RF006",
            "5PV": "RF007",
            "6PV": "RF008",
            "C1": "RF009",
            "C2": "RF010",
            "C3": "RF011",
            "C4": "RF012",
            "B": "RF013",
            "A": "RF014",
        }

        rf_id = rf_by_mora.get(mora)
        negotiation_validation["date_rule"] = rf_id

        if requires_new_negotiation_validation and confirms_commitment and mora_policy["mode"] != "MORA_NO_CONFIGURADA":
            if not parsed_call_date or not promise_date:
                negotiation_validation["valid"] = False
                negotiation_validation["reasons"].append("Faltan fecha de llamada o promesa interpretable para validar el plazo por mora.")
            if not parsed_due_date:
                negotiation_validation["valid"] = False
                negotiation_validation["reasons"].append("Falta el vencimiento de origen para validar la negociación.")
            if mora_policy["uses_cut"] and parsed_limit_date is None:
                negotiation_validation["valid"] = False
                negotiation_validation["reasons"].append("Falta corte válido para determinar el efecto de regularización o mensualidad vencida.")

        if requires_new_negotiation_validation and confirms_commitment and promise_date:
            window_end = cls._parse_context_date(mora_policy["window_end"])
            if parsed_call_date and promise_date < parsed_call_date:
                negotiation_validation["valid"] = False
                negotiation_validation["reasons"].append("La fecha de una nueva promesa es anterior a la llamada.")
            if mora_policy["mode"] == "MES_DE_LLAMADA":
                if not parsed_call_date or not window_end:
                    negotiation_validation["valid"] = False
                    negotiation_validation["reasons"].append("Falta la fecha de llamada para validar el mes de liquidación.")
                elif promise_date.year != parsed_call_date.year or promise_date.month != parsed_call_date.month:
                    negotiation_validation["valid"] = False
                    negotiation_validation["reasons"].append(
                        f"Liquidación {mora}: la promesa {promise_date.isoformat()} queda fuera del mes de la llamada; "
                        f"el vencimiento posterior no amplía el plazo {window_end.isoformat()}.")
            elif mora_policy["mode"] == "CORTE_Y_VENCIMIENTO":
                if installment_window["applies"]:
                    if not installment_window["valid"]:
                        negotiation_validation["valid"] = False
                        negotiation_validation["reasons"].extend(installment_window["reasons"])
                elif parsed_call_date and promise_date > parsed_call_date+timedelta(days=3):
                    negotiation_validation["valid"] = False
                    negotiation_validation["reasons"].append("RN004: la promesa excede los tres días posteriores a la llamada.")

        if requires_new_negotiation_validation and promise_date and parsed_due_date:
            if promise_date > parsed_due_date:
                negotiation_validation["valid"] = False
                negotiation_validation["date_effect"] = "NEGOCIACION INVALIDA"

                reason = (
                    f"{rf_id or 'RF'}: fecha de promesa "
                    f"{promise_date.isoformat()} posterior al vencimiento "
                    f"{parsed_due_date.isoformat()}."
                )
                negotiation_validation["reasons"].append(reason)

                if not confirms_commitment or plan["review_required"]:
                    negotiation_validation["reasons"].append("Confirmar aceptación del plan y sus fechas antes de atribuir falta grave.")
                else:
                    add_penalty(
                        "PEN005", "Fechas", reason, 100, True, [rf_id] if rf_id else [])

            elif mora in {"1PV", "2PV", "3PV"}:
                if parsed_limit_date and promise_date <= parsed_limit_date:
                    negotiation_validation["date_effect"] = "SE PONE AL CORRIENTE"

                elif parsed_limit_date and promise_date > parsed_limit_date:
                    negotiation_validation["date_effect"] = "CUBRE MENSUALIDAD VENCIDA"

                    if regularization_wording:
                        reason = (
                            f"PEN006/{rf_id}: la promesa es posterior a la fecha límite; "
                            "corresponde explicar que cubre mensualidad vencida, "
                            "no que se pone al corriente."
                        )
                        negotiation_validation["reasons"].append(reason)

                        add_penalty(
                            "PEN006",
                            "Negociación",
                            reason,
                            30,
                            False,
                            [rf_id] if rf_id else [],
                        )

            elif mora == "1FLP":
                negotiation_validation["date_effect"] = "CUBRE MENSUALIDAD VENCIDA"

            elif mora in {
                "3HN", "4PV", "5PV", "6PV",
                "C1", "C2", "C3", "C4", "B", "A",
            }:
                negotiation_validation["date_effect"] = (
                    "LIQUIDACION DENTRO DEL MES" if parsed_call_date and promise_date.year == parsed_call_date.year
                    and promise_date.month == parsed_call_date.month else "LIQUIDACION FUERA DEL MES")

        elif payment_confirmation_case and rf_id:
            # Pago ya realizado: no existe promesa futura que evaluar por RF.
            negotiation_validation["date_effect"] = "N/A"
            negotiation_validation["promise_date"] = None

        elif requires_new_negotiation_validation and rf_id and not promise_date:
            # Sin una fecha explícita de promesa no se inventa ni se penaliza RF/PEN005.
            negotiation_validation["date_effect"] = "FECHA DE PROMESA NO DETERMINADA"

        # ---------------------------------------------------------
        # SCORE Y RESULTADO FINAL
        # ---------------------------------------------------------
        if any(p["id"] == "PEN005" for p in penalties):
            negotiation_validation["hard_invalid"] = True
        score = max(0.0, 100.0 - float(penalty_total))
        # Evidencia de estatus/identidad no comprobada no equivale a 100% de calidad.
        # Penalización informativa, sin alterar la regla de bloqueo independiente.
        if not status_validation["valid"]:
            score = min(score, 79.0)

        # Las inconsistencias de estatus no necesariamente son -100 del score,
        # pero obligan a revisión porque la clasificación operativa es incorrecta.
        requires_review = (
            uncertain_disclosure
            or abandonment_review
            or contact_type == "CONTACTO NO DETERMINADO"
            or missing_collection_attempt
            or not status_validation["valid"]
            or not negotiation_validation["valid"]
            or card_validation in {"TARJETA INCORRECTA", "REVISAR - REFERENCIA DISTINTA", "REVISAR - TARJETA SIN DATO DE ORIGEN", "REVISAR - NUMERO NO CONFIABLE"}
        )

        # Una falta obligatoria de lugares de pago bloquea aprobación aunque
        # el puntaje sea >= 80. No altera la puntuación ni penalizaciones.
        mandatory_payment_places_missing = any(
            p.get("id") == "PEN_CONV_LUGARES"
            for p in penalties
        )
        if multi_payment_balance_mismatch:
            requires_review = True
        if insult_evidence or mistreatment_report_evidence or transfer_data_review or contextual_confrontation or confrontation_review or hostile_interlocutor_review:
            requires_review = True
        if uncertain_disclosure:
            status_validation["review_required"] = True
            status_validation["reasons"].append("Posible divulgación financiera: interlocutor no confirmado; requiere revisión del audio.")
        if critical_failures:
            final_result = "INCORRECTA"
        elif requires_review or mandatory_payment_places_missing:
            final_result = "REVISAR"
        elif score >= 80:
            final_result = "APROBADA"
        else:
            final_result = "NO_APROBADO_MENOR_80"

        observations: List[str] = []
        if card_validation == "TARJETA INCORRECTA":
            observations.append("La tarjeta/terminación indicada en la llamada no coincide con el Número de Tarjeta del Excel.")
        elif card_validation.startswith("REVISAR -"):
            observations.append(card_validation_reason)

        if payment_confirmation_case:
            observations.append(
                "Se detectó reporte de pago ya realizado; no se exige una nueva fecha, monto ni compromiso de convenio."
            )
            if payment_registration:
                observations.append(
                    "Se detectó que el gestor registra o da seguimiento al pago reportado."
                )

        if not represents_bradescard:
            observations.append(
                "No se detectó con claridad la frase de representación de Bradescard."
            )
        if not advisor_name:
            observations.append(
                "No se detectó con claridad nombre/apellido del gestor."
            )
        if contact_type == "CONTACTO NO DETERMINADO":
            observations.append(
                "No fue posible determinar con claridad el tipo de interlocutor."
            )
        observations.extend(status_validation["reasons"])
        observations.extend(negotiation_validation["reasons"])

        manual_rules = sorted({
            rule
            for penalty in penalties
            for rule in penalty.get("rule_ids", [])
        })

        checks = {
            "identifica_mrs": identifies_mrs,
            "identifica_mrs_explicito": identifies_mrs_explicit,
            "identifica_mrs_tolerancia_asr": identifies_mrs_asr,
            "variante_mrs_asr_detectada": mrs_asr_variant,
            "variante_mr_contextual_detectada": mrs_mr_context_variant,
            "contexto_presentacion_mrs": mrs_presentation_context,
            "representacion_bradescard": represents_bradescard,
            "identifica_gestor": advisor_name,
            "valida_interlocutor": relationship_validation or asks_person or titular,
            "deja_recado": leaves_message,
            "recontacto": callback,
            "no_conocen_confirmado": unknown_debtor,
            "proceso_arco": arco_process,
            "tiempo_con_linea": asks_line_tenure,
            "monto_confirmado": bool(detected_claim_amount is not None),
            "fecha_pago_confirmada": confirms_payment_date,
            "compromiso_confirmado": confirms_commitment,
            "liquidacion_detectada": liquidation_words,
            "conflicto_liquidacion_regularizacion": liquidation_regularization_conflict,
            "variante_asr_efecto_liquidacion": liquidation_effect_asr_variant,
            "reactivacion_credito_detectada": credit_reactivation_wording,
            "rn007_mora_alta_reactivacion": high_mora_credit_reactivation,
            "trato_sin_confrontacion": not gestor_confrontation,
            "interrupciones_reiteradas_revision": repeated_interruption_review,
            "finalizacion_llamada": call_end_result,
            "convenio_solicita_comprobante_whatsapp": requests_receipt_whatsapp if is_convenio else None,
            "convenio_lugares_pago_cantidad": len(set(detected_payment_places)) if is_convenio else None,
            "convenio_minimo_2_lugares": (len(set(detected_payment_places)) >= 2) if is_convenio else None,
            "convenio_posible_fraude": unauthorized_payment_method if is_convenio else None,
            "lugares_pago_detectados": len(set(detected_payment_places)),
            "lugares_pago_detalle": sorted(set(detected_payment_places)),
            "pago_sin_lugar_autorizado": bool(payment_instruction_context and len(set(detected_payment_places)) == 0),
            "queja_maltrato_detectada": mistreatment_report_evidence,
            "groseria_bloquea_aprobacion": bool(insult_evidence),
            "multipago_saldo_total_inconsistente": multi_payment_balance_mismatch,
            "insultos_detectados": insult_evidence,
        }

        blocks = {
            "identificacion": {
                "max_points": 20,
                "points": 20
                - (20 if any(p["id"] == "PEN001" for p in penalties) else 0),
            },
            "proteccion_datos": {
                "max_points": 30,
                "points": 0
                if any(p["id"] == "PEN003" for p in penalties)
                else 30,
            },
            "negociacion": {
                "max_points": 40,
                "points": max(
                    0,
                    40
                    - sum(
                        abs(p["points"])
                        for p in penalties
                        if p["category"] == "Negociación"
                    ),
                ),
            },
            "cierre": {
                "max_points": 10,
                "points": 0
                if any(p["id"] == "PEN009" for p in penalties)
                else 10,
            },
            "trato_no_confrontacion": {
                "max_points": 10,
                "points": 0 if any(p["category"] == "Trato" for p in penalties) else 10,
            },
            "finalizacion_llamada": {
                "max_points": 10,
                "points": 0 if any(p["category"] == "Finalización" for p in penalties) else 10,
            },
        }

        return {
            "score": round(score, 2),
            "checks": checks,
            "blocks": blocks,
            "contact_type": contact_type,
            "contact_validation": contact_confirmation,
            "detected_status": detected_status,
            "relationship": relationship,
            "observations": observations,
            "operational_context": {
                "estatus_grabacion": excel_status,
                "campana": campaign,
                "corte": context.get("corte"),
                "nombre_final": context.get("nombre_final"),
                "corte_aplicado": cut_applied,
                "fecha_pago_calculada": calculated_payment_date.isoformat() if calculated_payment_date else None,
                "fecha_asignacion": assignment_date,
                "fecha_limite": limit_date,
                "vencimiento": due_date,
                "asignacion": mora,
                "fecha": call_date,
                "gestor": context.get("gestor"),
                "supervisor": context.get("supervisor"),
                "numero_de_tarjeta": context.get("numero_de_tarjeta"),
                "pago_minimo": context.get("pago_minimo"),
                "saldo_total": context.get("saldo_total"),
            },
            "treatment_validation": treatment_validation,
            "call_end_validation": call_end_validation,
            "convenio_payment_validation": convenio_payment_validation,
            "card_validation": card_validation_data,
            "payment_reference_validation": payment_reference_validation,
            "privacy_validation": privacy_validation,
            "status_validation": status_validation,
            "negotiation_validation": negotiation_validation,
            "penalties": penalties,
            "critical_failures": critical_failures,
            "manual_rules": manual_rules,
            "final_result": final_result,
        }

    # =========================================================
    # CARPETA DE ANALYTICS
    # =========================================================

    @staticmethod
    def get_analytics_directory(
        project_path: str | Path,
    ) -> Path:
        """
        Devuelve la carpeta donde se guardan los análisis:

        proyecto/
            04_Reportes/
                Analytics/
        """

        project_directory = Path(
            project_path
        ).expanduser().resolve()

        analytics_directory = (
            project_directory
            / "04_Reportes"
            / "Analytics"
        )

        analytics_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return analytics_directory

    # =========================================================
    # GUARDAR ANÁLISIS
    # =========================================================

    @classmethod
    def save_analysis(
        cls,
        analysis: AnalyticsModel,
        project_path: str | Path,
    ) -> Path:
        """
        Guarda un AnalyticsModel en JSON.

        Si ya existe un análisis para la misma llamada,
        el archivo se actualiza.
        """

        if analysis is None:
            raise ValueError(
                "No se recibió un análisis para guardar."
            )

        analytics_directory = cls.get_analytics_directory(
            project_path
        )

        base_name = cls._get_analysis_base_name(
            analysis
        )

        output_path = (
            analytics_directory
            / f"{base_name}_analytics.json"
        )

        data = analysis.to_dict()

        data["analytics_file"] = str(
            output_path
        )

        data["saved_at"] = datetime.now().isoformat(
            timespec="seconds"
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
    # CARGAR ANÁLISIS
    # =========================================================

    @staticmethod
    def load_analysis(
        file_path: str | Path,
    ) -> AnalyticsModel:
        """
        Carga un análisis desde JSON.
        """

        path = Path(
            file_path
        ).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"No existe el archivo Analytics:\n{path}"
            )

        if not path.is_file():
            raise ValueError(
                f"La ruta no corresponde a un archivo:\n{path}"
            )

        if path.suffix.lower() != ".json":
            raise ValueError(
                "El archivo Analytics debe ser JSON."
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                "El archivo Analytics no contiene información válida."
            )

        return AnalyticsModel.from_dict(
            data
        )

    # =========================================================
    # LISTAR ANÁLISIS DEL PROYECTO
    # =========================================================

    @classmethod
    def load_project_analyses(
        cls,
        project_path: str | Path,
    ) -> List[AnalyticsModel]:
        """
        Carga todos los análisis guardados
        en el proyecto.
        """

        analytics_directory = cls.get_analytics_directory(
            project_path
        )

        analyses: List[AnalyticsModel] = []

        for json_file in sorted(
            analytics_directory.glob(
                "*_analytics.json"
            )
        ):

            try:
                analysis = cls.load_analysis(
                    json_file
                )

                analyses.append(
                    analysis
                )

            except Exception:
                continue

        return analyses

    # =========================================================
    # BUSCAR ANÁLISIS EXISTENTE
    # =========================================================

    @classmethod
    def find_analysis_for_transcription(
        cls,
        transcription: TranscriptionModel,
        project_path: str | Path,
    ) -> Optional[AnalyticsModel]:
        """
        Busca si ya existe un análisis guardado
        para una transcripción.
        """

        if transcription is None:
            return None

        analytics_directory = cls.get_analytics_directory(
            project_path
        )

        file_name = str(
            getattr(
                transcription,
                "file_name",
                "",
            )
            or ""
        )

        base_name = cls._sanitize_file_name(
            Path(
                file_name
            ).stem
        )

        if not base_name:
            return None

        analytics_file = (
            analytics_directory
            / f"{base_name}_analytics.json"
        )

        if not analytics_file.exists():
            return None

        try:
            return cls.load_analysis(
                analytics_file
            )

        except Exception:
            return None

    # =========================================================
    # CONTAR ANÁLISIS
    # =========================================================

    @classmethod
    def count_project_analyses(
        cls,
        project_path: str | Path,
    ) -> int:
        """
        Devuelve el número de análisis guardados.
        """

        analytics_directory = cls.get_analytics_directory(
            project_path
        )

        return len(
            list(
                analytics_directory.glob(
                    "*_analytics.json"
                )
            )
        )

    # =========================================================
    # NOMBRE DEL ARCHIVO
    # =========================================================

    @classmethod
    def _get_analysis_base_name(
        cls,
        analysis: AnalyticsModel,
    ) -> str:
        """
        Obtiene un nombre seguro para el JSON.
        """

        audio_file = str(
            analysis.audio_file
            or ""
        ).strip()

        if audio_file:
            base_name = Path(
                audio_file
            ).stem

        else:
            transcription_file = str(
                analysis.transcription_file
                or ""
            ).strip()

            if transcription_file:
                base_name = Path(
                    transcription_file
                ).stem
            else:
                base_name = "llamada"

        base_name = cls._sanitize_file_name(
            base_name
        )

        return (
            base_name
            or "llamada"
        )

    # =========================================================
    # NORMALIZACIÓN DE NOMBRE
    # =========================================================

    @staticmethod
    def _sanitize_file_name(
        value: str,
    ) -> str:
        """
        Limpia caracteres inválidos para Windows.
        """

        value = str(
            value
            or ""
        ).strip()

        value = re.sub(
            r'[<>:"/\\|?*]',
            "_",
            value,
        )

        value = re.sub(
            r"\s+",
            "_",
            value,
        )

        return value.strip(
            "._ "
        )

    # =========================================================
    # TEXTO
    # =========================================================

    @staticmethod
    def _normalize_spaces(
        text: str,
    ) -> str:
        """
        Elimina espacios repetidos.
        """

        return re.sub(
            r"\s+",
            " ",
            str(
                text
                or ""
            ),
        ).strip()

    @classmethod
    def _normalize_for_analysis(
        cls,
        text: str,
    ) -> str:
        """
        Normaliza texto para búsquedas de Analytics.

        Elimina diacríticos de forma segura para que expresiones como
        "Ya pagué ayer" se comparen como "ya pague ayer".
        """

        import unicodedata

        normalized = cls._normalize_spaces(
            str(text or "")
        ).lower()

        normalized = unicodedata.normalize(
            "NFKD",
            normalized,
        )

        normalized = "".join(
            char
            for char in normalized
            if not unicodedata.combining(char)
        )

        return normalized

    @classmethod
    def _tokenize(
        cls,
        text: str,
    ) -> List[str]:
        """
        Convierte el texto en palabras normalizadas.
        """

        normalized = cls._normalize_for_analysis(
            text
        )

        return re.findall(
            r"[a-z0-9]+",
            normalized,
        )
