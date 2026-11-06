"""Registrar confirmaciones explícitas y generar una copia sin ejecutar Whisper."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from app.services.amount_review_service import make_amount_review
from app.services.account_source_validation import corrected_account_name, write_corrected_relation_excel
from app.services.analytics_service import AnalyticsService
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.checkpoint_output import create_checkpoint_output
from app.models.transcriptions import TranscriptionModel
from app.services.transcription_services import TranscriptionService
from app.services.financial_review_service import make_financial_review


def unreviewed_negotiation(item):
    transcription = TranscriptionModel.from_dict(item.get("result") or {})
    transcription.text = TranscriptionService._normalize_asr_money_display(transcription.text)
    transcription.metadata["financial_audio_review"] = None
    return AnalyticsService.analyze_transcription(transcription, item.get("relation") or {}).metadata["negotiation_validation"]


def review_checkpoint(checkpoint_path, confirmations, name_corrections=(), output_directory=None, relation_excel=None,
                      *, financial_confirmations=None):
    source = Path(checkpoint_path).expanduser().resolve()
    raw = source.read_bytes()
    original = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(original, dict) or not original.get("items"):
        raise ValueError("El checkpoint no contiene llamadas.")
    names = [i.get("file_name") or (i.get("result") or {}).get("archivo") for i in original["items"]]
    if len(names) != len(set(names)):
        raise ValueError("El checkpoint tiene nombres duplicados; confirme la relación antes de revisar.")
    corrections = set(name_corrections)
    financial_confirmations = financial_confirmations or {}
    if (set(confirmations)|corrections|set(financial_confirmations))-set(names):
        raise ValueError("Una revisión corresponde a una llamada ajena al checkpoint.")
    updated = deepcopy(original)
    excel_corrections={}
    for item, name in zip(updated["items"], names):
        if name in financial_confirmations:
            entry = financial_confirmations[name]
            if set(entry)-{"balance_amount", "confirm_installments", "audio_verified", "revoke"}:
                raise ValueError("La revisión contiene campos financieros desconocidos.")
            if entry.get("revoke") is True:
                if set(entry) != {"revoke"}:
                    raise ValueError("No se puede confirmar y revocar a la vez.")
                record = None
            else:
                record = make_financial_review(item.get("result") or {}, unreviewed_negotiation(item),
                    balance_amount=entry.get("balance_amount"), confirm_installments=entry.get("confirm_installments") is True,
                    audio_verified=entry.get("audio_verified") is True)
            previous = item.get("financial_audio_review")
            if previous:
                item.setdefault("financial_review_history", []).append({"review": previous,
                    "replaced_at": datetime.now(timezone.utc).isoformat(), "revoked": record is None})
            item["financial_audio_review"] = record
        if name in confirmations:
            entry = confirmations[name]
            item["amount_audio_review"] = make_amount_review(
                item.get("result") or {}, entry.get("anchors", []), audio_verified=entry.get("audio_verified") is True)
        if name in corrections:
            relation = item.get("relation") or {}
            corrected = corrected_account_name(relation)
            item["output_name_review"] = {"reviewed_at": datetime.now(timezone.utc).isoformat(),
                "source": "EXPLICIT_USER_CHOICE_NUMERO_DE_TARJETA", "previous_name": relation.get("nombre_final"),
                "corrected_name": corrected}
            item["relation"]["nombre_final"] = corrected
            excel_corrections[name]={"nombre_final":corrected,"numero_de_tarjeta":relation["numero_de_tarjeta"]}
    target = create_checkpoint_output(output_directory,
        "Validacion_MRS_" + AnalyticsService.ENGINE_REVISION.rsplit("-", 1)[-1] + "_", nested_results=True)
    excel_copy=None
    excel_source=Path(relation_excel or original.get("relation_excel") or "")
    if corrections and excel_source.is_file():
        excel_copy=write_corrected_relation_excel(excel_source,excel_corrections,target/("Datos_Cuentas_Corregidos"+excel_source.suffix))
    intermediate = target/"checkpoint_con_validacion.json"
    intermediate.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    result = reanalyze_checkpoint(intermediate, target/"resultados")
    final_path = Path(result["checkpoint"])
    final = json.loads(final_path.read_text(encoding="utf-8"))
    final["human_review"] = {"source_checkpoint_sha256": hashlib.sha256(raw).hexdigest(),
        "amount_reviewed_calls": len(confirmations), "output_names_corrected": len(corrections),
        "financial_reviewed_calls": len(financial_confirmations),
        "corrected_excel":excel_copy,
        "whisper_executed": False, "scope": ("AMOUNTS_OUTPUT_NAMES_AND_FINANCIAL_FACTS_ONLY" if financial_confirmations else "AMOUNTS_AND_OUTPUT_NAMES_ONLY")}
    final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    from openpyxl import load_workbook
    book = load_workbook(result["report"])
    note = book["NOTA_REANALISIS"]
    note.append(["Confirmaciones de importe registradas por el usuario",len(confirmations)])
    note.append(["Identificadores de nombre final corregidos en la copia",len(corrections)])
    note.append(["Llamadas con saldo/acuerdo final confirmado o revocado",len(financial_confirmations)])
    if excel_copy:
        note.append(["Excel corregido en copia",excel_copy])
    elif corrections:
        note.append(["Excel original no localizado; los nombres corregidos están solo en el checkpoint nuevo."])
    note.append(["El audio se coteja contra numero_de_tarjeta de origen; la revisión del nombre no certifica el resto de la llamada."])
    book.save(result["report"])
    book.close()
    assert source.read_bytes() == raw, "El checkpoint original cambió"
    return dict(result,corrected_excel=excel_copy,output_names_corrected=len(corrections))
