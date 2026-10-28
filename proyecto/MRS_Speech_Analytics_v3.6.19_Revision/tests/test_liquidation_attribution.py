"""Separar oferta total, intención del cliente, pregunta y cobertura de lo vencido."""
import pytest

from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel


def analyze(text, mora="1PV", segments=None):
    raw={"archivo":"synthetic.wav","texto":text,"segmentos":segments or [],"duracion_segundos":90}
    relation={"asignacion":mora,"pago_minimo":500,"saldo_total":2000,
        "fecha":"2026-10-20","vencimiento":"2026-10-31","estatus_grabacion":"NO DEFINE FECHA DE PAGO"}
    return A.analyze_transcription(TranscriptionModel.from_dict(raw),relation)


@pytest.mark.parametrize("phrase", [
    "¿Liquida su saldo vencido?", "Con este pago liquida su saldo vencido.",
    "Usted puede liquidar la mensualidad vencida.", "Con ese pago liquida lo vencido.",
])
def test_covering_overdue_amount_is_not_full_account_settlement(phrase):
    a=analyze("Habla MRS. Soy yo. "+phrase)
    assert "PEN004" not in {p["id"] for p in a.metadata["penalties"]}
    assert not a.metadata["negotiation_validation"]["liquidation_detected"]


@pytest.mark.parametrize("phrase", [
    "Titular: Ya les había dicho que el día dos liquido la cuenta.",
    "Titular: Voy a liquidar la cuenta.",
    "Titular: Yo quiero liquidar.",
    "Cliente: Yo voy a liquidar el saldo total.",
])
def test_holder_intent_is_not_an_agent_offer(phrase):
    a=analyze("Habla MRS. Soy yo.\n"+phrase)
    assert "PEN004" not in {p["id"] for p in a.metadata["penalties"]}


@pytest.mark.parametrize("phrase", [
    "¿Usted puede liquidar la cuenta?", "El día dos que liquida la cuenta.",
    "Liquida su cuenta.", "¿Con este pago liquidaría la cuenta?",
    "Si realiza ese pago ya tendría su cuenta en ceros.",
])
def test_unattributed_echo_or_question_requires_review_without_pen004(phrase):
    a=analyze("Habla MRS. Soy yo. "+phrase)
    n=a.metadata["negotiation_validation"]
    assert "PEN004" not in {p["id"] for p in a.metadata["penalties"]}
    assert n["liquidation_offer_review_required"]
    assert n["liquidation_offer_evidence"]
    assert a.metadata["shared_classification"]["clasificacion"]=="REVISAR"


@pytest.mark.parametrize("phrase", [
    "Gestor: Liquida su cuenta.",
    "Usted debe liquidar la cuenta.",
    "Le ofrecemos un descuento para liquidar la cuenta.",
    "Con este pago liquida su cuenta.",
])
@pytest.mark.parametrize("mora",["1PV","1FLP","2PV","3PV"])
def test_explicit_total_settlement_offer_in_early_mora_stays_critical(phrase,mora):
    a=analyze("Habla MRS. Soy yo.\n"+phrase,mora)
    assert "PEN004" in {p["id"] for p in a.metadata["penalties"]}
    assert a.metadata["shared_classification"]["clasificacion"]=="FALLA_GRAVE"


def test_earlier_holder_intent_does_not_exempt_a_later_agent_offer():
    a=analyze("Titular: Yo quiero liquidar.\nGestor: Con este pago liquida su cuenta.")
    assert "PEN004" in {p["id"] for p in a.metadata["penalties"]}


def test_semantic_gestor_role_on_segment_is_respected():
    text="Liquida su cuenta."
    a=analyze(text,segments=[{"texto":text,"inicio":10,"fin":15,"speaker_role":"GESTOR"}])
    assert "PEN004" in {p["id"] for p in a.metadata["penalties"]}
    assert a.metadata["negotiation_validation"]["liquidation_offer_evidence"][0]["start"]==10


def test_diarization_identity_alone_does_not_identify_the_agent():
    text="Liquida su cuenta."
    a=analyze(text,segments=[{"texto":text,"inicio":10,"fin":15,"speaker":"SPEAKER_00"}])
    assert "PEN004" not in {p["id"] for p in a.metadata["penalties"]}
    assert a.metadata["negotiation_validation"]["liquidation_offer_review_required"]


def test_negated_offer_is_not_a_total_settlement_offer():
    a=analyze("Gestor: No puede liquidar la cuenta.")
    assert "PEN004" not in {p["id"] for p in a.metadata["penalties"]}


@pytest.mark.parametrize("amount",["1800","mil ochocientos"])
def test_owed_balance_and_first_person_intent_do_not_become_an_agent_order(amount):
    a=analyze(f"Habla MRS. Soy yo. Al día de hoy debe {amount} a la vez que voy a liquidar.")
    assert "PEN004" not in {p["id"] for p in a.metadata["penalties"]}
    assert a.metadata["shared_classification"]["clasificacion"]=="REVISAR"


def test_required_payment_to_settle_remains_an_explicit_offer():
    a=analyze("Gestor: Usted debe pagar 1800 pesos para liquidar su cuenta.")
    assert "PEN004" in {p["id"] for p in a.metadata["penalties"]}


def test_refusing_discount_then_explaining_full_settlement_is_still_an_offer():
    a=analyze("Gestor: No señor, tendría que, para poder liquidar su cuenta tendría que pagar su saldo total.")
    assert "PEN004" in {p["id"] for p in a.metadata["penalties"]}


def test_known_agent_promising_account_in_zeroes_is_still_a_total_claim():
    a=analyze("Gestor: Con este pago tendría su cuenta en ceros.")
    assert "PEN004" in {p["id"] for p in a.metadata["penalties"]}


@pytest.mark.parametrize("text",[
    "Gestor: No creo que tendría su cuenta en ceros.",
    "Gestor: No sé si puede liquidar su cuenta.",
])
def test_an_uncertain_effect_is_reviewed_instead_of_confirmed_as_critical(text):
    a=analyze("Habla MRS. Soy yo.\n"+text)
    assert "PEN004" not in {p["id"] for p in a.metadata["penalties"]}
    assert a.metadata["shared_classification"]["clasificacion"]=="REVISAR"


def test_agent_reporting_the_clients_words_does_not_invent_an_offer():
    a=analyze("Gestor: El cliente dice que liquida la cuenta.")
    assert "PEN004" not in {p["id"] for p in a.metadata["penalties"]}
