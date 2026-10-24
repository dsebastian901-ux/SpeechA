"""Casos sintéticos: expectativas de seguridad explícitas, sin datos personales."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import assess_recado, evidence_units
from app.services.payment_reference_validation import find_reference


def compliance(text, **context):
    return A.calculate_basic_compliance(text, context)


def penalties(result):
    return {p["id"] for p in result["penalties"]}


@pytest.mark.parametrize("phrase", [
    "Soy su hermana.", "Es mi esposa.", "Soy su madre.",
    "Es mi sobrino.", "Es esposa de mi primo, no vive aquí.",
])
@pytest.mark.parametrize("status", ["RECADO REF1", "RECADO REF2", "RECADO REF 1", "MENSAJE CON FAMILIAR"])
def test_recado_equivalence_requires_actual_message(phrase, status):
    r = compliance(phrase + " Habla MRS. Dígale que se comunique al número de contacto. Le paso el recado.",
                   estatus_grabacion=status)
    assert r["status_validation"]["matches"] is True
    assert r["status_validation"]["valid"] is True
    assert r["status_validation"]["recado_evidence"]["confirmed_recado"] is True
    assert "PEN_CONV_LUGARES" not in penalties(r)
    assert "PEN_CONV_WHATS" not in penalties(r)


@pytest.mark.parametrize("phrase", [
    "¿Es su hermana?", "¿Soy su hermano?", "No soy su hermano.",
    "No es mi esposa.", "No sé si es mi hermano.", "Creo que es mi hermano.",
    "Tal vez sea mi hermano.", "Es mi hermano, ¿verdad?", "No lo conozco.",
    "Gestor: Es mi esposa.", "Es su esposa.",
])
def test_questions_negations_and_agent_words_do_not_confirm_family(phrase):
    r = compliance(phrase + " Dígale que se comunique. Lo anoto.", estatus_grabacion="RECADO REF1")
    assert not r["status_validation"]["recado_evidence"]["confirmed_recado"]
    assert r["final_result"] != "APROBADA"
    assert not assess_recado(phrase)["family"]


@pytest.mark.parametrize("answer", [
    "Gracias por recibir el recado.", "¿Lo anoto?", "No lo anoto.",
    "No quiero recibir el recado.", "No le voy a pasar el recado.",
    "Gestor: Lo anoto.", "Diga que le paso el recado.",
])
def test_recado_acceptance_is_not_fabricated(answer):
    r = compliance("Soy su hermana. Dígale que se comunique. " + answer,
                   estatus_grabacion="RECADO REF2")
    assert not r["status_validation"]["recado_evidence"]["confirmed_recado"]
    assert r["final_result"] == "REVISAR"


def test_asking_to_write_does_not_prove_message_was_delivered():
    r = compliance("Soy su hermana. ¿Tiene dónde anotar un recado? Lo anoto.",
                   estatus_grabacion="RECADO REF1")
    assert not r["status_validation"]["recado_evidence"]["confirmed_recado"]


@pytest.mark.parametrize("financial", [
    "Tiene una deuda de 1500 pesos.", "Presenta dos mensualidades vencidas.",
    "Tiene tres meses de atraso.", "Su saldo pendiente es de 1500 pesos.",
    "Tiene una tarjeta.", "Su tarjeta es 1234567890123456.",
])
def test_confirmed_agent_disclosure_to_family_remains_critical(financial):
    r = compliance("Familiar: Soy su madre.\nGestor: " + financial,
                   estatus_grabacion="RECADO REF1")
    assert "PEN003" in penalties(r)
    p = next(p for p in r["penalties"] if p["id"] == "PEN003")
    assert p["invalidates"] and p["points"] == 100
    assert r["privacy_validation"]["confirmed_disclosure"]
    assert r["final_result"] == "INCORRECTA"


@pytest.mark.parametrize("speaker", [None, "SPEAKER_00", "SPEAKER_01"])
def test_unknown_speaker_is_review_not_false_critical(speaker):
    text = "Soy su madre. Tiene una deuda de 1500 pesos."
    segments = [{"texto": text, "speaker": speaker, "inicio": 0, "fin": 12}]
    r = compliance(text, estatus_grabacion="RECADO REF1", _segments=segments)
    assert "PEN003" not in penalties(r)
    assert r["privacy_validation"]["review_required"]
    assert r["final_result"] == "REVISAR"


def test_customer_financial_words_are_not_agent_disclosure():
    r = compliance("Familiar: Soy su madre. Su saldo pendiente es de 1500 pesos.\nGestor: Gracias.")
    assert "PEN003" not in penalties(r)
    assert not r["privacy_validation"]["confirmed_disclosure"]


@pytest.mark.parametrize("phrase", ["Saldo policía.", "Propuestas de pago.", "Atención de MRS."])
def test_isolated_words_do_not_trigger_pen003(phrase):
    r = compliance("Soy su madre. " + phrase, estatus_grabacion="RECADO REF1")
    assert "PEN003" not in penalties(r)
    assert not r["privacy_validation"]["review_required"]


def test_excel_label_does_not_confirm_actual_third_party():
    r = compliance("Gestor: Tiene una deuda de 1500 pesos.", estatus_grabacion="RECADO REF1")
    assert "PEN003" not in penalties(r)
    assert r["privacy_validation"]["review_required"]


def test_transfer_to_holder_is_not_disclosure_to_previous_family():
    r = compliance("Familiar: Soy su madre.\nTitular: Soy el titular.\nGestor: Tiene una deuda de 1500 pesos.")
    assert "PEN003" not in penalties(r)
    assert not r["privacy_validation"]["confirmed_disclosure"]


def test_attributed_segment_preserves_real_times():
    text = "Soy su madre. Tiene una deuda de 1500 pesos."
    segments = [{"texto": "Soy su madre.", "speaker_role": "familiar", "inicio": 1, "fin": 3},
                {"texto": "Tiene una deuda de 1500 pesos.", "speaker_role": "gestor", "inicio": 4, "fin": 9}]
    r = compliance(text, _segments=segments)
    evidence = next(e for e in r["privacy_validation"]["evidence"] if e["confirmed"])
    assert evidence["speaker_role"] == "GESTOR"
    assert (evidence["start"], evidence["end"]) == (4, 9)


def test_unrelated_labelled_segment_cannot_invent_disclosure():
    units = evidence_units("Hola.", [{"text": "Tiene deuda.", "role": "gestor"}])
    assert all(u["speaker_role"] != "GESTOR" for u in units)


@pytest.mark.parametrize("reference", [
    "12 34 56 78 90 12 34 56", "1234567890123456", "1234-5678-9012-3456",
    "doce treinta y cuatro cincuenta y seis setenta y ocho noventa doce treinta y cuatro cincuenta y seis",
    "uno dos tres cuatro cinco seis siete ocho nueve cero uno dos tres cuatro cinco seis",
])
def test_complete_reference_matches_all_sixteen_digits(reference):
    r = find_reference("Referencia de pago: " + reference, "1234567890123456")
    assert {d["digits"] for d in r["detected"]} == {"1234567890123456"}
    assert not r["incorrect"] and not r["requires_review"]


def test_complete_card_without_numero_prefix_is_detected():
    r = find_reference("Su tarjeta es 1234567890123456.", "1234567890123456")
    assert [d["digits"] for d in r["detected"]] == ["1234567890123456"]


def test_single_zero_words_are_not_each_padded_to_two_zeros():
    r = find_reference("Referencia: doce treinta y cuatro cincuenta y seis cero cero setenta y ocho noventa doce treinta y cuatro")
    assert [d["digits"] for d in r["detected"]] == ["1234560078901234"]


@pytest.mark.parametrize("phrase", ["Voy a hablar con mi esposo para conseguir dinero.",
                                    "Con mi hija intenté bajar la aplicación."])
def test_mentioning_own_relative_does_not_make_holder_a_third_party(phrase):
    r = compliance("Habla MRS. Soy yo. " + phrase, estatus_grabacion="CONVENIO")
    assert r["contact_type"] == "TITULAR"
    assert "PEN010" not in penalties(r)


@pytest.mark.parametrize("suffix", [
    "teléfono 55 12 34 56 78", "saldo 12 34 56 78 90 12 34 56 pesos",
    "fecha 12 10 20 26 12 10 20 26", "12 34 56 78 90 12 34 56 pesos",
])
def test_phone_money_and_dates_are_not_references(suffix):
    assert not find_reference("Referencia: " + suffix)["detected"]


def test_repeated_pairs_never_generate_sliding_fake_cards():
    r = find_reference("Referencia: 12 12 34 34 56 56 78 78 90 90 12 12 34 34 56 56", "1234567890123456")
    assert not r["detected"] and not r["incorrect"]
    assert r["ambiguous"] and r["requires_review"]


@pytest.mark.parametrize("expected", ["", "1234", "9999999999999999"])
def test_missing_or_wrong_excel_card_blocks_approval(expected):
    r = compliance("Habla MRS. Referencia de pago: 12 34 56 78 90 12 34 56.", numero_de_tarjeta=expected)
    assert r["card_validation"]["result"].startswith("REVISAR -")
    assert r["final_result"] == "REVISAR"


def test_new_evidence_survives_analytics_metadata_and_shared_gate():
    t = TranscriptionModel("synthetic.wav", "synthetic.wav",
        "Habla MRS. Soy su madre. Tiene una deuda de 1500 pesos.", duration_seconds=90)
    a = A.analyze_transcription(t)
    assert a.metadata["privacy_validation"]["review_required"]
    assert "payment_reference_validation" in a.metadata
    assert A.shared_quality_decision(a.metadata, 100, duration_seconds=90)["clasificacion"] == "REVISAR"


@pytest.mark.parametrize("role", ["gestor", "interlocutor", "SPEAKER_00"])
def test_profanity_at_end_is_detected_with_attribution_and_time(role):
    text = "Habla MRS. Gracias por su tiempo. Mierda."
    r = compliance(text, _segments=[{"texto": "Mierda.", "speaker": role, "inicio": 80, "fin": 81}], _duration_seconds=82)
    assert r["final_result"] != "APROBADA"
    evidence = r["treatment_validation"]["offensive_language_evidence"]
    assert evidence and (evidence[-1]["start"], evidence[-1]["end"]) == (80, 81)
    assert ("PEN_GROSERIA_GESTOR" in penalties(r)) == (role == "gestor")


def test_final_text_outside_segments_is_still_checked():
    r = compliance("Habla MRS. Gracias. Mierda.", _segments=[{"texto": "Habla MRS.", "inicio": 0, "fin": 1}])
    assert r["checks"]["groseria_bloquea_aprobacion"]
    assert r["final_result"] == "REVISAR"


def test_prior_mistreatment_still_blocks_approval():
    r = compliance("Habla MRS. Me trataron mal. Gracias.")
    assert "PEN_QUEJA_MALTRATO" in penalties(r)
    assert r["final_result"] != "APROBADA"


def test_payment_capture_instruction_does_not_identify_a_third_party():
    r = compliance("Habla MRS. Puede tomar una captura de pantalla del comprobante.", estatus_grabacion="CONVENIO")
    assert r["contact_type"] == "CONTACTO NO DETERMINADO"
    assert "PEN010" not in penalties(r)
    assert r["final_result"] != "APROBADA"


def test_arco_omission_still_blocks_unknown_debtor():
    r = compliance("Habla MRS. No lo conozco. Número equivocado.", estatus_grabacion="NO CONOCEN A DEUDOR")
    assert not r["status_validation"]["valid"]
    assert r["status_validation"]["arco_process"] is False
    assert r["final_result"] != "APROBADA"


def test_convenio_still_requires_two_authorized_places():
    r = compliance("Habla MRS. Soy yo. Confirmo su convenio. Voy a pagar mañana 500 pesos.",
                   estatus_grabacion="CONVENIO", asignacion="1PV", pago_minimo="500")
    assert "PEN_CONV_LUGARES" in penalties(r)
    assert r["final_result"] != "APROBADA"


@pytest.mark.parametrize("mora", ["1PV", "2PV"])
def test_home_collection_threat_remains_blocked(mora):
    r = compliance("Habla MRS. Soy yo. Vamos a realizar una visita a su domicilio para cobrar.", asignacion=mora)
    assert r["negotiation_validation"]["prohibited_visit_wording"]
    assert r["final_result"] != "APROBADA"
