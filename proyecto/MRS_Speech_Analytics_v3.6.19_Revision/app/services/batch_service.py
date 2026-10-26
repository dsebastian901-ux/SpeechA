import re
"""
============================================================
MRS Speech Analytics Professional
Servicio: Procesamiento por lotes
============================================================
"""

from pathlib import Path
from time import perf_counter
import shutil
import json
from datetime import datetime
from typing import Any, Dict, List

from app.services.whisper_service import whisper_service
from app.services.relation_service import RelationService
from app.services.analytics_service import AnalyticsService
from app.services.transcription_services import TranscriptionService
from app.services.batch_report_service import BatchReportService
from app.config.approval_rules import (
    MIN_APPROVAL_DURATION_SECONDS,
    MAX_APPROVAL_DURATION_SECONDS,
    MAX_DURATION_ACTION,
)


class BatchService:
    """
    Procesa una lista de audios secuencialmente.

    Estados:
    - pendiente
    - procesando
    - completado
    - error
    """

    def __init__(self):
        self.items: List[Dict[str, Any]] = []
        self.batch_elapsed_seconds = 0.0
        self.model_was_loaded_at_start = False
        self.relation_service = RelationService()
        self.relation_excel = None
        self.relation_enabled = False
        self.relation_validation = None
        self.last_report_path = None
        self.last_partial_report_path = None
        self.checkpoint_path = None
        self.partial_report_every = 10

    # =========================================================
    # CHECKPOINT / REANUDACION
    # =========================================================

    def _get_checkpoint_path(self, output_directory):
        output_dir = Path(output_directory).expanduser().resolve()
        project_path = output_dir.parent.parent
        state_dir = project_path / "05_Datos" / "batch_state"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / "batch_checkpoint.json"

    @staticmethod
    def _json_safe(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(k): BatchService._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [BatchService._json_safe(v) for v in value]
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass
        return str(value)

    def _save_checkpoint(self, output_directory, completed=False):
        if not output_directory:
            return None
        path = self._get_checkpoint_path(output_directory)
        self.checkpoint_path = str(path)
        payload = {
            "version": 1,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "completed": bool(completed),
            "output_directory": str(Path(output_directory).resolve()),
            "mode": "A" if self.has_relation_excel() else "B",
            "relation_excel": self.relation_excel if self.has_relation_excel() else None,
            "last_report_path": self.last_report_path,
            "batch_elapsed_seconds": self.batch_elapsed_seconds,
            "items": self._json_safe(self.items),
        }
        temp = path.with_suffix(".tmp")
        backup = path.with_name("batch_checkpoint_backup.json")

        # Escribe primero un archivo temporal completo.
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Valida el temporal antes de tocar el checkpoint principal.
        json.loads(temp.read_text(encoding="utf-8"))

        # Conserva la última copia válida del checkpoint principal.
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
                shutil.copy2(path, backup)
            except Exception:
                pass

        temp.replace(path)

        # Si todavía no existe respaldo, crea uno desde el checkpoint recién validado.
        if not backup.exists():
            try:
                shutil.copy2(path, backup)
            except Exception:
                pass

        return str(path)

    def find_checkpoint(self, output_directory):
        path = self._get_checkpoint_path(output_directory)
        backup = path.with_name("batch_checkpoint_backup.json")
        if not path.exists() and not backup.exists():
            return None

        payload = None
        used_path = path
        for candidate in (path, backup):
            if not candidate.exists():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
                used_path = candidate
                break
            except Exception:
                continue

        if payload is None:
            return None
        if payload.get("completed") or not payload.get("items"):
            return None
        items = payload["items"]
        completed = sum(i.get("status") == "completado" for i in items)
        errors = sum(i.get("status") == "error" for i in items)
        processing = sum(i.get("status") == "procesando" for i in items)
        pending = sum(i.get("status") == "pendiente" for i in items) + processing
        return {"path":str(used_path),"mode":payload.get("mode","B"),
                "relation_excel":payload.get("relation_excel"),"total":len(items),
                "completed":completed,"errors":errors,"pending":pending,
                "updated_at":payload.get("updated_at")}

    def resume_from_checkpoint(self, output_directory):
        path = self._get_checkpoint_path(output_directory)
        backup = path.with_name("batch_checkpoint_backup.json")

        payload = None
        used_path = path
        for candidate in (path, backup):
            if not candidate.exists():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
                used_path = candidate
                break
            except Exception:
                continue

        if payload is None:
            raise RuntimeError("El checkpoint principal y su respaldo no son válidos.")

        if payload.get("completed") or not payload.get("items"):
            raise RuntimeError("No existe un lote pendiente válido.")
        self.items = payload["items"]
        for item in self.items:
            if item.get("status") == "procesando":
                item["status"] = "pendiente"
                item["message"] = "Pendiente por reanudación"
        self.batch_elapsed_seconds = float(payload.get("batch_elapsed_seconds",0) or 0)
        self.last_report_path = payload.get("last_report_path")
        self.checkpoint_path = str(used_path)
        excel = payload.get("relation_excel")
        if payload.get("mode") == "A" and excel and Path(excel).exists():
            self.set_relation_excel(excel)
        else:
            self.clear_relation_excel()
        return self.get_summary()

    def discard_checkpoint(self, output_directory):
        path = self._get_checkpoint_path(output_directory)
        if path.exists():
            path.unlink()
        self.checkpoint_path = None

    # =========================================================
    # CARGAR AUDIOS
    # =========================================================

    def set_files(
        self,
        audio_files,
    ):
        """
        Agrega uno o varios audios a la cola.

        - Conserva los archivos ya cargados.
        - Permite agregar audios en varias selecciones.
        - Evita duplicados por ruta.
        - Si hay Excel de relación cargado, revalida toda la cola.
        """
        if self.items is None:
            self.items = []

        existing_paths = {
            str(Path(item.get("path", "")).expanduser().resolve()).lower()
            for item in self.items
            if item.get("path")
        }

        # v3.6.18 · evita copias automáticas tipo archivo_2.ogg cuando el
        # original archivo.ogg está en la misma selección. No afecta nombres cuyo
        # sufijo _2 sea el único archivo disponible.
        selected = {str(Path(a).expanduser().resolve()).lower() for a in audio_files}

        for audio in audio_files:
            path = Path(audio).expanduser().resolve()
            normalized_path = str(path).lower()

            if normalized_path in existing_paths:
                continue

            m_dup = re.match(r"^(.*)_(\d+)$", path.stem)
            if m_dup and int(m_dup.group(2)) >= 2:
                original = path.with_name(m_dup.group(1) + path.suffix)
                if str(original).lower() in selected or str(original).lower() in existing_paths:
                    continue

            self.items.append(
                {
                    "path": str(path),
                    "file_name": path.name,
                    "status": "pendiente",
                    "message": "",
                    "result": None,
                    "elapsed_seconds": 0.0,
                    "whisper_seconds": 0.0,
                    "analytics_seconds": 0.0,
                    "copy_seconds": 0.0,
                    "checkpoint_seconds": 0.0,
                    "relation": None,
                    "relation_status": "sin_validar",
                    "analytics": None,
                    "analytics_metadata": None,
                    "compliance_score": None,
                    "classification": None,
                    "classified_audio_path": None,
                    "copy_status": None,
                }
            )

            existing_paths.add(normalized_path)

        if self.has_relation_excel():
            self.validate_relation()


    # =========================================================
    # RELACION EXCEL (MODO OPCIONAL)
    # =========================================================

    def set_relation_excel(self, excel_path):
        path = Path(excel_path).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"No se encontro el Excel: {path}"
            )

        if path.suffix.lower() not in (".xlsx", ".xlsm"):
            raise ValueError(
                "El archivo de relacion debe ser .xlsx o .xlsm"
            )

        excel_summary = self.relation_service.load_excel(path)

        self.relation_excel = str(path)
        self.relation_enabled = True
        self.relation_validation = None

        if self.items:
            validation = self.validate_relation()
        else:
            validation = {
                "coincidencias": [],
                "total_coincidencias": 0,
                "audios_sin_relacion": [],
                "registros_sin_audio": [],
                "puntaje_minimo": self.relation_service.get_minimum_score(),
            }
            self.relation_validation = validation

        return {
            "excel": excel_summary,
            "validacion": validation,
        }

    def clear_relation_excel(self):
        self.relation_excel = None
        self.relation_enabled = False
        self.relation_validation = None

        for item in self.items:
            item["relation"] = None
            item["relation_status"] = "sin_validar"

    def get_relation_excel(self):
        return self.relation_excel

    def has_relation_excel(self):
        return bool(
            self.relation_enabled
            and self.relation_excel
        )

    def get_relation_service(self):
        return self.relation_service

    def get_relation_service_methods(self):
        return [
            name
            for name in dir(self.relation_service)
            if not name.startswith("_")
            and callable(getattr(self.relation_service, name, None))
        ]

    def validate_relation(self):
        if not self.has_relation_excel():
            raise RuntimeError(
                "No hay un Excel de relacion cargado."
            )

        audio_files = [
            item["path"]
            for item in self.items
        ]

        validation = self.relation_service.validate_audio_files(
            audio_files
        )

        for item in self.items:
            record = self.relation_service.find_record(
                item["path"]
            )

            if record is None:
                item["relation"] = None
                item["relation_status"] = "sin_relacion"
                item["message"] = "Audio sin relacion en Excel"
            else:
                item["relation"] = record.to_dict()
                item["relation_status"] = "relacionado"

                if item.get("status") == "pendiente":
                    item["message"] = "Relacion Excel validada"

        self.relation_validation = validation
        return validation

    def get_relation_validation(self):
        return self.relation_validation

    def get_relation_summary(self):
        validation = self.relation_validation or {}

        return {
            "modo_excel": self.has_relation_excel(),
            "archivo_excel": self.relation_excel,
            "puntaje_minimo": validation.get(
                "puntaje_minimo",
                self.relation_service.get_minimum_score(),
            ),
            "total_coincidencias": validation.get(
                "total_coincidencias",
                0,
            ),
            "audios_sin_relacion": len(
                validation.get(
                    "audios_sin_relacion",
                    [],
                )
            ),
            "registros_sin_audio": len(
                validation.get(
                    "registros_sin_audio",
                    [],
                )
            ),
        }

    # =========================================================
    # COPIA SEGURA DE AUDIOS CLASIFICADOS
    # =========================================================

    @staticmethod
    def _safe_copy_path(output_directory, filename):
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        source_name = Path(filename).name
        candidate = output_dir / source_name

        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        counter = 2

        while True:
            alternate = output_dir / f"{stem}_{counter}{suffix}"
            if not alternate.exists():
                return alternate
            counter += 1

    def _copy_classified_audio(self, item, record, classification, output_directory):
        if not output_directory:
            return None

        source = Path(item["path"])
        if not source.exists():
            raise FileNotFoundError(
                f"No existe el audio original para copiar: {source}"
            )

        # output_directory es la carpeta usada para las transcripciones.
        # La clasificación se crea junto a ella, dentro de su carpeta padre.
        base_directory = Path(output_directory).resolve().parent
        classified_root = base_directory / "Audios Clasificados"

        approved = bool(classification.get("aprobado"))
        category = str(classification.get("clasificacion") or "REVISAR").strip().upper()
        folder_map = {
            "APROBADO": "APROBADOS",
            "APROBADOS": "APROBADOS",
            "APROBADO_SIN_ETIQUETAR": "APROBADO_SIN_ETIQUETAR",
            "APROBADO_CON_EXCEPCION": "APROBADO_CON_EXCEPCION",
            "NO_APROBADO_MENOR_80": "NO_APROBADOS_MENOR_80",
            "MAL_DICTAMINADO": "MAL_DICTAMINADO",
            "NEGOCIACION_INVALIDA": "NEGOCIACION_INVALIDA",
            "FALLA_GRAVE": "FALLA_GRAVE",
            "REVISAR": "REVISAR",
        }
        destination_dir = classified_root / folder_map.get(category, "REVISAR")

        if approved:
            if self.has_relation_excel():
                if record is None:
                    raise RuntimeError(
                        "No se puede copiar como APROBADO un audio sin relacion Excel."
                    )
                filename = self.relation_service.build_output_filename(source, record)
            else:
                filename = source.name
        else:
            # Los no aprobados conservan el nombre original para auditoría.
            filename = source.name

        destination = self._safe_copy_path(
            destination_dir,
            filename,
        )

        shutil.copy2(source, destination)

        item["classified_audio_path"] = str(destination)
        item["copy_status"] = "copiado"

        return str(destination)

    # =========================================================
    # OBTENER ESTADO
    # =========================================================

    def get_items(self):
        return self.items

    # =========================================================
    # PROCESAR TODO
    # =========================================================

    def process_all(
        self,
        output_directory=None,
        progress_callback=None,
    ):
        total = len(self.items)

        results = []
        batch_started = perf_counter()
        previous_elapsed = float(self.batch_elapsed_seconds or 0.0)
        self._save_checkpoint(output_directory, completed=False)
        self.model_was_loaded_at_start = bool(
            getattr(whisper_service, "is_model_loaded", False)
        )

        for index, item in enumerate(
            self.items,
            start=1,
        ):
            if item.get("status") in ("completado", "error"):
                continue
            item["status"] = "procesando"
            item["message"] = ""
            item["elapsed_seconds"] = 0.0
            item["whisper_seconds"] = 0.0
            item["analytics_seconds"] = 0.0
            item["copy_seconds"] = 0.0
            item["checkpoint_seconds"] = 0.0
            item_started = perf_counter()

            if progress_callback:
                progress_callback(
                    index,
                    total,
                    item,
                )

            try:
                whisper_started = perf_counter()

                # RECUPERACIÓN:
                # Si ya existe un JSON válido de esta llamada, reutiliza la
                # transcripción y evita volver a ejecutar Whisper.
                recovered_json = None
                if output_directory:
                    candidate_json = (
                        Path(output_directory).expanduser().resolve()
                        / f"{Path(item['path']).stem}.json"
                    )
                    if candidate_json.exists():
                        try:
                            recovered_payload = json.loads(
                                candidate_json.read_text(encoding="utf-8")
                            )
                            recovered_audio = str(
                                recovered_payload.get("archivo") or ""
                            ).strip()
                            if (
                                recovered_audio
                                and Path(recovered_audio).stem.lower()
                                == Path(item["path"]).stem.lower()
                            ):
                                recovered_json = candidate_json
                        except Exception:
                            recovered_json = None

                if recovered_json is not None:
                    result = {
                        "ruta_json": str(recovered_json),
                        "json_path": str(recovered_json),
                        "archivo": Path(item["path"]).name,
                        "recuperado": True,
                    }
                    item["message"] = "Transcripción recuperada · sin reprocesar Whisper"
                else:
                    result = whisper_service.transcribe_audio(
                        audio_path=item["path"],
                        output_directory=output_directory,
                    )

                item["whisper_seconds"] = max(
                    0.0, perf_counter() - whisper_started
                )
                item["transcription_recovered"] = bool(recovered_json)

                item["result"] = result

                json_path = (
                    result.get("ruta_json")
                    or result.get("json_path")
                    or ""
                )

                if not json_path:
                    raise RuntimeError(
                        "Whisper no devolvio la ruta JSON de la transcripcion."
                    )

                transcription = TranscriptionService.load_from_json(
                    json_path
                )

                record = (
                    self.relation_service.find_record(item["path"])
                    if self.has_relation_excel()
                    else None
                )

                # Un audio relacionado con un estatus NO autorizado puede ser,
                # por su propia naturaleza, un buzón/silencio/cuelgue y no
                # contener texto útil. Eso no es un fallo técnico de Whisper.
                #
                # En ese caso el lote lo conserva como procesado y lo envía a
                # REVISAR. Nunca se aprueba ni se renombra por esta vía.
                transcription_text = str(
                    getattr(transcription, "text", "") or ""
                ).strip()

                if (
                    record is not None
                    and not transcription_text
                    and not self.relation_service.is_status_authorized(
                        record.estatus_grabacion
                    )
                ):
                    minimum_score = self.relation_service.get_minimum_score()
                    classification = {
                        "clasificacion": "REVISAR",
                        "aprobado": False,
                        "score": 0.0,
                        "puntaje_minimo": minimum_score,
                        "cumple_puntaje": False,
                        "estatus_autorizado": False,
                        "tiene_nombre_final": bool(
                            str(record.nombre_final or "").strip()
                        ),
                        "motivo": (
                            f"estatus no autorizado: {record.estatus_grabacion}; "
                            "transcripción sin texto útil"
                        ),
                    }

                    item["relation"] = record.to_dict()
                    item["relation_status"] = "relacionado"
                    item["analytics"] = {}
                    item["analytics_metadata"] = {
                        "final_result": "REVISAR",
                        "empty_transcription": True,
                        "status_from_excel": record.estatus_grabacion,
                    }
                    item["compliance_score"] = 0.0
                    item["classification"] = classification
                    item["status"] = "completado"

                    try:
                        copy_started = perf_counter()
                        self._copy_classified_audio(
                            item=item,
                            record=record,
                            classification=classification,
                            output_directory=output_directory,
                        )
                        item["copy_seconds"] = max(0.0, perf_counter() - copy_started)
                    except Exception as copy_error:
                        item["copy_status"] = "error"
                        item["classified_audio_path"] = None
                        classification["motivo"] = (
                            f"{classification['motivo']} | "
                            f"error al copiar audio clasificado: {copy_error}"
                        )

                    item["message"] = (
                        f"Sin texto útil · REVISAR · "
                        f"{record.estatus_grabacion}"
                    )

                    results.append(
                        {
                            "transcription": result,
                            "analytics": item["analytics"],
                            "classification": classification,
                            "classified_audio_path": item.get(
                                "classified_audio_path"
                            ),
                            "copy_status": item.get("copy_status"),
                        }
                    )

                    continue

                operational_context = {}

                if record is not None:
                    record_data = record.to_dict()

                    operational_context = {
                        "nombre_final": record_data.get("nombre_final"),
                        "estatus_grabacion": record_data.get("estatus_grabacion"),
                        "campana": record_data.get("campana"),
                        "fecha_asignacion": record_data.get("fecha_asignacion"),
                        "corte": record_data.get("corte"),
                        "vencimiento": record_data.get("vencimiento"),
                        "asignacion": record_data.get("asignacion"),
                        "fecha": record_data.get("fecha"),
                        "gestor": record_data.get("gestor"),
                        "supervisor": record_data.get("supervisor"),
                        "numero_de_tarjeta": record_data.get("numero_de_tarjeta"),
                        "pago_minimo": record_data.get("pago_minimo"),
                        "saldo_total": record_data.get("saldo_total"),
                    }

                analytics_started = perf_counter()
                analysis = AnalyticsService.analyze_transcription(
                    transcription,
                    operational_context=operational_context,
                )
                item["analytics_seconds"] = max(0.0, perf_counter() - analytics_started)

                score = float(
                    getattr(
                        analysis,
                        "compliance_score",
                        0.0,
                    )
                    or 0.0
                )

                minimum_score = self.relation_service.get_minimum_score()

                if self.has_relation_excel() and record is None:
                    classification = {
                        "clasificacion": "REVISAR",
                        "aprobado": False,
                        "score": round(score, 2),
                        "puntaje_minimo": minimum_score,
                        "cumple_puntaje": score >= minimum_score,
                        "estatus_autorizado": False,
                        "tiene_nombre_final": False,
                        "motivo": "audio sin relacion en Excel",
                    }
                elif self.has_relation_excel():
                    # MODO A · AUDIOS + EXCEL
                    classification = self.relation_service.classify(
                        compliance_score=score,
                        record=record,
                    )
                else:
                    # MODO B · SOLO AUDIOS
                    # La aprobación depende del umbral y posteriormente de las
                    # reglas críticas/manuales de Analytics. No requiere Excel.
                    cumple_puntaje = score >= minimum_score
                    classification = {
                        "clasificacion": "APROBADO" if cumple_puntaje else "REVISAR",
                        "aprobado": bool(cumple_puntaje),
                        "score": round(score, 2),
                        "puntaje_minimo": minimum_score,
                        "cumple_puntaje": bool(cumple_puntaje),
                        "estatus_autorizado": None,
                        "tiene_nombre_final": None,
                        "modo": "SOLO_AUDIOS",
                        "motivo": (
                            f"score {score:.1f} >= mínimo {minimum_score:.1f}"
                            if cumple_puntaje
                            else f"score {score:.1f} < mínimo {minimum_score:.1f}"
                        ),
                    }

                analytics_data = analysis.to_dict()
                analytics_metadata = getattr(analysis, "metadata", {}) or {}
                final_result = str(
                    analytics_metadata.get("final_result") or ""
                ).strip().upper()
                critical_failures = (
                    analytics_metadata.get("critical_failures") or []
                )
                status_validation = (
                    analytics_metadata.get("status_validation") or {}
                )
                negotiation_validation = (
                    analytics_metadata.get("negotiation_validation") or {}
                )

                # Puerta de aprobación común en SOLO AUDIOS; sin requisitos de Excel.
                if not self.has_relation_excel():
                    shared = AnalyticsService.shared_quality_decision(
                        analytics_metadata, score, minimum_score,
                        getattr(transcription, "duration_seconds", None),
                    )
                    classification.update(shared)
                    classification["modo"] = "SOLO_AUDIOS"

                # Las reglas críticas del Manual Operativo tienen prioridad
                # sobre el simple cumplimiento del umbral.
                manual_reasons = []

                # v3.5.5 · Regla general de duración para aprobación.
                # El mínimo es obligatorio; el máximo queda configurable y
                # desactivado por defecto (None).
                duration_seconds = float(
                    getattr(transcription, "duration_seconds", 0.0) or 0.0
                )
                duration_validation = {
                    "duration_seconds": round(duration_seconds, 2),
                    "minimum_seconds": float(MIN_APPROVAL_DURATION_SECONDS),
                    "maximum_seconds": (
                        float(MAX_APPROVAL_DURATION_SECONDS)
                        if MAX_APPROVAL_DURATION_SECONDS is not None
                        else None
                    ),
                    "minimum_met": duration_seconds >= float(MIN_APPROVAL_DURATION_SECONDS),
                    "maximum_met": (
                        True
                        if MAX_APPROVAL_DURATION_SECONDS is None
                        else duration_seconds <= float(MAX_APPROVAL_DURATION_SECONDS)
                    ),
                    "valid": True,
                    "result": "CUMPLE",
                    "reason": "",
                }

                if duration_seconds < float(MIN_APPROVAL_DURATION_SECONDS):
                    duration_validation["valid"] = False
                    duration_validation["result"] = "NO APROBADO - DURACION INSUFICIENTE"
                    duration_validation["reason"] = (
                        f"duración {duration_seconds:.1f}s < mínimo "
                        f"{float(MIN_APPROVAL_DURATION_SECONDS):.0f}s"
                    )
                    classification["aprobado"] = False
                    classification["clasificacion"] = "REVISAR"
                    manual_reasons.append(duration_validation["reason"])

                elif (
                    MAX_APPROVAL_DURATION_SECONDS is not None
                    and duration_seconds > float(MAX_APPROVAL_DURATION_SECONDS)
                ):
                    duration_validation["valid"] = False
                    duration_validation["result"] = "REVISAR - DURACION EXCEDIDA"
                    duration_validation["reason"] = (
                        f"duración {duration_seconds:.1f}s > máximo "
                        f"{float(MAX_APPROVAL_DURATION_SECONDS):.0f}s"
                    )
                    classification["aprobado"] = False
                    classification["clasificacion"] = "REVISAR"
                    manual_reasons.append(duration_validation["reason"])

                analytics_metadata["duration_validation"] = duration_validation
                if isinstance(analytics_data, dict):
                    analytics_data.setdefault("metadata", analytics_metadata)

                if final_result == "INCORRECTA" or critical_failures:
                    classification["aprobado"] = False
                    classification["clasificacion"] = "REVISAR"

                    for failure in critical_failures:
                        reason = str(failure.get("reason") or "").strip()
                        if reason:
                            manual_reasons.append(reason)

                    if not manual_reasons:
                        manual_reasons.append(
                            "incumplimiento crítico del Manual Operativo"
                        )

                if status_validation and not status_validation.get("valid", True):
                    classification["aprobado"] = False
                    classification["clasificacion"] = "REVISAR"
                    manual_reasons.extend(
                        str(reason).strip()
                        for reason in status_validation.get("reasons", [])
                        if str(reason).strip()
                    )

                if negotiation_validation and not negotiation_validation.get("valid", True):
                    classification["aprobado"] = False
                    classification["clasificacion"] = "REVISAR"
                    manual_reasons.extend(
                        str(reason).strip()
                        for reason in negotiation_validation.get("reasons", [])
                        if str(reason).strip()
                    )

                if manual_reasons:
                    # Evita repetir el mismo motivo.
                    unique_reasons = list(dict.fromkeys(manual_reasons))
                    classification["motivo"] = " | ".join(unique_reasons)

                # Una sola puerta de decisión para individual, lote con Excel y solo audios.
                decision = AnalyticsService.shared_quality_decision(
                    analytics_metadata, score, minimum_score, duration_seconds, classification)
                classification.update(decision)
                operational_class = decision["clasificacion"]
                if decision.get("motivo"):
                    manual_reasons.append(decision["motivo"])
                # Un mismo dictamen en checkpoint, reporte y metadatos.
                analytics_metadata["final_result"] = operational_class
                analytics_metadata["shared_classification"] = decision
                if isinstance(analytics_data, dict):
                    analytics_data.setdefault("metadata", {})["final_result"] = analytics_metadata["final_result"]
                if manual_reasons:
                    classification["motivo"] = " | ".join(dict.fromkeys(part.strip() for reason in manual_reasons for part in str(reason).split("|") if part.strip()))

                item["analytics"] = analytics_data
                item["analytics_metadata"] = analytics_metadata
                item["compliance_score"] = score
                item["classification"] = classification
                item["status"] = "completado"

                try:
                    copy_started = perf_counter()
                    self._copy_classified_audio(
                        item=item,
                        record=record,
                        classification=classification,
                        output_directory=output_directory,
                    )
                    item["copy_seconds"] = max(0.0, perf_counter() - copy_started)
                except Exception as copy_error:
                    item["copy_status"] = "error"
                    item["classified_audio_path"] = None
                    classification["aprobado"] = False
                    classification["clasificacion"] = "REVISAR"
                    classification["motivo"] = (
                        f"error al copiar audio clasificado: {copy_error}"
                    )

                if self.has_relation_excel() and record is None:
                    item["message"] = (
                        f"Analytics {score:.1f}% · REVISAR · "
                        "audio sin relacion en Excel"
                    )
                else:
                    item["message"] = (
                        f"Analytics {score:.1f}% · "
                        f"{classification['clasificacion']} · "
                        f"{classification['motivo']}"
                    )

                results.append(
                    {
                        "transcription": result,
                        "analytics": item["analytics"],
                        "classification": classification,
                        "classified_audio_path": item.get("classified_audio_path"),
                        "copy_status": item.get("copy_status"),
                    }
                )

            except Exception as error:
                item["status"] = "error"
                item["message"] = str(error)
                item["result"] = None
            finally:
                # Guarda primero los tiempos de trabajo y mide por separado el checkpoint.
                item["elapsed_seconds"] = max(0.0, perf_counter() - item_started)
                self.batch_elapsed_seconds = previous_elapsed + max(0.0, perf_counter() - batch_started)
                checkpoint_started = perf_counter()
                self._save_checkpoint(output_directory, completed=False)
                item["checkpoint_seconds"] = max(0.0, perf_counter() - checkpoint_started)

                # Reporte incremental de seguridad.
                # Se actualiza cada 10 audios finalizados para no penalizar el rendimiento.
                finished_count = sum(
                    1 for batch_item in self.items
                    if batch_item.get("status") in ("completado", "error")
                )
                if (
                    output_directory
                    and finished_count > 0
                    and finished_count % self.partial_report_every == 0
                ):
                    try:
                        self.generate_partial_report(output_directory)
                    except Exception as partial_error:
                        item["partial_report_error"] = str(partial_error)

                # El total visible incluye también el costo real de guardar el checkpoint.
                item["elapsed_seconds"] = max(0.0, perf_counter() - item_started)
                self.batch_elapsed_seconds = previous_elapsed + max(0.0, perf_counter() - batch_started)

            if progress_callback:
                progress_callback(
                    index,
                    total,
                    item,
                )

        self.batch_elapsed_seconds = previous_elapsed + max(0.0, perf_counter() - batch_started)

        # Actualiza una última vez el reporte parcial antes del reporte final.
        if self.items and output_directory:
            try:
                self.generate_partial_report(output_directory)
            except Exception:
                pass

        # Genera un único Excel al finalizar todo el lote.
        # Un fallo del reporte no invalida transcripciones ni clasificaciones.
        self.last_report_path = None
        if self.items:
            try:
                self.last_report_path = BatchReportService.generate_report(
                    items=self.items,
                    output_directory=output_directory,
                    minimum_score=self.relation_service.get_minimum_score(),
                )
            except Exception as report_error:
                # Conserva el lote terminado y deja disponible el error para UI/log.
                self.last_report_path = None
                for item in self.items:
                    if item.get("status") == "completado":
                        item["report_error"] = str(report_error)

        # v3.6.18: "completed" significa lote terminado sin errores. Si hubo
        # errores, el checkpoint queda recuperable y no aparenta éxito total.
        batch_errors = sum(1 for batch_item in self.items if batch_item.get("status") == "error")
        self._save_checkpoint(output_directory, completed=(batch_errors == 0))
        return results

    def generate_partial_report(self, output_directory):
        """Genera/actualiza el Excel de seguridad con resultados ya procesados."""
        self.last_partial_report_path = BatchReportService.generate_partial_report(
            items=self.items,
            output_directory=output_directory,
            minimum_score=self.relation_service.get_minimum_score(),
        )
        return self.last_partial_report_path

    def generate_partial_report_from_checkpoint(self, output_directory):
        """Reconstruye el Excel parcial directamente desde el checkpoint interrumpido."""
        path = self._get_checkpoint_path(output_directory)
        if not path.exists():
            raise FileNotFoundError("No existe checkpoint para generar el reporte parcial.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload.get("items") or []
        processed = [
            item for item in items
            if item.get("status") in ("completado", "error")
        ]
        if not processed:
            raise ValueError("El checkpoint todavía no contiene audios procesados.")
        self.last_partial_report_path = BatchReportService.generate_partial_report(
            items=processed,
            output_directory=output_directory,
            minimum_score=self.relation_service.get_minimum_score(),
        )
        return self.last_partial_report_path

    def get_last_partial_report_path(self):
        return self.last_partial_report_path

    def get_last_report_path(self):
        """Devuelve la ruta del último Excel generado por el Batch."""
        return self.last_report_path

    def get_metrics(self):
        finished_items = [
            item for item in self.items
            if item.get("status") in ("completado", "error")
            and float(item.get("elapsed_seconds", 0.0) or 0.0) > 0
        ]
        finished_times = [float(item.get("elapsed_seconds", 0.0) or 0.0) for item in finished_items]
        average = sum(finished_times) / len(finished_times) if finished_times else 0.0

        # Promedio reciente: últimos 10 audios finalizados. Es más representativo
        # después de cambiar la configuración durante un lote reanudado.
        recent_items = finished_items[-10:]
        recent_times = [float(item.get("elapsed_seconds", 0.0) or 0.0) for item in recent_items]
        recent_average = sum(recent_times) / len(recent_times) if recent_times else 0.0

        def _avg(field):
            values = [float(item.get(field, 0.0) or 0.0) for item in recent_items]
            values = [value for value in values if value >= 0.0]
            return sum(values) / len(values) if values else 0.0

        whisper_average = _avg("whisper_seconds")
        analytics_average = _avg("analytics_seconds")
        copy_average = _avg("copy_seconds")
        checkpoint_average = _avg("checkpoint_seconds")
        measured = whisper_average + analytics_average + copy_average + checkpoint_average
        other_average = max(0.0, recent_average - measured)

        remaining = sum(
            1 for item in self.items
            if item.get("status") in ("pendiente", "procesando")
        )

        try:
            runtime = whisper_service.get_runtime_configuration()
        except Exception:
            runtime = {}

        return {
            "elapsed_seconds": self.batch_elapsed_seconds,
            "average_seconds": average,
            "recent_average_seconds": recent_average,
            "recent_sample_size": len(recent_items),
            "estimated_remaining_seconds": average * remaining,
            "recent_estimated_remaining_seconds": recent_average * remaining,
            "whisper_average_seconds": whisper_average,
            "analytics_average_seconds": analytics_average,
            "copy_average_seconds": copy_average,
            "checkpoint_average_seconds": checkpoint_average,
            "other_average_seconds": other_average,
            "runtime_configuration": runtime,
            "model_was_loaded_at_start": self.model_was_loaded_at_start,
            "model_is_loaded": bool(getattr(whisper_service, "is_model_loaded", False)),
        }

    # =========================================================
    # RESUMEN DE CLASIFICACION
    # =========================================================

    def get_classification_summary(self):
        approved = 0
        review = 0
        analyzed = 0

        for item in self.items:
            classification = item.get("classification")

            if not classification:
                continue

            analyzed += 1

            if classification.get("aprobado"):
                approved += 1
            else:
                review += 1

        return {
            "analizados": analyzed,
            "aprobados": approved,
            "revisar": review,
            "puntaje_minimo": self.relation_service.get_minimum_score(),
        }

    # =========================================================
    # RESUMEN
    # =========================================================

    def get_summary(self):
        total = len(self.items)

        completed = sum(
            1
            for item in self.items
            if item["status"] == "completado"
        )

        errors = sum(
            1
            for item in self.items
            if item["status"] == "error"
        )

        pending = sum(
            1
            for item in self.items
            if item["status"] == "pendiente"
        )

        processing = sum(
            1
            for item in self.items
            if item["status"] == "procesando"
        )

        return {
            "total": total,
            "completed": completed,
            "errors": errors,
            "pending": pending,
            "processing": processing,
        }
