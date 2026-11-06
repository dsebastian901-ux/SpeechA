"""Ejemplos sintéticos derivados de la auditoría; sin datos personales."""
import pytest
from app.services.analytics_service import AnalyticsService as A


@pytest.mark.parametrize("report", [
    "Ya pagué 900 pesos por transferencia. Mande la captura de esa transferencia por WhatsApp.",
    "Lo pagué a través del banco. Ok, por transferencia. Mande la captura para registrar el pago.",
    "Ya realicé mi pago por transferencia. Envíe el comprobante al número que le dicto.",
])
def test_past_transfer_and_receipt_request_do_not_require_new_bank_instructions(report):
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. " + report, {"estatus_grabacion": "CONVENIO"})
    assert r["negotiation_validation"]["payment_confirmation_case"]
    assert not r["convenio_payment_validation"]["transfer_data_review"]
    assert "PEN_CONV_TRANSFER_REV" not in {p["id"] for p in r["penalties"]}


@pytest.mark.parametrize("instruction", [
    "Puede realizar una transferencia.", "Transfiera el resto mañana.",
    "Puede pagar por transferencia a la CLABE que le enviaré.",
])
def test_new_transfer_instruction_still_requires_authorized_data(instruction):
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. Ya pagué 900 pesos. " + instruction)
    assert r["convenio_payment_validation"]["transfer_data_review"]
    assert "PEN_CONV_TRANSFER_REV" in {p["id"] for p in r["penalties"]}


def test_past_payment_in_the_same_sentence_does_not_hide_a_new_transfer_instruction():
    r = A.calculate_basic_compliance("Ya pagué 900 pesos y puede realizar una transferencia por el resto.")
    assert r["convenio_payment_validation"]["transfer_data_review"]


def test_authorized_account_in_an_unrelated_past_report_does_not_authorize_a_new_instruction():
    r = A.calculate_basic_compliance(
        "Titular: Ya pagué a la cuenta 014320655030560466.\nGestor: Puede realizar otra transferencia.")
    assert r["convenio_payment_validation"]["transfer_data_review"]


def test_authorized_account_linked_to_current_transfer_instruction_is_kept():
    r = A.calculate_basic_compliance("Gestor: Puede realizar una transferencia a la CLABE Santander 014320655030560466.")
    assert not r["convenio_payment_validation"]["transfer_data_review"]
    assert r["convenio_payment_validation"]["authorized_transfer_instruction_confirmed"]


def test_past_payment_does_not_waive_customer_question_about_a_new_transfer():
    r = A.calculate_basic_compliance(
        "Titular: Ya pagué 900 pesos. ¿Puedo hacer, es una transferencia?\n"
        "Gestor: Correcto, desde su banco.")
    assert r["convenio_payment_validation"]["transfer_data_review"]


def test_past_payment_does_not_waive_a_conditional_future_transfer_option():
    r = A.calculate_basic_compliance("Ya pagué 900 pesos. Podría hacer la transferencia para el resto.")
    assert r["convenio_payment_validation"]["transfer_data_review"]


@pytest.mark.parametrize("speaker,critical", [("Gestor", True), ("Interlocutor", False)])
def test_accusation_of_lying_does_not_get_approved_as_a_payment_report(speaker, critical):
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. Ya pagué 900 pesos. " + speaker + ": Mentirosa.")
    assert r["final_result"] != "APROBADA"
    assert ("PEN_TRATO_CONFRONTACION" in {p["id"] for p in r["penalties"]}) is critical


def test_past_payment_does_not_waive_an_unauthorized_new_account():
    r = A.calculate_basic_compliance(
        "Ya pagué 900 pesos por transferencia. Deposite el resto a la cuenta Santander 765432109876.")
    assert "PEN_CONV_FRAUDE" in {p["id"] for p in r["penalties"]}
    assert r["final_result"] == "INCORRECTA"


def test_negated_transfer_instruction_is_not_bank_data_omission():
    r = A.calculate_basic_compliance("No puede realizar una transferencia. Puede pagar en Chedraui.")
    assert not r["convenio_payment_validation"]["transfer_data_review"]


@pytest.mark.parametrize("identity", ["Es nuestro proveedor.", "Lo conocí en una fiesta.",
                                     "Soy su compañero de trabajo.", "Soy su madre."])
def test_third_party_identity_alone_is_not_a_delivered_message(identity):
    r = A.calculate_basic_compliance("Habla MRS. " + identity,
                                      {"estatus_grabacion": "MENSAJE CON TERCERO"})
    assert not r["status_validation"]["detected_status"].startswith("MENSAJE")
    assert r["status_validation"]["evidence_method"] == "TERCERO_SIN_RECADO_CONFIRMADO"
    assert r["final_result"] == "REVISAR"


def test_confirmed_message_to_a_third_party_remains_detected():
    r = A.calculate_basic_compliance(
        "Habla MRS. Es nuestro proveedor. Dígale que se comunique al número de contacto. Le paso el recado.",
        {"estatus_grabacion": "MENSAJE CON TERCERO"})
    assert r["status_validation"]["matches"] is True
    assert r["status_validation"]["detected_status"] == "MENSAJE CON TERCERO"


def test_positive_answer_to_past_payment_question_is_a_report_not_a_future_agreement():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Su saldo es 36000 pesos. ¿Ya pudo realizar algún movimiento de pago? Sí. "
        "¿Qué día lo realizó? ¿Por qué cantidad? El sábado pasado por cinco mil. Mande el ticket para verificar.",
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO", "pago_minimo": "11000", "saldo_total": "36000"})
    n = r["negotiation_validation"]
    assert n["payment_confirmation_case"]
    assert n["prior_payment_total"] == 5000
    assert not n["commitment_confirmed"]
    assert r["status_validation"]["detected_status"] == "PAGO REPORTADO / ACLARACION"
    assert "PEN_SIN_INTENTO_NEGOCIACION" in {p["id"] for p in r["penalties"]}


def test_asr_puedo_requires_a_past_payment_followup():
    r = A.calculate_basic_compliance(
        "Soy yo. ¿Ya puedo realizar algún movimiento de pado? Sí. ¿Qué día lo realicé? ¿Por qué cantidad? "
        "El sábado pasado por cinco mil.")
    assert r["negotiation_validation"]["payment_already_made"]
    assert not A.calculate_basic_compliance("¿Ya puedo realizar su pago? Sí.")["negotiation_validation"]["payment_already_made"]


def test_reported_realice_then_distant_amount_is_not_replaced_by_announced_balance():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Su saldo vencido es 2000 pesos. Ya lo realicé. "
        "Fue hace unos días, no recuerdo cuándo, me comentaron que se vería reflejado. "
        "Hoy en la mañana lo pagué por la cantidad de 900 pesos.",
        {"estatus_grabacion": "CONVENIO", "pago_minimo": "700", "saldo_total": "2000"})
    assert r["negotiation_validation"]["prior_payment_total"] == 900
    assert r["negotiation_validation"]["prior_payment_covers_minimum"]


def test_ambiguous_saldo_pasado_phrase_is_not_a_new_announced_balance():
    r = A.calculate_basic_compliance(
        "Su saldo vencido es 36000 pesos. ¿Ya pudo realizar su pago? Sí. "
        "¿Por qué cantidad? Hace el saldo pasado 4, 5000.",
        {"pago_minimo": "11000", "saldo_total": "36000"})
    assert r["negotiation_validation"]["saldo_informado_detectado"] == 36000


@pytest.mark.parametrize("text", [
    "¿Ya pudo realizar su pago? No.",
    "¿Ya pudo realizar su pago? Sí puedo mañana.",
    "¿Ya pudo realizar su pago? Sí, creo.",
    "¿Puede realizar su pago mañana? Sí.",
    "Gestor: ¿Ya pudo realizar su pago? Sí.",
])
def test_negative_uncertain_future_or_agent_answer_is_not_a_completed_payment(text):
    assert not A.calculate_basic_compliance(text)["negotiation_validation"]["payment_already_made"]
