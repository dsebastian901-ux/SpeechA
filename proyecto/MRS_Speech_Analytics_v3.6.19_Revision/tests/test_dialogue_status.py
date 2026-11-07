"""Casos sintéticos de identificación y estatus, sin etiquetas como evidencia."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import holder_confirmation, payment_commitment


@pytest.mark.parametrize("opening", [
    "¿Me podré comunicar con Persona de Ejemplo? Sí, ella habla.",
    "¿Me puede comunicar, por favor, con Persona de Ejemplo? Sí, con ella habla.",
    "Estoy buscando a Persona de Ejemplo. Sí, con ella habla.",
    "¿Es usted el caballero Persona de Ejemplo? Sí, dígame.",
    "¿Me puede comunicar con Persona de Ejemplo? Sí, qué tal. Buen día. Mucho gusto.",
    "¿Me puede comunicar con Persona de Ejemplo? Sí, qué tal. Bueno día. Mucho gusto.",
])
def test_natural_identification_variants(opening):
    assert holder_confirmation(opening)["confirmed"]


@pytest.mark.parametrize("text", [
    "¿Es usted familiar de Persona de Ejemplo? Sí.",
    "¿Es usted quien va a pagar? Sí.",
    "¿Es usted su madre? Sí.",
    "¿Es usted médico? Sí.",
    "¿Me puede comunicar con Persona de Ejemplo? Sí, espere, se lo comunico.",
    "Gestor: ¿Es usted Persona de Ejemplo? Sí.",
    "¿Me puede comunicar con Persona de Ejemplo? Me presento, habla MRS.",
])
def test_questions_and_handoffs_do_not_invent_identity(text):
    assert not holder_confirmation(text)["confirmed"]


def test_unknown_acoustic_chunks_do_not_hide_third_party_identity():
    text = "¿Es usted el señor Persona de Ejemplo? Sí. Lo conocí en una fiesta nada más."
    r = A.calculate_basic_compliance(text, {"_segments": [
        {"texto": "¿Es usted el señor Persona de Ejemplo? Sí. Lo conocí", "inicio": 0, "fin": 5},
        {"texto": "en una fiesta nada más.", "inicio": 5, "fin": 8}]})
    assert r["contact_type"] == "TERCERO"


@pytest.mark.parametrize("reply", ["No se encuentra.", "Está trabajando."])
def test_absence_confirms_intermediary_without_inventing_family(reply):
    r = A.calculate_basic_compliance("¿Me puede comunicar con Persona de Ejemplo? " + reply,
                                      {"estatus_grabacion": "MENSAJE CON FAMILIAR"})
    assert r["contact_type"] == "TERCERO"
    assert not r["status_validation"]["recado_evidence"]["family_phrases"]
    assert r["final_result"] == "REVISAR"


def test_initial_absence_does_not_override_later_holder_confirmation():
    r = A.calculate_basic_compliance(
        "¿Me puede comunicar con Persona de Ejemplo? No se encuentra. Espere, le paso. "
        "Estoy buscando a Persona de Ejemplo. Sí, con ella habla.")
    assert r["contact_type"] == "TITULAR"


def test_identified_intermediary_without_message_is_not_approved_without_excel():
    r = A.calculate_basic_compliance("Habla MRS. ¿Me puede comunicar con Persona de Ejemplo? No se encuentra.")
    assert r["contact_type"] == "TERCERO"
    assert r["final_result"] == "REVISAR"


def test_missing_application_is_not_a_statement_that_the_holder_is_absent():
    r = A.calculate_basic_compliance("Habla MRS. No se encuentra la aplicación en mi teléfono.")
    assert r["contact_type"] == "CONTACTO NO DETERMINADO"


@pytest.mark.parametrize("reply", ["Con dos mil pesos hoy.", "Dos mil pesos."])
def test_explicit_amount_response_can_confirm_future_payment(reply):
    c = payment_commitment("¿Qué cantidad confirmaría pagar el día de hoy? " + reply)
    assert c["accepted"]


@pytest.mark.parametrize("reply", ["Dos mil pesos, creo.", "A lo mejor mil pesos.", "No tengo esa cantidad."])
def test_uncertain_amount_response_does_not_confirm_payment(reply):
    c = payment_commitment("¿Qué cantidad confirmaría pagar el día de hoy? " + reply)
    assert not c["accepted"]


def test_payment_report_question_does_not_create_future_commitment():
    assert not payment_commitment("¿Qué cantidad pagó ayer? Dos mil pesos.")["accepted"]
    assert not payment_commitment("¿Cuenta con WhatsApp? Sí.")["accepted"]


def test_known_agent_cannot_accept_an_own_offer():
    assert not payment_commitment("Gestor: ¿Qué cantidad confirmaría pagar hoy? Dos mil pesos.")["accepted"]


def test_new_accepted_offer_replaces_prior_condition():
    c = payment_commitment(
        "Si me da tiempo hoy, sí. Le coloco la fecha del pago para mañana. "
        "¿Cuánto me dices? Dos mil pesos. Ok, está bien.")
    assert c["accepted"]


def test_unclear_acknowledgement_does_not_accept_a_new_offer():
    c = payment_commitment("Si me da tiempo hoy, sí. Le coloco el pago mañana. Muy bien. Ok.")
    assert not c["accepted"]


@pytest.mark.parametrize("reply", [
    "Me interesa el descuento, pero yo creo a principios de noviembre.",
    "Haré lo posible por juntar esa cantidad.",
    "No tengo esa cantidad.",
])
def test_explicit_uncertain_payment_without_firm_commitment_matches_no_date(reply):
    text = "Habla MRS. ¿Es usted? Sí. Le ofrecemos una opción de pago. " + reply
    t = TranscriptionModel("synthetic.wav", "synthetic.wav", text, duration_seconds=90)
    a = A.analyze_transcription(t, {"estatus_grabacion": "NO DEFINE FECHA DE PAGO"})
    s = a.metadata["status_validation"]
    assert s["matches"] is True and s["detected_status"] == "NO DEFINE FECHA DE PAGO"
    assert s["evidence"]
    assert a.metadata["final_result"] == "APROBADO"


def test_silence_after_proposal_is_not_no_date_or_a_payment_commitment():
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. Le ofrecemos un pago de 600 pesos mañana.",
                                      {"estatus_grabacion": "NO DEFINE FECHA DE PAGO"})
    assert r["status_validation"]["matches"] is None
    assert r["final_result"] == "REVISAR"


def test_known_agent_uncertainty_is_not_customer_refusal():
    r = A.calculate_basic_compliance(
        "Titular: Soy el titular.\nGestor: No tengo esa cantidad. Haré lo posible por juntar dinero.",
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO"})
    assert r["status_validation"]["matches"] is None


def test_matching_status_does_not_waive_prior_mistreatment():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Me trataron mal. Le ofrecemos una opción de pago. No tengo esa cantidad.",
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO"})
    assert r["status_validation"]["matches"] is True
    assert r["final_result"] == "REVISAR"


@pytest.mark.parametrize("phrase", ["¿Sabes escuchar?", "Aprende cómo funciona una tarjeta.",
                                    "Me está poniendo muchas trabas."])
def test_matching_status_does_not_waive_condescending_language(phrase):
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Le ofrecemos una opción de pago. No tengo esa cantidad. " + phrase,
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO"})
    assert r["status_validation"]["matches"] is True
    assert r["treatment_validation"]["confrontation_review_required"]
    assert r["final_result"] == "REVISAR"


def test_payment_store_is_not_a_date_and_date_evidence_matches_value():
    details = A._extract_payment_promise_date_details(
        "Me comprometo a pagar 600 pesos mañana. Puede pagarlo en 7-11 o Círculo K.", "2026-10-13")
    assert details["date"].isoformat() == "2026-10-14"
    assert details["text"] == "manana"
    assert A._extract_payment_promise_date("Puede pagar en 7-11.", "2026-10-13") is None


def test_numeric_date_is_kept_when_explicitly_used_as_payment_date():
    details = A._extract_payment_promise_date_details("El pago será para el 7/11 de este año.", "2026-10-13")
    assert details["date"].isoformat() == "2026-11-07"
    assert details["text"] == "7/11"


def test_spoken_date_is_detected_with_matching_evidence():
    details = A._extract_payment_promise_date_details("Me comprometo a pagar el veinte de octubre.", "2026-10-13")
    assert details["date"].isoformat() == "2026-10-20"
    assert details["text"] == "veinte de octubre"


def test_two_equal_installments_are_both_counted_without_prior_proposal():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Le ofrecimos un pago de 600 pesos hoy. "
        "Ahora serán dos pagos por 900 pesos. Primer pago mañana y segundo pago el veinte de octubre. "
        "Me comprometo a pagar dos pagos por 900 pesos. Puede pagar en Chedraui y Farmacias del Ahorro. "
        "Envíe su comprobante por WhatsApp.",
        {"estatus_grabacion": "CONVENIO", "fecha": "2026-10-13", "pago_minimo": "500", "saldo_total": "1800"})
    n = r["negotiation_validation"]
    assert n["montos_multipago"] == [900, 900]
    assert n["monto_detectado"] == 1800
    assert n["promise_date_text"] == "veinte de octubre"


def test_hybrid_amount_is_not_added_a_second_time_as_its_suffix():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Primer pago por mil pesos hoy y segundo pago por mil 900 pesos mañana. "
        "Me comprometo a pagar esos dos pagos.",
        {"estatus_grabacion": "CONVENIO", "fecha": "2026-10-13", "pago_minimo": "2500", "saldo_total": "4000"})
    n = r["negotiation_validation"]
    assert n["montos_multipago"] == [1000, 1900]
    assert n["monto_detectado"] == 2900


def test_contradictory_installment_amounts_block_approval():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Primer pago por mil pesos hoy y un pago más por mil 900 pesos mañana. "
        "El primer pago por mil pesos hoy y el segundo por mil 800 pesos mañana. "
        "Me comprometo a pagar esos dos pagos. Puede pagar en Chedraui y Farmacias del Ahorro. "
        "Envíe su comprobante por WhatsApp.",
        {"estatus_grabacion": "CONVENIO", "fecha": "2026-10-13", "pago_minimo": "2500", "saldo_total": "4000"})
    n = r["negotiation_validation"]
    assert n["monto_detectado"] == 2800
    assert n["installment_validation"]["review_required"]
    assert r["final_result"] == "REVISAR"


def test_an_earlier_installment_offer_does_not_override_a_different_accepted_amount():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Podemos ofrecer dos pagos por 900 pesos. "
        "Me comprometo a pagar 600 pesos mañana. Puede pagar en Chedraui y Farmacias del Ahorro. "
        "Envíe su comprobante por WhatsApp.",
        {"estatus_grabacion": "CONVENIO", "fecha": "2026-10-13", "pago_minimo": "500", "saldo_total": "2000"})
    assert r["negotiation_validation"]["installment_validation"]["review_required"]
    assert r["final_result"] == "REVISAR"


def test_matching_status_does_not_hide_a_different_announced_balance():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Presenta un saldo vencido por la cantidad de 1300 pesos. "
        "Le ofrecemos una opción de pago de 900 pesos. No tengo esa cantidad.",
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO", "saldo_total": "1600", "pago_minimo": "700"})
    n = r["negotiation_validation"]
    assert r["status_validation"]["matches"] is True
    assert n["saldo_informado_detectado"] == 1300
    assert n["monto_detectado"] == 900
    assert n["review_required"]
    assert r["final_result"] == "REVISAR"


def test_missing_discount_amount_is_reviewed_even_if_no_payment_date_was_agreed():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Se le está ofreciendo un descuento. Haré lo posible por juntar esa cantidad.",
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO"})
    assert r["status_validation"]["matches"] is True
    assert r["negotiation_validation"]["review_required"]
    assert r["final_result"] == "REVISAR"


def test_split_audio_chunks_do_not_hide_missing_discount_amount():
    text = "Habla MRS. Soy yo. Se le está ofreciendo un descuento. Haré lo posible por juntar esa cantidad."
    r = A.calculate_basic_compliance(text, {
        "estatus_grabacion": "NO DEFINE FECHA DE PAGO", "_segments": [
            {"texto": "Habla MRS. Soy yo. Se le está ofreciendo", "inicio": 0, "fin": 5},
            {"texto": "un descuento. Haré lo posible por juntar esa cantidad.", "inicio": 5, "fin": 10}]})
    assert r["status_validation"]["matches"] is True
    assert r["negotiation_validation"]["review_required"]
    assert r["final_result"] == "REVISAR"


def test_question_after_a_declared_offer_does_not_hide_missing_amount():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Se le está ofreciendo un descuento, ¿podemos contemplar ese pago? "
        "Haré lo posible por juntar esa cantidad.",
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO"})
    assert r["status_validation"]["matches"] is True
    assert r["negotiation_validation"]["review_required"]
    assert r["final_result"] == "REVISAR"


def test_excel_does_not_put_contact_type_in_the_detected_status_column():
    from app.services.batch_report_service import BatchReportService
    t = TranscriptionModel("synthetic.wav", "synthetic.wav",
        "Habla MRS. Soy yo. Me comprometo a pagar 600 pesos mañana. "
        "Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.",
        duration_seconds=90)
    a = A.analyze_transcription(t, {"estatus_grabacion": "CONVENIO", "fecha": "2026-10-13"})
    row = BatchReportService._row_from_item({"path": "synthetic.wav", "result": {"texto": t.text},
          "analytics": a.to_dict(), "analytics_metadata": a.metadata,
          "classification": a.metadata["shared_classification"], "compliance_score": a.compliance_score})
    assert row["Estatus detectado IA"] == "CONVENIO"
    assert row["Interlocutor detectado"] == "TITULAR"
    assert row["Evidencia estatus"]
    assert row["Método detección estatus"] == "COMPROMISO_ACEPTADO_CON_FECHA"
