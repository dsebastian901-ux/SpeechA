"""Reanalizar checkpoints sin audio, Whisper, ni modificaciones a los originales.

Los resultados contienen evidencia privada: guardarlos fuera del repositorio.
Las etiquetas históricas no son el oráculo; se comprueban invariantes de seguridad.
"""
import argparse
import collections
import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path
import subprocess
import sys


def evaluate(source, files):
    sys.path.insert(0, str(source))
    from app.models.transcriptions import TranscriptionModel
    from app.services.analytics_service import AnalyticsService
    rows = []
    for path in files:
        raw = path.read_bytes()
        source_hash = hashlib.sha256(raw).hexdigest()
        checkpoint = json.loads(raw.decode("utf-8-sig"))
        items = checkpoint.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError(f"Checkpoint sin llamadas: {path.name}")
        for index, item in enumerate(items, 1):
            t = TranscriptionModel.from_dict(item["result"])
            analysis = AnalyticsService.analyze_transcription(t, item.get("relation") or {})
            metadata = analysis.metadata
            decision = AnalyticsService.shared_quality_decision(metadata, analysis.compliance_score,
                                                                duration_seconds=t.duration_seconds)
            rows.append({"case": f"{path.stem}:{index:03}", "checkpoint": path.name,
                         "index": index, "source_sha256": source_hash,
                         "transcript_sha256": hashlib.sha256(t.text.encode("utf-8")).hexdigest(),
                         "score": analysis.compliance_score, "metadata": metadata,
                         "shared_decision": decision})
    return rows


def worker(source, files):
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--source", str(source)]
    result = subprocess.run(command + [str(f) for f in files], text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def invariants(row):
    m = row["metadata"]
    failures = []
    privacy = m.get("privacy_validation") or {}
    pen = {p["id"] for p in m.get("penalties", [])}
    approved = m["final_result"] in {"APROBADA", "APROBADO", "APROBADO_CON_EXCEPCION", "APROBADO_SIN_ETIQUETAR"}
    if privacy.get("review_required") and approved:
        failures.append("privacidad incierta aprobada")
    if privacy.get("confirmed_disclosure") and ("PEN003" not in pen or m["final_result"] not in {"INCORRECTA", "FALLA_GRAVE"}):
        failures.append("divulgación confirmada sin bloqueo crítico")
    if "PEN003" in pen and not privacy.get("confirmed_disclosure"):
        failures.append("PEN003 sin atribución confirmada")
    card = str((m.get("card_validation") or {}).get("result", ""))
    if (card == "TARJETA INCORRECTA" or card.startswith("REVISAR -")) and approved:
        failures.append("referencia pendiente aprobada")
    status = m.get("status_validation") or {}
    recado = status.get("recado_evidence")
    if recado and status.get("matches") is True and not recado.get("confirmed_recado"):
        failures.append("equivalencia de recado sin evidencia")
    checks = m.get("quality_checks") or {}
    if (checks.get("groseria_bloquea_aprobacion") or checks.get("queja_maltrato_detectada")) and approved:
        failures.append("trato pendiente aprobado")
    if privacy.get("review_required") and row["shared_decision"].get("aprobado"):
        failures.append("puerta común aprobó privacidad incierta")
    negotiation = m.get("negotiation_validation") or {}
    if approved and m.get('quality_contact_type')=='CONTACTO NO DETERMINADO':
        failures.append('interlocutor no determinado aprobado')
    if approved and negotiation.get('unaccepted_new_payment_instruction'):
        failures.append('instrucción nueva de pago sin aceptación aprobada como seguimiento')
    if approved and (negotiation.get("installment_validation") or {}).get("review_required"):
        failures.append("parcialidades contradictorias aprobadas")
    if approved and status.get("detected_status") == "CONVENIO" and not (negotiation.get("commitment_evidence") or {}).get("accepted"):
        failures.append("convenio aprobado sin aceptación acreditada")
    return failures


def verified_followup_approval(metadata):
    """Excepción documental explícita para la regla del usuario del 28/oct.

    No elimina la revisión de hashes ni las causas de cada penalización. Solo
    permite que un seguimiento acreditado sea aprobado bajo la nueva política.
    """
    status=metadata.get('status_validation') or {}
    negotiation=metadata.get('negotiation_validation') or {}
    completed=negotiation.get('completed_payment_evidence') or {}
    return bool(status.get('policy_source')=='ACLARACION_USUARIO_20261028'
        and status.get('evidence_method')=='SEGUIMIENTO_PAGO_REPORTADO_ESTATUS_ORIGINAL'
        and status.get('excel_status') in {'CONVENIO','NO DEFINE FECHA DE PAGO'}
        and status.get('matches') is True and status.get('valid') is True and status.get('evidence')
        and metadata.get('quality_contact_type')=='TITULAR'
        and negotiation.get('payment_followup_case') is True
        and negotiation.get('payment_confirmation_case') is True
        and completed.get('confirmed') is True and completed.get('evidence')
        and not negotiation.get('commitment_confirmed')
        and not negotiation.get('unaccepted_new_payment_instruction')
        and negotiation.get('valid') is True and not negotiation.get('review_required')
        and not metadata.get('critical_failures')
        and not (metadata.get('privacy_validation') or {}).get('review_required')
        and not (metadata.get('privacy_validation') or {}).get('confirmed_disclosure')
        and not invariants({'metadata':metadata,'shared_decision':{'aprobado':True}}))


def verified_removal(rule, previous, current):
    """Causas esperadas explícitas; una etiqueta histórica no es un oráculo."""
    negotiation = current.get("negotiation_validation") or {}
    payment = current.get("convenio_payment_validation") or {}
    if rule == "payment_already_reported":
        return bool(negotiation.get("payment_confirmation_case")
                    and (negotiation.get("completed_payment_evidence") or {}).get("confirmed")
                    and not (negotiation.get("commitment_evidence") or {}).get("accepted"))
    if rule == "two_distinct_payment_places":
        return len(set(payment.get("authorized_places_detected") or [])) >= 2 and bool(payment.get("payment_place_details"))
    if rule == "accepted_payment_commitment":
        return negotiation.get("commitment_confirmed") is True and (negotiation.get("commitment_evidence") or {}).get("accepted") is True
    if rule == "reported_transfer_not_new_instruction":
        return bool((previous.get("convenio_payment_validation") or {}).get("transfer_data_review")
                    and negotiation.get("payment_confirmation_case")
                    and (negotiation.get("completed_payment_evidence") or {}).get("confirmed")
                    and payment.get("reported_transfer_only")
                    and not payment.get("transfer_instruction_evidence")
                    and not payment.get("future_transfer_discussion")
                    and not payment.get("unauthorized_payment_method")
                    and not payment.get("wrong_bank_data"))
    if rule == "callback_numbers_not_bank_account":
        return bool((previous.get("convenio_payment_validation") or {}).get("wrong_bank_data")) and not payment.get("unauthorized_evidence") and not payment.get("wrong_bank_data")
    if rule == "contact_number_not_payment_date":
        old = previous.get("negotiation_validation") or {}
        evidence = old.get("promise_date_evidence") or ""
        try:
            old_date = date.fromisoformat(old["promise_date"])
            call_date = date.fromisoformat(str(old["call_date"]).split()[0])
        except (KeyError, TypeError, ValueError):
            return False
        return bool(re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", evidence)
                    and re.search(r"comprobante|whatsapp|numero", evidence)
                    and old_date.year > call_date.year+2
                    and negotiation.get("promise_date") != old.get("promise_date")
                    and not negotiation.get("commitment_confirmed")
                    and current.get("final_result") == "REVISAR")
    if rule == "capture_instruction_not_recipient":
        return (previous.get("quality_contact_type") == "TERCERO" and
                current.get("quality_contact_type") != "TERCERO")
    if rule in {"spoken_payment_date", "payment_store_not_date"}:
        old = previous.get("negotiation_validation") or {}
        raw = negotiation.get("promise_date_text") or ""
        evidence = negotiation.get("promise_date_evidence") or ""
        try:
            detected = date.fromisoformat(negotiation["promise_date"])
            due = date.fromisoformat(str(negotiation["due_date"]).split()[0])
        except (KeyError, ValueError, TypeError):
            return False
        supported = raw in evidence and detected <= due
        if rule == "spoken_payment_date":
            return supported and not old.get("promise_date") and bool(re.search(r"[a-z]+ de [a-z]+", raw))
        return supported and old.get("promise_date_text") == "7-11" and raw != "7-11" and old.get("promise_date", "") > due.isoformat()
    return False


def verified_current_agreement(metadata):
    """Una aceptación textual nueva permite retirar solo PEN009 documentado.

    No autoriza quitar faltas de privacidad, trato, referencias o finanzas. La
    revisión por llamada sigue exigiendo hash de origen y causa verificable.
    """
    status=metadata.get('status_validation') or {}
    n=metadata.get('negotiation_validation') or {}
    commitment=n.get('commitment_evidence') or {}
    policy=n.get('mora_payment_policy') or {}
    try:
        promise=date.fromisoformat(n['promise_date'])
        call=date.fromisoformat(str(n['call_date']).split()[0])
        due=date.fromisoformat(str(n['due_date']).split()[0])
        end=date.fromisoformat(policy['window_end'])
    except (KeyError,TypeError,ValueError):
        return False
    window_ok=promise<=end or (n.get('installment_window') or {}).get('valid') is True
    return bool(metadata.get('quality_contact_type')=='TITULAR'
        and (metadata.get('contact_validation') or {}).get('confirmed') is True
        and status.get('matches') is True and status.get('valid') is True
        and status.get('detected_status')=='CONVENIO'
        and status.get('evidence_method')=='COMPROMISO_ACEPTADO_CON_FECHA'
        and status.get('evidence')==commitment.get('evidence') and commitment.get('evidence')
        and commitment.get('accepted') is True and n.get('commitment_confirmed') is True
        and n.get('valid') is True and not n.get('review_required')
        and not n.get('hard_invalid') and not n.get('unaccepted_new_payment_instruction')
        and call<=promise<=due and window_ok
        and (metadata.get('shared_classification') or {}).get('aprobado') is True
        and not metadata.get('critical_failures')
        and not (metadata.get('privacy_validation') or {}).get('review_required')
        and not (metadata.get('privacy_validation') or {}).get('confirmed_disclosure')
        and not invariants({'metadata':metadata,'shared_decision':{'aprobado':True}}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--baseline-source", type=Path)
    parser.add_argument("--reviewed-changes", type=Path)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("files", type=Path, nargs="*")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(evaluate(args.source, args.files), ensure_ascii=False))
        return
    if not args.input_dir or not args.output_dir or not args.baseline_source:
        parser.error("Se requieren --input-dir, --output-dir y --baseline-source")
    files = sorted(args.input_dir.glob("*.json"))
    if not files:
        parser.error("No se encontraron checkpoints JSON; cero llamadas no es una regresión")
    # Datos reales nunca se escriben dentro del checkout durante esta auditoría.
    checkout = Path(__file__).resolve().parents[3]
    target = args.output_dir.resolve()
    if target == checkout or checkout in target.parents:
        parser.error("Elija una salida privada fuera del repositorio")
    target.mkdir(parents=True, exist_ok=True)
    before = worker(args.baseline_source, files)
    after = worker(args.source, files)
    old = {r["case"]: r for r in before}
    if len(old) != len(after) or set(old) != {r["case"] for r in after}:
        raise RuntimeError("No coinciden las llamadas antes/después")
    (target/"before.json").write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
    (target/"after.json").write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8")
    differences, failures, penalty_changes = [], [], []
    reviewed = {}
    if args.reviewed_changes:
        reviewed = {r["case"]: r for r in json.loads(args.reviewed_changes.read_text(encoding="utf-8"))}
    totals = collections.Counter()
    for row in after:
        prev = old[row["case"]]
        m, b = row["metadata"], prev["metadata"]
        old_pen = {p["id"] for p in b["penalties"]}
        new_pen = {p["id"] for p in m["penalties"]}
        removed = sorted(old_pen-new_pen)
        added = sorted(new_pen-old_pen)
        other_removed = set(removed)-{"PEN003"}
        review = reviewed.get(row["case"], {})
        if other_removed and other_removed == set(review.get("allowed_removed", [])):
            original = json.loads((args.input_dir/row["checkpoint"]).read_text(encoding="utf-8-sig"))["items"][row["index"]-1]
            valid = (not str(m["final_result"]).startswith("APROBAD") or
                     (bool(review.get('checkpoint_sha256')) and (
                         verified_followup_approval(m) or
                         (other_removed=={'PEN009'} and verified_current_agreement(m)))))
            if review.get("checkpoint_sha256"):
                valid = valid and row["source_sha256"] == review["checkpoint_sha256"]
                rules = review.get("evidence_rules") or {}
                valid = valid and set(rules) == other_removed and all(verified_removal(rules[p], b, m) for p in other_removed)
            else:
                valid = valid and review.get("required_text") in original["result"]["texto"].lower()
            if not valid:
                penalty_changes.append({"case": row["case"], "removed": removed, "issue": "Revisión documental no coincide con evidencia o resultado"})
        elif other_removed:
            penalty_changes.append({"case": row["case"], "removed": removed})
        issues = invariants(row)
        failures.extend({"case": row["case"], "issue": issue} for issue in issues)
        totals[m["final_result"]] += 1
        differences.append({"case": row["case"], "before_result": b["final_result"],
            "after_result": m["final_result"], "before_score": prev["score"], "after_score": row["score"],
            "removed_penalties": "|".join(removed), "added_penalties": "|".join(added),
            "privacy_review": (m.get("privacy_validation") or {}).get("review_required"),
            "before_card": b["card_validation"]["result"], "after_card": m["card_validation"]["result"],
            "before_status": b["status_validation"]["detected_status"],
            "after_status": m["status_validation"]["detected_status"],
            "safety_invariants": "PASS" if not issues else "FAIL"})
    with (target/"before_after.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(differences[0]))
        writer.writeheader()
        writer.writerows(differences)
    summary = {"evaluations": len(after), "checkpoints": len(files), "outcomes": dict(totals),
               "unique_transcripts": len({r["transcript_sha256"] for r in after}),
               "per_checkpoint": {p.name: dict(collections.Counter(r["metadata"]["final_result"] for r in after if r["checkpoint"]==p.name)) for p in files},
               "safety_failures": failures, "other_penalties_removed": penalty_changes,
               "acoustic_verification": False,
               "changed_outcomes": sum({"APROBADA":"APROBADO", "INCORRECTA":"FALLA_GRAVE"}.get(r["before_result"], r["before_result"])!=r["after_result"] for r in differences)}
    (target/"summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    if failures or penalty_changes:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
