"""Reanálisis de reglas sin retranscripción, sin copiar audios y sin alterar el origen."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService
from app.services.batch_report_service import BatchReportService
from app.services.transcription_services import TranscriptionService
from app.services.checkpoint_output import create_checkpoint_output



def transcription_with_saved_reviews(item, data=None):
    """Preparar el mismo análisis en reanálisis y exportación de copias."""
    data = (item.get('result') or {}) if data is None else data
    transcription = TranscriptionModel.from_dict(data)
    transcription.text = TranscriptionService._normalize_asr_money_display(transcription.text)
    previous_review = (item.get("analytics_metadata") or {}).get("hostile_interlocutor_exception")
    if isinstance(previous_review, dict):
        transcription.metadata["hostile_interlocutor_exception"] = deepcopy(previous_review)
    amount_review = (item.get("amount_audio_review") or
                     ((item.get("analytics_metadata") or {}).get("amount_recovery_validation") or {}).get("human_review_record"))
    if isinstance(amount_review, dict):
        transcription.metadata["amount_audio_review"] = deepcopy(amount_review)
    financial_review = (item.get("financial_audio_review") if "financial_audio_review" in item else
        ((item.get("analytics_metadata") or {}).get("financial_review_validation") or {}).get("human_review_record"))
    transcription.metadata["financial_audio_review"] = deepcopy(financial_review)
    transcription.metadata['audio_block_evidence']=deepcopy(item.get('audio_block_evidence'))
    transcription.metadata['family_contact_confirmation']=deepcopy(item.get('family_contact_confirmation'))
    transcription.metadata['recado_acceptance_confirmation']=deepcopy(item.get('recado_acceptance_confirmation'))
    transcription.metadata['privacy_disclosure_confirmation']=deepcopy(item.get('privacy_disclosure_confirmation'))
    transcription.metadata['home_warning_confirmation']=deepcopy(item.get('home_warning_confirmation'))
    transcription.metadata['context_asr_recovery']=deepcopy(item.get('context_asr_recovery'))
    return transcription


def recover_saved_transcription(item, directory):
    """Recuperar únicamente el JSON del mismo audio; nunca buscar por fila."""
    name = item.get("file_name")
    if not name or Path(name).name != name or not directory:
        raise ValueError("La llamada no contiene transcripción recuperable.")
    candidate = Path(directory).expanduser().resolve() / (Path(name).stem + ".json")
    raw = candidate.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    if (not isinstance(data, dict) or data.get("archivo") != name
            or not str(data.get("texto") or "").strip()):
        raise ValueError("El JSON de recuperación no corresponde al audio o no contiene texto.")
    if data.get("ruta_audio") and item.get("path"):
        if Path(data["ruta_audio"]).resolve() != Path(item["path"]).resolve():
            raise ValueError("El JSON de recuperación corresponde a otra ruta de audio.")
    return data, {"path": str(candidate), "sha256": hashlib.sha256(raw).hexdigest(),
                  "file_name": name, "whisper_executed": False}

def reanalyze_checkpoint(checkpoint_path, output_directory=None, *, relation_excel=None):
    source = Path(checkpoint_path).expanduser().resolve()
    raw = source.read_bytes()
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list) or not payload["items"]:
        raise ValueError("El checkpoint no contiene llamadas para reanalizar.")
    if (payload.get('schema')==1 and payload.get('source_checkpoint_sha256')
            and any('original_text' in i for i in payload['items'])
            and not any(isinstance(i.get('result'),dict) for i in payload['items'])):
        raise ValueError('Seleccionó una lectura adicional, no el checkpoint del lote. '
                         'Use INCORPORAR_LECTURAS_BLOQUE para incorporarla sin sustituir transcripciones.')
    updated = deepcopy(payload)
    mora_update=None
    if relation_excel is not None:
        from app.services.checkpoint_mora_update import fill_missing_mora
        updated,mora_update=fill_missing_mora(payload,relation_excel)
    target = create_checkpoint_output(output_directory,
        "Reanalisis_MRS_" + AnalyticsService.ENGINE_REVISION.rsplit("-", 1)[-1] + "_")
    destination = target/"checkpoint_reanalizado.json"
    if destination == source or destination.exists():
        raise ValueError("Elija una carpeta nueva; no se sobrescriben checkpoints.")
    outcomes = {}
    pending_count = 0
    relecturas = {'realizadas': 0, 'sin_audio': 0, 'sin_modelo': 0, 'errores': 0}
    model_unavailable = False
    for item in updated["items"]:
        # Un guardado intermedio conserva la cola. No crear ERROR, dictamen,
        # ni una transcripción para audios que todavía no se procesaron.
        if item.get('status') in {'pendiente', 'procesando', 'cancelado'} and not item.get('result'):
            pending_count += 1
            continue
        try:
            data = item.get("result") or {}
            if not data or (isinstance(data, dict) and not str(data.get("texto") or "").strip()):
                data, recovery = recover_saved_transcription(item, payload.get("output_directory"))
                item["result"] = deepcopy(data)
                item["transcription_recovery"] = recovery
            if not isinstance(data, dict) or not str(data.get("texto") or "").strip():
                raise ValueError("La llamada no contiene transcripción recuperable.")
            transcription = transcription_with_saved_reviews(item, data)
            from app.services.account_source_validation import apply_output_name_authority
            apply_output_name_authority(item)
            relation = item.get("relation") or {}
            analysis = AnalyticsService.analyze_transcription(transcription, relation)
            # El reanálisis debe pasar por la segunda escucha cuando exista
            # el audio local y la duda se pueda resolver acústicamente.
            # Nunca se altera el ASR original ni se inventa una confirmación.
            from app.services.context_audio_recovery import needs_recovery
            from app.services.whisper_service import whisper_service
            pending = needs_recovery(analysis.metadata)
            item['relectura_r59'] = 'NO_REQUIERE' if not pending else 'PENDIENTE'
            if pending:
                audio = Path(item.get('path') or '')
                if not audio.is_file() or audio.name != str(item.get('file_name') or audio.name):
                    relecturas['sin_audio'] += 1
                    item['relectura_r59'] = 'AUDIO_LOCAL_NO_DISPONIBLE'
                else:
                    try:
                        if not whisper_service.is_model_loaded and not model_unavailable:
                            try:
                                whisper_service.load_model()
                            except Exception:
                                model_unavailable = True
                        if model_unavailable or not whisper_service.is_model_loaded:
                            relecturas['sin_modelo'] += 1
                            item['relectura_r59'] = 'MODELO_LOCAL_NO_DISPONIBLE'
                        else:
                            recovered = whisper_service.recover_context(
                                audio, data, relation, analysis.metadata)
                            if recovered is not None:
                                item['context_asr_recovery'] = recovered
                                transcription.metadata['context_asr_recovery'] = recovered
                                transcription.audio_path = str(audio)
                                analysis = AnalyticsService.analyze_transcription(
                                    transcription, relation)
                                validation = analysis.metadata.get('context_audio_validation') or {}
                                item['relectura_r59'] = (
                                    'VALIDADA' if validation.get('valid') else
                                    'EVIDENCIA_NO_VERIFICADA')
                                relecturas['realizadas'] += 1
                            else:
                                item['relectura_r59'] = 'SIN_VENTANA_ACUSTICA'
                    except Exception as error:
                        relecturas['errores'] += 1
                        item['relectura_r59'] = 'ERROR_RELECTURA_' + type(error).__name__
            old = item.get("classification") or {}
            base = {"estatus_autorizado": old.get("estatus_autorizado"),
                    "tiene_nombre_final": bool(relation.get("nombre_final")),
                    "missing_excel_relation": bool(not relation and (payload.get('mode') == 'A'
                        or payload.get('relation_excel') or item.get('relation_status') == 'sin_relacion'))}
            decision = AnalyticsService.shared_quality_decision(
                analysis.metadata, analysis.compliance_score, old.get("puntaje_minimo") or 80,
                transcription.duration_seconds, base)
            analysis.metadata["final_result"] = decision["clasificacion"]
            analysis.metadata["shared_classification"] = decision
            item["analytics"] = analysis.to_dict()
            item["analytics_metadata"] = analysis.metadata
            item["classification"] = {**old, **decision}
            item["compliance_score"] = analysis.compliance_score
            item["status"] = "completado"
            item["message"] = decision["motivo"]
            category = decision["clasificacion"]
        except Exception as error:
            category = "ERROR"
            item["status"] = "error"
            item["message"] = str(error)
            item["classification"] = {"clasificacion": "ERROR", "aprobado": False, "motivo": str(error)}
            item["analytics"] = {}
            item["analytics_metadata"] = {"final_result": "ERROR"}
            item["compliance_score"] = None
        item["classified_audio_path"] = None
        item["copy_status"] = "NO_COPIADO_REANALISIS"
        item["transcription_recovered"] = category != "ERROR"
        outcomes[category] = outcomes.get(category, 0)+1
    report = BatchReportService.generate_report(updated["items"], target/"02_Audios"/"Transcripciones",
                                                report_filename="Reporte_Reanalisis_Reglas.xlsx")
    # El encabezado histórico de clasificación física se conserva para compatibilidad.
    # Esta hoja hace explícito que el reanálisis no mueve ni reclasifica archivos de audio.
    from openpyxl import load_workbook
    workbook = load_workbook(report)
    note = workbook.create_sheet("NOTA_REANALISIS")
    note.append(["Reanálisis de reglas sobre transcripciones existentes"])
    note.append(["Se usa Whisper local solo en dudas REVISAR con audio disponible; no se copian ni mueven audios."])
    note.append(["Segundas escuchas ejecutadas", relecturas['realizadas']])
    note.append(["Audios ausentes", relecturas['sin_audio']])
    note.append(["Modelo local ausente", relecturas['sin_modelo']])
    note.append(["Errores de relectura", relecturas['errores']])
    note.append(["La columna 'Clasificación física' muestra la clasificación calculada; no acredita una copia nueva."])
    note.append(["El checkpoint y el reporte originales permanecen sin cambios."])
    note.append(["Revisión del motor", AnalyticsService.ENGINE_REVISION])
    if mora_update is not None:
        note.append(['Moras faltantes recuperadas del Excel',mora_update['filled']])
        note.append(['Moras existentes conservadas',mora_update['already_present']])
        note.append(['Solo se completó asignacion/mora; tarjetas, nombres y transcripciones conservados.'])
    workbook.save(report)
    workbook.close()
    updated["completed"] = not outcomes.get("ERROR") and pending_count == 0
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    updated["last_report_path"] = report
    from app.services.nonpayment_report_service import NonpaymentReportService
    companion_status = NonpaymentReportService.report_status(report)
    updated['last_nonpayment_report_path'] = companion_status['path']
    updated['nonpayment_report_error'] = companion_status['error']
    updated["reanalysis"] = {"engine_revision": AnalyticsService.ENGINE_REVISION,
                              "source_sha256": hashlib.sha256(raw).hexdigest(),
                              "whisper_executed": relecturas['realizadas'] > 0, "audio_files_copied": False,
                              "second_listening": relecturas,
                              "pending_preserved": pending_count, "outcomes": outcomes}
    updated['engine_revision'] = AnalyticsService.ENGINE_REVISION
    destination.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    assert source.read_bytes() == raw, "El origen cambió durante el reanálisis"
    return {"report": report, "nonpayment_report": companion_status["path"], "nonpayment_report_error": companion_status["error"], "checkpoint": str(destination), "outcomes": outcomes,
            "evaluations": sum(outcomes.values()), "pending_preserved": pending_count,
            "engine_revision": AnalyticsService.ENGINE_REVISION, "second_listening": relecturas}
