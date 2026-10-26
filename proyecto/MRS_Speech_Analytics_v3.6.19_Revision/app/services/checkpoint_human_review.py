"""Registrar confirmaciones explícitas y generar una copia sin ejecutar Whisper."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from app.services.amount_review_service import make_amount_review
from app.services.account_source_validation import corrected_account_name, write_corrected_relation_excel
from app.services.analytics_service import AnalyticsService
from app.services.checkpoint_reanalysis import reanalyze_checkpoint


def review_checkpoint(checkpoint_path, confirmations, name_corrections=(), output_directory=None, relation_excel=None):
    source = Path(checkpoint_path).expanduser().resolve()
    raw = source.read_bytes()
    original = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(original, dict) or not original.get("items"):
        raise ValueError("El checkpoint no contiene llamadas.")
    names = [i.get("file_name") or (i.get("result") or {}).get("archivo") for i in original["items"]]
    if len(names) != len(set(names)):
        raise ValueError("El checkpoint tiene nombres duplicados; confirme la relación antes de revisar.")
    corrections = set(name_corrections)
    if (set(confirmations)|corrections)-set(names):
        raise ValueError("Una revisión corresponde a una llamada ajena al checkpoint.")
    updated = deepcopy(original)
    excel_corrections={}
    for item, name in zip(updated["items"], names):
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
    target = (Path(output_directory).expanduser().resolve() if output_directory else
              Path(tempfile.mkdtemp(prefix="Validacion_MRS_"+AnalyticsService.ENGINE_REVISION.rsplit("-",1)[-1]+"_", dir=source.parent)))
    if target.exists() and any(target.iterdir()):
        raise ValueError("Seleccione una carpeta nueva y vacía.")
    target.mkdir(parents=True, exist_ok=True)
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
        "corrected_excel":excel_copy,
        "whisper_executed": False, "scope": "AMOUNTS_AND_OUTPUT_NAMES_ONLY"}
    final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    from openpyxl import load_workbook
    book = load_workbook(result["report"])
    note = book["NOTA_REANALISIS"]
    note.append(["Confirmaciones de importe registradas por el usuario",len(confirmations)])
    note.append(["Identificadores de nombre final corregidos en la copia",len(corrections)])
    if excel_copy:
        note.append(["Excel corregido en copia",excel_copy])
    elif corrections:
        note.append(["Excel original no localizado; los nombres corregidos están solo en el checkpoint nuevo."])
    note.append(["El audio se coteja contra numero_de_tarjeta de origen; la revisión del nombre no certifica el resto de la llamada."])
    book.save(result["report"])
    book.close()
    assert source.read_bytes() == raw, "El checkpoint original cambió"
    return dict(result,corrected_excel=excel_copy,output_names_corrected=len(corrections))
