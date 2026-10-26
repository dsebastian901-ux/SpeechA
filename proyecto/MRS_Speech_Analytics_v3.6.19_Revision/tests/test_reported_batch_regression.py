"""Casos sintéticos derivados de fallos del lote informado; sin datos reales."""
import pytest

from app.services.analytics_service import AnalyticsService as A


@pytest.mark.parametrize("opening", [
    "¿Me puede comunicar con Persona de Ejemplo? Ella habla.",
    "¿Me puede comunicar con Persona de Ejemplo? Sí, dígame.",
    "¿Es usted el caballero? Así es.",
    "¿Es usted? Sí.",
])
def test_natural_holder_confirmation_is_detected(opening):
    r = A.calculate_basic_compliance(opening + " Habla MRS. Mi tarjeta ya la pagué.")
    assert r["contact_type"] == "TITULAR"


@pytest.mark.parametrize("answer", ["No se encuentra.", "No, soy su esposa.",
                                   "Sí, dígame, pero no está aquí."])
def test_contact_question_does_not_turn_intermediary_into_holder(answer):
    r = A.calculate_basic_compliance("¿Me puede comunicar con Persona de Ejemplo? " + answer)
    assert r["contact_type"] != "TITULAR"


def test_telephone_greeting_is_not_proof_of_agent_abandonment():
    r = A.calculate_basic_compliance("¿Bueno? ¿Bueno, bueno?", {
        "_segments": [{"texto": "¿Bueno? ¿Bueno, bueno?", "inicio": 0, "fin": 8}],
        "_duration_seconds": 108})
    assert r["final_result"] == "REVISAR"
    assert not any(p["id"] == "PEN_ABANDONO_GESTOR" and p["invalidates"] for p in r["penalties"])


def test_refusing_liquidation_is_not_offering_liquidation():
    r = A.calculate_basic_compliance("Gestor: No puede liquidar dado que solamente cubre la mensualidad vencida.",
                                      {"asignacion": "1PV"})
    assert not r["negotiation_validation"]["liquidation_detected"]
    assert "PEN004" not in {p["id"] for p in r["penalties"]}


def test_card_reference_near_bank_names_is_not_unauthorized_bank_account():
    r = A.calculate_basic_compliance(
        "Soy yo. Habla MRS. En relación a la cuenta con terminación 1234. Puede pagar en Santander. "
        "Le dicto la referencia de tarjeta: 1234 5678 9012 3456.",
        {"estatus_grabacion": "CONVENIO", "numero_de_tarjeta": "1234567890123456"})
    assert "PEN_CONV_FRAUDE" not in {p["id"] for p in r["penalties"]}


def test_explicit_wrong_bank_account_still_blocks():
    r = A.calculate_basic_compliance("Gestor: Deposite a la cuenta Santander 765432109876.")
    assert "PEN_CONV_FRAUDE" in {p["id"] for p in r["penalties"]}


def test_payment_places_do_not_depend_on_whisper_chunk_boundaries():
    text = "Puede pagar en Chedraui y Farmacias del Ahorro."
    r = A.calculate_basic_compliance(text, {"estatus_grabacion": "CONVENIO", "_segments": [
        {"texto": "Puede pagar en", "inicio": 0, "fin": 1},
        {"texto": "Chedraui y", "inicio": 1, "fin": 2},
        {"texto": "Farmacias del Ahorro.", "inicio": 2, "fin": 3}]})
    assert r["convenio_payment_validation"]["authorized_places_count"] == 2


def test_accepted_payment_does_not_require_literal_confirmo_convenio():
    r = A.calculate_basic_compliance(
        "Habla MRS. ¿Es usted el titular? Así es. "
        "¿Podemos contemplar su pago de 600 pesos el 23 de octubre de 2026? Sí, de acuerdo. "
        "Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.",
        {"estatus_grabacion": "CONVENIO", "fecha": "2026-10-20", "vencimiento": "2026-10-25",
         "pago_minimo": "500", "saldo_total": "2000", "asignacion": "1PV", "corte": "3"})
    assert r["status_validation"]["detected_status"] == "CONVENIO"
    assert r["status_validation"]["matches"] is True
    assert r["final_result"] == "APROBADA"


def test_holder_without_date_can_pass_quality_when_negotiation_was_attempted():
    r = A.calculate_basic_compliance(
        "Habla MRS. ¿Es usted? Sí. Le ofrecemos una opción de pago. No puedo confirmar una fecha.",
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO"})
    assert r["status_validation"]["matches"] is True
    assert r["final_result"] == "APROBADA"


def test_rejected_proposal_does_not_create_a_payment_commitment():
    r = A.calculate_basic_compliance(
        "Habla MRS. ¿Es usted? Sí. Le ofrecemos un convenio pagando mañana. No tengo esa cantidad.",
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO", "fecha": "2026-10-20"})
    assert not r["negotiation_validation"]["commitment_confirmed"]
    assert r["status_validation"]["detected_status"] == "NO DEFINE FECHA DE PAGO"


def test_written_seven_eleven_and_payment_pronoun_are_supported():
    r = A.calculate_basic_compliance("Puede pagarlo en 7-11 o Círculo K.", {"estatus_grabacion": "CONVENIO"})
    assert r["convenio_payment_validation"]["authorized_places_count"] == 2


def test_later_conditional_does_not_confirm_firm_payment_promise():
    r = A.calculate_basic_compliance(
        "Soy yo. ¿Podemos contemplar su pago mañana? Sí. Pues si me da tiempo.",
        {"estatus_grabacion": "CONVENIO", "fecha": "2026-10-20"})
    assert not r["negotiation_validation"]["commitment_confirmed"]
    assert r["negotiation_validation"]["commitment_evidence"]["conditional"]


def test_contextual_smr_requires_company_presentation():
    assert A.calculate_basic_compliance("Habla consultor SMR.")["checks"]["identifica_mrs"]
    assert not A.calculate_basic_compliance("Mi código es SMR.")["checks"]["identifica_mrs"]


def test_payment_question_and_negative_answer_are_not_a_completed_payment():
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. ¿Ya realizó su pago? No.", {"estatus_grabacion": "CONVENIO"})
    assert not r["negotiation_validation"]["payment_confirmation_case"]
    assert "PEN_CONV_LUGARES" in {p["id"] for p in r["penalties"]}


def test_known_agent_cannot_answer_own_identity_or_payment_question():
    r = A.calculate_basic_compliance("Gestor: ¿Es usted? Sí. ¿Podemos contemplar su pago mañana? Sí.")
    assert r["contact_type"] != "TITULAR"
    assert not r["negotiation_validation"]["commitment_confirmed"]


@pytest.mark.parametrize("instruction", [
    "Una vez que realice el pago, envíe el comprobante.",
    "Cuando realice mi pago, enviaré el comprobante.",
    "Para que realice el pago, le enviaré la referencia.",
    "En cuanto haga el pago, le aviso.",
    "Una vez que  realice el pago, envíe el comprobante.",
    "Si yo realice el pago, enviaré el comprobante.",
])
def test_future_payment_instructions_do_not_exempt_new_collection(instruction):
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. " + instruction,
                                      {"estatus_grabacion": "CONVENIO"})
    n = r["negotiation_validation"]
    assert not n["payment_already_made"]
    assert not n["payment_confirmation_case"]
    assert not n["prior_payment_evidence"]
    assert "PEN_CONV_LUGARES" in {p["id"] for p in r["penalties"]}


@pytest.mark.parametrize("report", [
    "Sí pagué 600 pesos ayer.",
    "Cuando realicé mi pago envié el comprobante.",
    "Ayer realicé mi pago.",
])
def test_accented_past_payment_reports_remain_completed(report):
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. " + report,
                                      {"estatus_grabacion": "CONVENIO"})
    assert r["negotiation_validation"]["payment_confirmation_case"]
    assert "PEN_CONV_LUGARES" not in {p["id"] for p in r["penalties"]}


def test_a_future_instruction_does_not_erase_a_separate_completed_payment():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Ya pagué 600 pesos hoy, cuando realice el otro pago le aviso.",
        {"estatus_grabacion": "CONVENIO", "pago_minimo": "500", "saldo_total": "2000"})
    n = r["negotiation_validation"]
    assert n["payment_confirmation_case"]
    assert n["prior_payment_total"] == 600


def test_negated_payment_report_is_not_completed():
    r = A.calculate_basic_compliance("Habla MRS. Soy yo. No pagué 600 pesos ayer.",
                                      {"estatus_grabacion": "CONVENIO"})
    assert not r["negotiation_validation"]["payment_confirmation_case"]


def test_reported_deposit_amount_can_cover_the_minimum_without_a_new_promise():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Depositamos desde el domingo. ¿Qué cantidad pagaron? "
        "Fueron mil pesos. Llame hoy al banco para verificar la aplicación.",
        {"estatus_grabacion": "NO DEFINE FECHA DE PAGO", "pago_minimo": "750", "saldo_total": "2000"})
    n = r["negotiation_validation"]
    assert n["payment_confirmation_case"]
    assert n["prior_payment_total"] == 1000
    assert n["prior_payment_covers_minimum"]
    assert not n["promise_date_confirmed_from_call"]
    assert "PEN_SIN_INTENTO_NEGOCIACION" not in {p["id"] for p in r["penalties"]}
    assert r["status_validation"]["detected_status"] == "PAGO REPORTADO / ACLARACION"
    assert r["status_validation"]["matches"] is False
    assert r["final_result"] == "REVISAR"


def test_payment_today_followed_by_good_day_is_not_a_second_installment():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Podemos ofrecer mil pesos o dos mil pesos. "
        "Me comprometo a pagar dos mil pesos hoy. Que tenga buen día.",
        {"estatus_grabacion": "CONVENIO", "pago_minimo": "500", "saldo_total": "8000",
         "fecha": "2026-10-13"})
    n = r["negotiation_validation"]
    assert not n["multipago_detectado"]
    assert n["monto_detectado"] == 2000


def test_distinct_dated_installments_are_still_added():
    r = A.calculate_basic_compliance(
        "Habla MRS. Soy yo. Me comprometo a pagar mil pesos hoy y dos mil pesos mañana.",
        {"estatus_grabacion": "CONVENIO", "pago_minimo": "2500", "saldo_total": "8000",
         "fecha": "2026-10-13"})
    n = r["negotiation_validation"]
    assert n["multipago_detectado"]
    assert n["total_multipago"] == 3000
