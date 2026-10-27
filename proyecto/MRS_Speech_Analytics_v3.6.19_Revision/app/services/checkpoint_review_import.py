"""Incorporar confirmaciones existentes en otro lote con la misma evidencia."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from app.models.transcriptions import TranscriptionModel
from app.services.account_source_validation import corrected_account_name, write_corrected_relation_excel
from app.services.amount_review_service import amount_review_status
from app.services.analytics_service import AnalyticsService
from app.services.checkpoint_output import create_checkpoint_output
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.transcription_services import TranscriptionService


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _read(path):
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list) or not data["items"]:
        raise ValueError("El checkpoint no contiene llamadas.")
    items = {}
    for item in data["items"]:
        name = item.get("file_name")
        if not name or name in items:
            raise ValueError("El checkpoint contiene nombres ausentes o duplicados.")
        items[name] = item
    return raw, data, items


def _review_copy(target, donor, field):
    record = donor.get(field)
    existing = target.get(field)
    if record is None:
        if field in donor and existing is not None:
            raise ValueError("La fuente contiene una revocación; revise esa llamada por separado.")
        return False
    if not isinstance(record, dict):
        raise ValueError("El registro de confirmación no es válido.")
    # Una fecha distinta no cambia el hecho confirmado. Nunca sustituir hechos incompatibles.
    if existing is not None:
        without_time = lambda r: {k: v for k, v in r.items() if k != "reviewed_at"}
        if not isinstance(existing, dict) or without_time(existing) != without_time(record):
            raise ValueError("El lote ya contiene una confirmación diferente; no se sobrescribe.")
    else:
        target[field] = deepcopy(record)
    return True


def _merge_item(base, donor):
    name = base["file_name"]
    original, reviewed = base.get("result") or {}, donor.get("result") or {}
    if original.get("archivo") != name or reviewed.get("archivo") != name:
        raise ValueError("El nombre interno de la transcripción no coincide con la llamada.")
    for key in ("texto", "segmentos", "duracion_segundos"):
        if original.get(key) != reviewed.get(key):
            raise ValueError("La transcripción, segmentos o duración cambiaron; no se traslada la confirmación.")
    if not str(original.get("texto") or "").strip():
        raise ValueError("La llamada no tiene transcripción recuperable.")
    relation, donor_relation = base.get("relation") or {}, donor.get("relation") or {}
    card = str(relation.get("numero_de_tarjeta") or "")
    if not re.fullmatch(r"\d{16}", card) or card != str(donor_relation.get("numero_de_tarjeta") or ""):
        raise ValueError("La tarjeta de origen no coincide; no se traslada la confirmación.")
    if ({k: v for k, v in relation.items() if k != "nombre_final"} !=
            {k: v for k, v in donor_relation.items() if k != "nombre_final"}):
        raise ValueError("Los datos de cuenta cambiaron entre los checkpoints; revise el Excel de origen.")
    target = deepcopy(base)
    fields = []
    audit = reviewed.get("recuperacion_importes")
    if audit is not None and audit != original.get("recuperacion_importes"):
        if original.get("recuperacion_importes") is not None:
            raise ValueError("La evidencia de recuperación existente es diferente; no se sobrescribe.")
        target["result"]["recuperacion_importes"] = deepcopy(audit)
        fields.append("recuperacion_importes")
    amount = _review_copy(target, donor, "amount_audio_review")
    financial = _review_copy(target, donor, "financial_audio_review")
    if amount:
        if not amount_review_status(target["result"], target["amount_audio_review"])["human_verified"]:
            raise ValueError("La confirmación del importe recuperado no corresponde a la evidencia actual.")
        fields.append("amount_audio_review")
    if financial:
        fields.append("financial_audio_review")
    naming = donor.get("output_name_review")
    if naming is not None:
        if (not isinstance(naming, dict) or naming.get("source") != "EXPLICIT_USER_CHOICE_NUMERO_DE_TARJETA"
                or naming.get("corrected_name") != donor_relation.get("nombre_final")):
            raise ValueError("La corrección del nombre no tiene una confirmación válida.")
        if relation.get("nombre_final") != donor_relation.get("nombre_final"):
            if (naming.get("previous_name") != relation.get("nombre_final") or
                    corrected_account_name(relation) != donor_relation.get("nombre_final")):
                raise ValueError("La corrección del nombre no coincide con la tarjeta de origen.")
            target["relation"]["nombre_final"] = donor_relation["nombre_final"]
        elif not re.match(r"^0*" + re.escape(card) + r"_", str(donor_relation.get("nombre_final") or "")):
            raise ValueError("El nombre corregido no contiene la tarjeta de origen.")
        _review_copy(target, donor, "output_name_review")
        fields.append("output_name_review")
    elif relation.get("nombre_final") != donor_relation.get("nombre_final"):
        raise ValueError("El nombre final cambió sin una confirmación de origen.")
    if not (amount or financial or naming):
        raise ValueError("La llamada fuente no contiene confirmaciones humanas que incorporar.")
    transcription = TranscriptionModel.from_dict(target["result"])
    transcription.text = TranscriptionService._normalize_asr_money_display(transcription.text)
    for field in ("amount_audio_review", "financial_audio_review"):
        transcription.metadata[field] = deepcopy(target.get(field))
    checked = AnalyticsService.analyze_transcription(transcription, target.get("relation") or {})
    if financial and not checked.metadata["financial_review_validation"]["human_verified"]:
        raise ValueError("La confirmación financiera no corresponde a la evidencia actual.")
    return target, fields


def import_checkpoint_reviews(batch_path, reviewed_path, output_directory=None, relation_excel=None):
    source, reviewed_source = Path(batch_path).expanduser().resolve(), Path(reviewed_path).expanduser().resolve()
    if source == reviewed_source:
        raise ValueError("Seleccione el lote completo y un checkpoint revisado diferente.")
    raw, original, master = _read(source)
    reviewed_raw, _, donors = _read(reviewed_source)
    if set(donors)-set(master):
        raise ValueError("El checkpoint revisado contiene llamadas ajenas al lote completo.")
    updated = deepcopy(original)
    changes, excel_corrections = [], {}
    # Validar todo antes de crear la salida. Ninguna fila se incorpora parcialmente.
    for index, item in enumerate(updated["items"]):
        name = item["file_name"]
        if name not in donors:
            continue
        merged, fields = _merge_item(item, donors[name])
        record = {"file_name": name, "fields": fields, "previous_item_sha256": _digest(item),
                  "previous_result_sha256": _digest(item.get("result")),
                  "imported_result_sha256": _digest(merged.get("result"))}
        if item.get("relation", {}).get("nombre_final") != merged.get("relation", {}).get("nombre_final"):
            excel_corrections[name] = {key: merged["relation"][key] for key in ("nombre_final", "numero_de_tarjeta")}
        merged["review_import"] = {"reviewed_checkpoint_sha256": hashlib.sha256(reviewed_raw).hexdigest(), **record}
        updated["items"][index] = merged
        changes.append(record)
    target = create_checkpoint_output(output_directory,
        "Integracion_MRS_" + AnalyticsService.ENGINE_REVISION.rsplit("-", 1)[-1] + "_", nested_results=True)
    excel_source = Path(relation_excel or original.get("relation_excel") or "")
    excel_copy = None
    if excel_corrections and excel_source.is_file():
        excel_copy = write_corrected_relation_excel(excel_source, excel_corrections,
            target/("Datos_Cuentas_Corregidos" + excel_source.suffix))
    intermediate = target/"checkpoint_con_validaciones_integradas.json"
    intermediate.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    result = reanalyze_checkpoint(intermediate, target/"resultados")
    destination = Path(result["checkpoint"])
    final = json.loads(destination.read_text(encoding="utf-8"))
    final["review_import"] = {"batch_sha256": hashlib.sha256(raw).hexdigest(),
        "reviewed_checkpoint_sha256": hashlib.sha256(reviewed_raw).hexdigest(),
        "imported_at": datetime.now(timezone.utc).isoformat(), "imported_calls": len(changes),
        "batch_calls": len(master), "scope": "MATCHED_FINANCIAL_AND_OUTPUT_NAME_REVIEWS_ONLY",
        "whisper_executed": False, "audio_files_copied": False, "changes": changes, "corrected_excel": excel_copy}
    destination.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    from openpyxl import load_workbook
    book = load_workbook(result["report"])
    note = book["NOTA_REANALISIS"]
    note.append(["Confirmaciones incorporadas por coincidencia de llamada y evidencia", len(changes)])
    note.append(["Total de llamadas conservadas en el lote", len(master)])
    note.append(["Se recalcularon todas las clasificaciones; no se importaron etiquetas de aprobación."])
    if excel_copy:
        note.append(["Excel corregido en copia", excel_copy])
    elif excel_corrections:
        note.append(["Excel original no localizado; nombre corregido solo en el checkpoint y reporte nuevos."])
    book.save(result["report"]); book.close()
    assert source.read_bytes() == raw and reviewed_source.read_bytes() == reviewed_raw, "Un origen cambió"
    return dict(result, imported_calls=len(changes), corrected_excel=excel_copy)
