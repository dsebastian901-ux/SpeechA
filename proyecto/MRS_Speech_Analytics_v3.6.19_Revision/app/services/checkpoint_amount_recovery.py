"""Recupera evidencia de audio en una copia y genera reporte sin tocar el origen."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

from app.services.asr_amount_recovery import missing_proposals
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.whisper_service import WhisperService
from app.services.analytics_service import AnalyticsService
from app.services.checkpoint_output import create_checkpoint_output


def recover_checkpoint_amounts(checkpoint_path, audio_directory=None, output_directory=None, whisper_service=None):
    source = Path(checkpoint_path).expanduser().resolve()
    raw = source.read_bytes()
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, dict) or not payload.get("items"):
        raise ValueError("El checkpoint no contiene llamadas.")
    target = create_checkpoint_output(output_directory,
        "Recuperacion_MRS_" + AnalyticsService.ENGINE_REVISION.rsplit("-", 1)[-1] + "_", nested_results=True)
    updated = deepcopy(payload)
    service = whisper_service or WhisperService()
    checked = recovered = pending = 0
    for item in updated["items"]:
        result = item.get("result") or {}
        text, segments = result.get("texto", ""), result.get("segmentos", [])
        if not missing_proposals(text, segments):
            continue
        checked += 1
        # file_name puede contener rutas Windows incluso en otro sistema.
        name = str(result.get("archivo") or item.get("file_name") or "").replace("\\", "/").rsplit("/", 1)[-1]
        candidates = ([Path(audio_directory)/name] if audio_directory else [])
        candidates += [Path(str(result.get("ruta_audio") or "")), Path(str(item.get("path") or ""))]
        audio = next((p for p in candidates if p.is_file()), None)
        if audio is None:
            from app.services.asr_amount_recovery import recover_amounts

            def unavailable(*args):
                raise FileNotFoundError("Audio no localizado")

            audit = recover_amounts(text, segments, unavailable)
            audit["error"] = "Audio no localizado en la carpeta seleccionada."
        else:
            audit = service.recover_missing_amounts(audio, text, segments, result.get("idioma_solicitado") or "es")
        result["recuperacion_importes"] = audit
        recovered += sum(e.get("amount") is not None for e in audit["entries"])
        pending += sum(e.get("amount") is None for e in audit["entries"])
    intermediate = target/"checkpoint_con_evidencia.json"
    intermediate.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    output = reanalyze_checkpoint(intermediate, target/"resultados")
    final_path = Path(output["checkpoint"])
    final = json.loads(final_path.read_text(encoding="utf-8"))
    final["audio_amount_recovery"] = {
        "source_checkpoint_sha256": hashlib.sha256(raw).hexdigest(),
        "checked_calls": checked, "recovered_amounts": recovered, "pending_windows": pending,
        "human_verified": False, "original_transcripts_preserved": True,
    }
    final["reanalysis"]["whisper_executed"] = checked > 0 and any(
        any(not a.get("error") for a in e.get("attempts", []))
        for item in final["items"] for e in (item.get("result", {}).get("recuperacion_importes") or {}).get("entries", []))
    final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    from openpyxl import load_workbook
    book = load_workbook(output["report"])
    note = book["NOTA_REANALISIS"]
    note["A2"] = "Recuperación focalizada: se releen ventanas de audio; se conservan textos originales y no se copian audios."
    note.append(["Importes recuperados por ASR", recovered])
    note.append(["Ventanas pendientes", pending])
    note.append(["Importes recuperados requieren validación; no acreditan autorización de descuentos."])
    book.save(output["report"])
    book.close()
    assert source.read_bytes() == raw, "El checkpoint original cambió"
    return dict(output, checked_calls=checked, recovered_amounts=recovered, pending_windows=pending)
