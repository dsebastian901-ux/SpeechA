"""Recuperación de evidencia con muestras sintéticas; no se inventan importes."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import wave

import numpy as np
import pytest
from openpyxl import load_workbook

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.asr_amount_recovery import missing_proposals, monetary_readings, recover_amounts, validated_entries
from app.services.checkpoint_amount_recovery import recover_checkpoint_amounts
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.whisper_service import WhisperService


TEXT = ("Habla MRS. Soy yo. Se le está ofreciendo un descuento para finiquitar la deuda, "
        "le están pidiendo la cuenta. Me interesa, pero yo creo a principios de noviembre.")
SEGMENTS = [{"inicio": 20, "fin": 28, "texto": TEXT}]
READINGS = ["Le están pidiendo únicamente dos mil cuatrocientos cincuenta pesos para liquidar la cuenta.",
            "Únicamente 2.450 pesos para liquidar la cuenta."]
CONTEXT = {"estatus_grabacion": "NO DEFINE FECHA DE PAGO", "asignacion": "C4",
           "saldo_total": "50000", "pago_minimo": "2000"}


def audit():
    readings = iter(READINGS)
    return recover_amounts(TEXT, SEGMENTS, lambda *args: next(readings))


@pytest.mark.parametrize("text,value", [
    ("2.450 pesos", 2450), ("2,450 pesos", 2450), ("2450 pesos", 2450),
    ("dos mil cuatrocientos cincuenta pesos", 2450), ("novecientos pesos", 900),
    ("mil pesos", 1000), ("dos mil pesos", 2000), ("10.50 pesos", 10.5),
])
def test_currency_amounts_in_two_notations(text, value):
    assert monetary_readings(text) == {value}


@pytest.mark.parametrize("text", [
    "Referencia de tarjeta 1234567890123456.", "Teléfono 5551234567.",
    "El día 16 de octubre.", "Saldo total 50000 pesos.",
    "No le están pidiendo 2450 pesos.",
])
def test_non_offer_numbers_do_not_confirm_recovery(text):
    assert not monetary_readings(text)


@pytest.mark.parametrize("text", [
    "Le están pidiendo dos mil pesos.", "Le están pidiendo 2450.",
    "Le están pidiendo novecientos.",
    "No le están pidiendo la cuenta.", "Me dijeron que le están pidiendo la cuenta.",
    "Únicamente la cuenta.",
    "Le ofrecemos información de contacto.",
    "Le están pidiendo su identificación oficial.",
])
def test_complete_ambiguous_negated_and_historical_requests_are_not_rewritten(text):
    assert not missing_proposals(text, [{"texto": text, "inicio": 1, "fin": 4}])


def test_missing_timing_or_known_customer_does_not_trigger_an_audio_window():
    assert not missing_proposals(TEXT, [])
    assert not missing_proposals(TEXT, [dict(SEGMENTS[0], speaker_role="TITULAR")])


def test_matching_windows_recover_an_amount_without_changing_text_or_using_excel():
    original = deepcopy(SEGMENTS)
    result = audit()
    entries = validated_entries(TEXT, SEGMENTS, result)
    assert len(entries) == 1 and entries[0]["amount"] == 2450
    assert result["human_verified"] is False
    assert SEGMENTS == original
    t = TranscriptionModel("synthetic.wav", "synthetic.wav", TEXT, duration_seconds=90,
                           segments=SEGMENTS, metadata={"recuperacion_importes": result})
    a = A.analyze_transcription(t, CONTEXT)
    assert a.metadata["negotiation_validation"]["monto_detectado"] == 2450
    assert a.metadata["negotiation_validation"]["validacion_monto"] == "VALIDA - MINIMO DE LIQUIDACION SEGUN MORA"
    assert a.metadata["shared_classification"]["clasificacion"] == "REVISAR"
    assert t.text == TEXT


@pytest.mark.parametrize("second", ["2400 pesos", "2450 pesos y 2500 pesos", "No recuerdo la cantidad."])
def test_disagreement_ambiguity_and_missing_readings_never_guess_an_amount(second):
    readings = iter([READINGS[0], second])
    result = recover_amounts(TEXT, SEGMENTS, lambda *args: next(readings))
    assert result["entries"][0]["amount"] is None
    assert not validated_entries(TEXT, SEGMENTS, result)


def test_failed_audio_read_is_pending_instead_of_a_fabricated_amount():
    def failed(*args):
        raise FileNotFoundError("Missing audio")
    result = recover_amounts(TEXT, SEGMENTS, failed)
    assert result["entries"][0]["status"] == "REQUIERE_REVISION"
    assert result["entries"][0]["amount"] is None


def test_missing_model_does_not_turn_a_completed_transcription_into_a_crash(monkeypatch):
    service = WhisperService()
    def unavailable():
        raise RuntimeError("Model unavailable")
    monkeypatch.setattr(service, "load_model", unavailable)
    result = service.recover_missing_amounts("missing.wav", TEXT, SEGMENTS)
    assert result["entries"][0]["amount"] is None
    assert all(a["error"] == "RuntimeError" for a in result["entries"][0]["attempts"])


@pytest.mark.parametrize("change", ["text", "amount", "window", "evidence", "shape", "invalid_amount", "invalid_anchor", "schema"])
def test_stale_or_modified_recovery_evidence_is_not_reused(change):
    result = audit()
    text = TEXT
    if change == "text": text += " Información nueva."
    if change == "amount": result["entries"][0]["amount"] = 2500
    if change == "window": result["entries"][0]["attempts"][0]["inicio"] += 2
    if change == "evidence": result["entries"][0]["attempts"][1]["texto"] = "2500 pesos"
    if change == "shape": result["entries"] = "invalid"
    if change == "invalid_amount": result["entries"][0]["amount"] = [2450]
    if change == "invalid_anchor": result["entries"][0]["anchor_start"] = []
    if change == "schema": result["schema"] = 99
    assert not validated_entries(text, SEGMENTS, result)


def test_hostility_exception_cannot_waive_pending_audio_amount_review():
    flags = dict.fromkeys(("audio_verified", "interlocutor_hostile_or_lascivious", "prevented_script", "agent_professional"), True)
    result = A.shared_quality_decision({"amount_recovery_validation": {"review_required": True},
                                       "hostile_interlocutor_exception": flags}, 100, duration_seconds=90)
    assert result["clasificacion"] == "REVISAR"


def checkpoint(tmp_path):
    source = tmp_path/"batch.json"
    source.write_text(json.dumps({"items": [{"path": "C:/missing/synthetic.wav", "file_name": "synthetic.wav",
        "result": {"archivo": "synthetic.wav", "texto": TEXT, "segmentos": SEGMENTS, "duracion_segundos": 90},
        "relation": CONTEXT}]}), encoding="utf-8")
    return source


def test_checkpoint_recovery_preserves_source_and_exports_evidence_and_version(tmp_path):
    source = checkpoint(tmp_path)
    original = source.read_bytes()
    (tmp_path/"synthetic.wav").write_bytes(b"mock fixture; audio callback is simulated")
    service = SimpleNamespace(recover_missing_amounts=lambda *args: audit())
    result = recover_checkpoint_amounts(source, tmp_path, tmp_path/"new", service)
    assert result["recovered_amounts"] == 1 and result["outcomes"] == {"REVISAR": 1}
    assert source.read_bytes() == original
    saved = json.loads(Path(result["checkpoint"]).read_text())
    assert saved["items"][0]["result"]["texto"] == TEXT
    assert saved["reanalysis"]["whisper_executed"] is True
    book = load_workbook(result["report"], read_only=True, data_only=True)
    try:
        rows = list(book["RESULTADOS"].values)
        assert rows[1][rows[0].index("Monto Detectado")] == 2450
        assert rows[1][rows[0].index("Recuperación importe audio")] == "REVISAR"
    finally:
        book.close()
    # Un reanálisis posterior conserva la evidencia sin requerir el audio.
    next_result = reanalyze_checkpoint(result["checkpoint"], tmp_path/"again")
    again = json.loads(Path(next_result["checkpoint"]).read_text())
    assert again["items"][0]["analytics_metadata"]["negotiation_validation"]["monto_detectado"] == 2450


def test_missing_audio_generates_a_report_with_pending_windows(tmp_path):
    source = checkpoint(tmp_path)
    service = SimpleNamespace(recover_missing_amounts=lambda *args: pytest.fail("No model without audio"))
    result = recover_checkpoint_amounts(source, tmp_path/"absent", tmp_path/"new", service)
    assert result["recovered_amounts"] == 0 and result["pending_windows"] == 1
    assert result["outcomes"] == {"REVISAR": 1}


def test_existing_destination_is_not_overwritten(tmp_path):
    source = checkpoint(tmp_path)
    target = tmp_path/"used"; target.mkdir(); (target/"keep.txt").write_text("keep")
    with pytest.raises(ValueError, match="nueva y vacía"):
        recover_checkpoint_amounts(source, output_directory=target)
    assert (target/"keep.txt").read_text() == "keep"


def test_new_audio_path_runs_recovery_and_saves_original_transcript(tmp_path, monkeypatch):
    audio_path = tmp_path/"synthetic.wav"
    with wave.open(str(audio_path), "wb") as stream:
        stream.setparams((1, 2, 16000, 0, "NONE", "not compressed")); stream.writeframes(b"\0\0"*160)
    service = WhisperService()
    monkeypatch.setattr(service, "load_model", lambda **kwargs: None)
    monkeypatch.setattr(service, "_run_transcription", lambda **kwargs: (
        [SimpleNamespace(id=0, start=20, end=28, text=TEXT)],
        SimpleNamespace(duration=90, language="es", language_probability=1)))
    readings = iter(READINGS)
    service._model = SimpleNamespace(transcribe=lambda *args, **kwargs: (
        iter([SimpleNamespace(text=next(readings))]), None))
    monkeypatch.setattr("faster_whisper.audio.decode_audio", lambda *args, **kwargs: np.zeros(90*16000))
    result = service.transcribe_audio(audio_path, tmp_path/"output")
    assert result["texto"] == TEXT
    assert result["revision_transcripcion"] == "3.6.19-r14"
    assert result["recuperacion_importes"]["entries"][0]["amount"] == 2450
    assert Path(result["ruta_json"]).is_file()


def test_recovery_respects_automatic_language(monkeypatch):
    service = WhisperService()
    readings, languages = iter(READINGS), []
    def transcribe(*args, **kwargs):
        languages.append(kwargs["language"])
        return iter([SimpleNamespace(text=next(readings))]), None
    service._model = SimpleNamespace(transcribe=transcribe)
    monkeypatch.setattr("faster_whisper.audio.decode_audio", lambda *args, **kwargs: np.zeros(90*16000))
    result = service.recover_missing_amounts("synthetic.wav", TEXT, SEGMENTS, language="auto")
    assert result["entries"][0]["amount"] == 2450
    assert languages == [None, None]
