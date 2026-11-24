"""Segunda escucha focal: decisiones de la usuaria de 23/11/2026."""
from pathlib import Path

from app.services.context_audio_recovery import (
    needs_recovery, windows, collect, validate, reading_summary
)


def _metadata(code=None, contact="TITULAR"):
    return {
        "quality_contact_type": contact,
        "shared_classification": {
            "clasificacion": "REVISAR",
            "pending_alerts": [{"code": code}] if code else [],
        },
    }


def test_all_review_calls_have_a_recovery_purpose():
    assert needs_recovery(_metadata())
    assert needs_recovery(_metadata("RECEIPT_UNCERTAIN")) == {"financial"}
    assert needs_recovery(_metadata("HOME_WARNING_UNATTRIBUTED")) == {"safety"}
    assert "holder" in needs_recovery(_metadata("UNCERTAIN_DISCLOSURE", "CONTACTO NO DETERMINADO"))
    assert needs_recovery({
        "shared_classification": {"clasificacion": "APROBADO"},
        "quality_contact_type": "TITULAR",
    }) == set()


def test_financial_and_security_reading_windows_are_focal():
    data = {
        "duracion_segundos": 120,
        "segmentos": [
            {"inicio": 21, "texto": "Se solicita el comprobante"},
            {"inicio": 74, "texto": "Se anuncia visita domiciliaria"},
        ],
    }
    finance = windows(data, {"financial"})
    safety = windows(data, {"safety"})
    assert len(finance) == len(safety) == 1
    assert finance[0][1][0][0] < safety[0][1][0][0]


def _sample(tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"audio sintético sin clientes")
    data = {
        "archivo": audio.name, "texto": "¿Me puede comunicar con Persona Ejemplo? Sí.",
        "duracion_segundos": 90, "segmentos": [], "modelo": "small",
    }
    return audio, data, {"numero_de_tarjeta": "1234567890123456"}


def test_third_read_when_two_disagree_and_two_safe_identity_reads_agree(tmp_path):
    audio, data, relation = _sample(tmp_path)
    texts = [
        "¿Me puede comunicar con Persona Ejemplo? Dígame, ¿quién llama?",
        "¿Me puede comunicar con Persona Ejemplo? Sí, soy yo.",
        "¿Me puede comunicar con Persona Ejemplo? Sí, soy yo.",
    ]
    attempts = []
    def reader(start, end, beam):
        attempts.append((start,end,beam))
        return {"text": texts[len(attempts)-1], "segments": []}

    record = collect(audio, data, relation, _metadata(contact="CONTACTO NO DETERMINADO"), reader, "small")
    assert len(attempts) == 3
    assert attempts[-1][-1] == 8
    outcome = validate(record, data, relation, audio)
    assert outcome["valid"] and outcome["holder"]
    assert len(outcome["readings"]) == 3
    assert len(reading_summary(record)) == 3


def test_third_read_does_not_overrule_explicit_third_party(tmp_path):
    audio, data, relation = _sample(tmp_path)
    texts = [
        "¿Me puede comunicar con Persona Ejemplo? Soy su hermana, no está.",
        "¿Me puede comunicar con Persona Ejemplo? Sí, soy yo.",
        "¿Me puede comunicar con Persona Ejemplo? Sí, soy yo.",
    ]
    count = [0]
    def reader(start,end,beam):
        text = texts[count[0]]
        count[0] += 1
        return {"text": text, "segments": []}
    record = collect(audio,data,relation,
                     _metadata(contact="CONTACTO NO DETERMINADO"),reader,"small")
    outcome = validate(record,data,relation,audio)
    assert len(record["groups"][0]["attempts"]) == 3
    assert not outcome["holder"]


def test_focal_read_is_visible_but_does_not_validate_financial_agreement(tmp_path):
    audio,data,relation=_sample(tmp_path)
    data["segmentos"]=[{"inicio": 13, "texto": "debe pagar mañana"}]
    count=[0]
    texts=["Se informa un pago pendiente del mes", "Se informa un pago pendiente para mañana",
           "Se informa un pago pendiente del mes"]
    def reader(start,end,beam):
        index=count[0];count[0]+=1
        return {"text":texts[index], "segments":[]}
    record=collect(audio,data,relation,_metadata("PAYMENT_OUTCOME_NOT_CONFIRMED"),reader,"small")
    result=validate(record,data,relation,audio)
    assert len(record["groups"][0]["attempts"])==3
    assert result["review_required"]
    assert not result["holder"] and not result["callback"]
    assert result["reason"]
    assert len(result["readings"])==3


def test_reading_record_cannot_be_reused_for_another_audio(tmp_path):
    audio,data,relation=_sample(tmp_path)
    def reader(start,end,beam):
        return {"text":"¿Me puede comunicar con Persona Ejemplo? Sí, soy yo.", "segments":[]}
    record=collect(audio,data,relation,
                   _metadata(contact="CONTACTO NO DETERMINADO"),reader,"small")
    audio.write_bytes(b"audio diferente")
    assert not validate(record,data,relation,audio)["valid"]


def test_critical_issues_still_prevent_approval_after_focal_listening():
    from app.services.quality_decision import evaluate_quality
    metadata={
        "shared_classification": {"clasificacion":"REVISAR"},
        "context_audio_validation": {
            "present":True, "valid":True, "review_required":True,
            "reason":"Relectura pendiente de atribución", "risks":[],
            "readings":[{"purpose":"safety","attempt":1,"text":"visita"}],
        },
        "privacy_validation":{"confirmed_disclosure":True},
    }
    decision=evaluate_quality(metadata,100,80,90)
    assert not decision["aprobado"]
    assert decision["clasificacion"]=="FALLA_GRAVE"
