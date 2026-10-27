"""Saldo corregido y propuesta inicial frente al plan final confirmado, sin datos reales."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.checkpoint_human_review import review_checkpoint, unreviewed_negotiation
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.financial_review_service import make_financial_review


CARD = "4800000000001234"
BALANCE_TEXT = ("Habla MRS. Soy yo. Presenta un saldo vencido por la cantidad de 1300 pesos. "
    "Le ofrecemos una opción de pago de 900 pesos. No puedo confirmar fecha.")
PLAN_TEXT = ("Habla MRS. Soy yo. Presenta un saldo vencido por 6000 pesos. "
    "¿Por qué cantidad podemos contemplar el pago hoy? Lo que traigo son mil pesos. "
    "Puede realizar ese pago y se requeriría un pago más por la cantidad de mil 900 pesos el 18 de octubre. "
    "Muy bien, entonces activaría convenio por mil pesos el día de hoy como primer pago "
    "y el segundo por mil 800 pesos el día 18 de octubre para cubrir la mensualidad vencida. Muy bien. "
    "Puede pagar en Chedraui y Farmacias del Ahorro. Envíe el comprobante por WhatsApp.")


def item(kind="balance"):
    text = BALANCE_TEXT if kind == "balance" else PLAN_TEXT
    return {"file_name": kind+".wav", "result": {"archivo": kind+".wav", "texto": text,
        "segmentos": [{"inicio": 0, "fin": 70, "texto": text}], "duracion_segundos": 90},
        "relation": {"numero_de_tarjeta": CARD, "nombre_final": "000"+CARD+"_synthetic",
            "estatus_grabacion": "NO DEFINE FECHA DE PAGO" if kind == "balance" else "CONVENIO",
            "asignacion": "1PV", "fecha": "2026-10-14", "vencimiento": "2026-10-23", "corte": "23",
            "pago_minimo": 700 if kind == "balance" else 2700, "saldo_total": 1600 if kind == "balance" else 6000}}


def make_review(i):
    return make_financial_review(i["result"], unreviewed_negotiation(i),
        **({"balance_amount": 1600} if i["file_name"] == "balance.wav" else {"confirm_installments": True}),
        audio_verified=True)


def analyze(i, record=None):
    t = TranscriptionModel.from_dict(i["result"])
    t.metadata["financial_audio_review"] = record
    return A.analyze_transcription(t, i["relation"])


@pytest.mark.parametrize("kind", ["balance", "plan"])
def test_confirmed_fact_resolves_only_its_discrepancy_without_changing_source(kind):
    i = item(kind); before = deepcopy(i)
    original = analyze(i)
    assert original.metadata["shared_classification"]["clasificacion"] == "REVISAR"
    updated = analyze(i, make_review(i))
    assert updated.metadata["shared_classification"]["clasificacion"] == "APROBADO"
    assert updated.compliance_score == original.compliance_score
    status = updated.metadata["financial_review_validation"]
    assert status["human_verified"] and not status["review_required"]
    negotiation = updated.metadata["negotiation_validation"]
    if kind == "balance":
        assert negotiation["saldo_informado_detectado"] == 1600
        assert status["human_review_record"]["balance"]["original_amount"] == 1300
        assert negotiation["monto_detectado"] == 900
    else:
        plan = negotiation["installment_validation"]
        assert plan["amounts"] == [1000, 1800] and plan["total"] == 2800
        assert plan["resolved_conflicts"] == [{"installment": 2, "amounts": [1800, 1900]}]
        assert any(e.get("amount") == 1900 for e in plan["evidence"])
        assert negotiation["installment_window"]["valid"] is True
    assert i == before


@pytest.mark.parametrize("change", ["text", "segments", "call", "scope", "hash", "flag", "balance", "plan", "malformed"])
def test_invalid_or_stale_confirmation_never_applies(change):
    i = item("plan" if change == "plan" else "balance"); record = make_review(i)
    if change == "text": i["result"]["texto"] += " Cambio."
    if change == "segments": i["result"]["segmentos"][0]["fin"] += 1
    if change == "call": i["result"]["archivo"] = "other.wav"
    if change == "scope": record["scope"] = "APPROVE_ALL"
    if change == "hash": record["source_sha256"] = "wrong"
    if change == "flag": record["audio_verified"] = "true"
    if change == "balance": record["balance"]["original_amount"] = 1299
    if change == "plan": record["installments"]["amounts"] = [1000, 1900]
    if change == "malformed": record["balance"] = [1600]
    a = analyze(i, record)
    assert a.metadata["financial_review_validation"]["review_required"]
    assert not a.metadata["shared_classification"]["aprobado"]


@pytest.mark.parametrize("value", [0, -1, "NaN", "Infinity", True, "1600.001", ""])
def test_invalid_balance_values_are_rejected(value):
    i = item()
    with pytest.raises(ValueError, match="importe positivo"):
        make_financial_review(i["result"], unreviewed_negotiation(i), balance_amount=value, audio_verified=True)


def test_explicit_audio_confirmation_and_nonempty_selection_are_required():
    i = item(); n = unreviewed_negotiation(i)
    with pytest.raises(ValueError, match="explícita"):
        make_financial_review(i["result"], n, balance_amount=1600)
    with pytest.raises(ValueError, match="Seleccione"):
        make_financial_review(i["result"], n, audio_verified=True)


def test_balance_correction_does_not_resolve_unconfirmed_installment_conflict():
    i = item("plan")
    record = make_financial_review(i["result"], unreviewed_negotiation(i), balance_amount=6000, audio_verified=True)
    assert analyze(i, record).metadata["shared_classification"]["clasificacion"] == "REVISAR"


def test_confirmed_balance_still_compares_against_current_excel():
    i = item(); record = make_review(i); i["relation"]["saldo_total"] = 1700
    a = analyze(i, record)
    assert a.metadata["financial_review_validation"]["human_verified"]
    assert a.metadata["negotiation_validation"]["review_required"]
    assert not a.metadata["shared_classification"]["aprobado"]


@pytest.mark.parametrize("problem", ["under_minimum", "late", "name", "wrong_card", "treatment"])
def test_final_plan_confirmation_keeps_other_blockers(problem):
    i = item("plan")
    if problem == "under_minimum": i["relation"]["pago_minimo"] = 3500
    if problem == "late":
        i["result"]["texto"] = i["result"]["texto"].replace("18 de octubre", "22 de octubre")
    if problem == "name": i["relation"]["nombre_final"] = "0004800000000005678_synthetic"
    if problem == "wrong_card": i["result"]["texto"] += " Referencia de pago 4800000000005678."
    if problem == "treatment": i["result"]["texto"] += " Gestor: Mierda."
    a = analyze(i, make_review(i))
    assert a.metadata["financial_review_validation"]["human_verified"]
    assert not a.metadata["shared_classification"]["aprobado"]


def test_balance_confirmation_never_waives_confirmed_disclosure():
    i = item();i["result"]["texto"] = (
        "Familiar: Soy su madre.\nGestor: Tiene una deuda, un saldo de 1300 pesos.")
    a = analyze(i, make_review(i))
    assert a.metadata["financial_review_validation"]["human_verified"]
    assert a.metadata["shared_classification"]["clasificacion"] == "FALLA_GRAVE"


def test_only_a_final_explicit_plan_can_be_confirmed():
    i = item(); n = unreviewed_negotiation(i)
    with pytest.raises(ValueError, match="plan final explícito"):
        make_financial_review(i["result"], n, confirm_installments=True, audio_verified=True)


def test_checkpoint_reviews_persist_report_original_values_and_can_be_revoked(tmp_path):
    items = [item(), item("plan")]
    source = tmp_path/"batch.json";source.write_text(json.dumps({"items": items}))
    before = source.read_bytes()
    confirmations = {"balance.wav": {"balance_amount":1600, "audio_verified":True},
                     "plan.wav": {"confirm_installments":True, "audio_verified":True}}
    out = review_checkpoint(source, {}, output_directory=tmp_path/"reviewed", financial_confirmations=confirmations)
    assert out["outcomes"] == {"APROBADO":2}
    saved = json.loads(Path(out["checkpoint"]).read_text())
    assert [i["result"] for i in saved["items"]] == [i["result"] for i in items]
    assert saved["human_review"]["financial_reviewed_calls"] == 2
    again = reanalyze_checkpoint(out["checkpoint"],tmp_path/"again")
    assert again["outcomes"] == out["outcomes"]
    book = load_workbook(out["report"],read_only=True,data_only=True)
    rows = list(book["RESULTADOS"].values);head = rows[0]
    assert all(row[head.index("Confirmación financiera")] == "CONFIRMADO POR USUARIO" for row in rows[1:])
    assert rows[1][head.index("Saldo ASR original")] == 1300
    assert rows[1][head.index("Saldo confirmado por usuario")] == 1600
    assert rows[2][head.index("Parcialidades finales confirmadas")] == "1000 + 1800"
    assert "1900" in rows[2][head.index("Historial de propuestas de parcialidades")]
    book.close()
    revoked = review_checkpoint(again["checkpoint"],{},output_directory=tmp_path/"revoked",
        financial_confirmations={name:{"revoke":True} for name in confirmations})
    assert revoked["outcomes"] == {"REVISAR":2}
    saved = json.loads(Path(revoked["checkpoint"]).read_text())
    assert all(i["financial_audio_review"] is None and i["financial_review_history"] for i in saved["items"])
    assert reanalyze_checkpoint(revoked["checkpoint"],tmp_path/"after-revocation")["outcomes"] == {"REVISAR":2}
    assert source.read_bytes() == before


def test_unknown_call_is_rejected_before_writing(tmp_path):
    source = tmp_path/"batch.json";source.write_text(json.dumps({"items":[item()]}))
    with pytest.raises(ValueError, match="ajena"):
        review_checkpoint(source,{},output_directory=tmp_path/"new",financial_confirmations={"unknown.wav":{}})
    assert not (tmp_path/"new").exists()


def test_financial_confirmation_does_not_lower_the_saved_threshold(tmp_path):
    i = item("plan"); original = analyze(i)
    i["classification"] = {"puntaje_minimo":original.compliance_score+1}
    source = tmp_path/"batch.json";source.write_text(json.dumps({"items":[i]}))
    out = review_checkpoint(source,{},output_directory=tmp_path/"new",
        financial_confirmations={"plan.wav":{"confirm_installments":True,"audio_verified":True}})
    assert "APROBADO" not in out["outcomes"]
