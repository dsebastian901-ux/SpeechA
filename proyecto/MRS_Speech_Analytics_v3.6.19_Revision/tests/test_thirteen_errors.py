"""Cobertura transversal de los trece errores reportados por el usuario."""
import json

import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.review_service import ReviewService
from app.services.transcription_services import TranscriptionService


def run(text, **context):
    return A.calculate_basic_compliance(text, context)


def ids(result):
    return {p["id"] for p in result["penalties"]}


@pytest.mark.parametrize("text", ["¿No lo conozco?", "Gestor: No lo conozco.", "No soy yo.", "¿Soy yo?"])
def test_e04_identity_questions_and_agent_phrases_do_not_confirm_recipient(text):
    r = run(text)
    assert r["contact_type"] == "CONTACTO NO DETERMINADO"
    assert "PEN_ARCO_OMISION" not in ids(r)


def test_e06_email_alone_does_not_satisfy_arco_procedure():
    r = run("Habla MRS. No lo conozco. Correo privacidad@bradesco.com.mx.", estatus_grabacion="NO CONOCEN A DEUDOR")
    assert "PEN_ARCO_OMISION" in ids(r)
    assert r["final_result"] == "INCORRECTA"


def test_e06_linea_does_not_count_as_ine():
    r = run("Habla MRS. No lo conozco. Derechos ARCO. Tengo dos años con esta línea. Correo privacidad@bradesco.com.mx.",
            estatus_grabacion="NO CONOCEN A DEUDOR")
    assert r["status_validation"]["ine_or_line_proof"] is False
    assert r["status_validation"]["valid"] is False


def test_e06_complete_arco_workflow_is_not_critical():
    r = run("Habla MRS. No lo conozco. Puede ejercer sus derechos ARCO. Tengo dos años con esta línea. "
            "Envíe identificación oficial y comprobante de teléfono a privacidad@bradesco.com.mx.",
            estatus_grabacion="NO CONOCEN A DEUDOR")
    assert r["status_validation"]["valid"] is True
    assert "PEN_ARCO_OMISION" not in ids(r)


def test_e06_denied_or_customer_mentioned_arco_is_not_agent_procedure():
    for phrase in ["No voy a explicarle el proceso ARCO.", "Interlocutor: Puede ejercer sus derechos ARCO."]:
        r = run("No lo conozco. " + phrase, estatus_grabacion="NO CONOCEN A DEUDOR")
        assert "PEN_ARCO_OMISION" in ids(r)


def test_e06_tenure_question_without_answer_is_not_confirmation():
    r = run("No lo conozco. Puede ejercer sus derechos ARCO. ¿Cuánto tiempo tiene con la línea? "
            "Envíe identificación oficial a privacidad@bradesco.com.mx.", estatus_grabacion="NO CONOCEN A DEUDOR")
    assert r["status_validation"]["line_tenure_confirmed"] is False
    assert r["status_validation"]["valid"] is False


@pytest.mark.parametrize("text,count", [
    ("Puede pagar en Mi Bodega Aurrera Express.", 1),
    ("Puede pagar en Chedraui y Farmacias del Ahorro.", 2),
    ("Su tarjeta es de Chedraui. La tienda de origen es Suburbia.", 0),
    ("No puede pagar en Chedraui ni en Farmacias del Ahorro.", 0),
    ("Puede pagar en Santander.", 0),
    ("Puede pagar en Santander con convenio 3411 y en BBVA convenio 1042378.", 2),
    ("Titular: Puede pagar en Chedraui y Farmacias del Ahorro.", 0),
])
def test_e07_only_distinct_authorized_offers_are_counted(text, count):
    r = run("Habla MRS. " + text, estatus_grabacion="CONVENIO")
    assert r["convenio_payment_validation"]["authorized_places_count"] == count
    assert ("PEN_CONV_LUGARES" in ids(r)) == (count < 2)


@pytest.mark.parametrize("mora", ["1PV", "2PV"])
@pytest.mark.parametrize("phrase", ["Se puede generar una diligencia en su domicilio.",
                                    "Vamos a realizar una visita a su casa para cobrar.",
                                    "Se programará una diligencia en su domicilio.",
                                    "Acudiremos a su domicilio."])
def test_e08_prohibited_visits_are_critical(mora, phrase):
    r = run("Habla MRS. Soy yo. " + phrase, asignacion=mora)
    assert "PEN012" in ids(r)
    assert r["final_result"] == "INCORRECTA"


@pytest.mark.parametrize("phrase", ["No vamos a realizar una visita a su domicilio.", "No iremos a su casa."])
def test_e08_explicit_negation_is_not_a_visit_threat(phrase):
    assert "PEN012" not in ids(run("Habla MRS. " + phrase, asignacion="1PV"))


FLAGS = {k: True for k in ReviewService.FLAGS}


def test_e10_exception_is_explicit_persistent_and_cannot_waive_prior_mistreatment(tmp_path):
    source = tmp_path/"synthetic.json"
    source.write_text(json.dumps({"archivo": "synthetic.wav", "duracion_segundos": 90,
        "texto": "Habla MRS. Soy su madre. Dígale que se comunique. Le paso el recado. Mierda."}), encoding="utf-8")
    original = source.read_bytes()
    ReviewService.save(source, FLAGS)
    assert source.read_bytes() == original
    transcription = TranscriptionService.load_from_json(source)
    analysis = A.analyze_transcription(transcription)
    assert analysis.metadata["final_result"] == "APROBADO_CON_EXCEPCION"
    assert analysis.metadata["shared_classification"]["aprobado"] is False
    # La excepción se invalida si cambia la transcripción revisada.
    source.write_text(source.read_text().replace("Mierda.", "Gracias."))
    assert ReviewService.load(source) is None


@pytest.mark.parametrize("missing", list(ReviewService.FLAGS))
def test_e10_each_human_confirmation_is_required(missing):
    flags = dict(FLAGS, **{missing: False})
    metadata = {"quality_contact_type": "TERCERO / FAMILIAR",
                "quality_checks": {"groseria_bloquea_aprobacion": True},
                "hostile_interlocutor_exception": flags}
    assert A.shared_quality_decision(metadata, 100, duration_seconds=90)["clasificacion"] == "REVISAR"


@pytest.mark.parametrize("blocker", [
    {"quality_checks": {"queja_maltrato_detectada": ["me trataron mal"]}},
    {"privacy_validation": {"review_required": True}},
    {"card_validation": {"result": "REVISAR - REFERENCIA DISTINTA"}},
    {"negotiation_validation": {"valid": False, "reasons": ["Monto incompatible"]}},
    {"status_validation": {"valid": False, "reasons": ["Interlocutor incierto"]}},
    {"critical_failures": [{"invalidates": True, "id": "PEN003"}]},
])
def test_e10_e11_exception_does_not_override_other_blockers(blocker):
    metadata = {"hostile_interlocutor_exception": FLAGS, **blocker}
    decision = A.shared_quality_decision(metadata, 100, duration_seconds=90)
    assert decision["clasificacion"] in {"REVISAR", "FALLA_GRAVE"}


NEGOTIATION = {"estatus_grabacion": "CONVENIO", "fecha": "2026-10-20", "vencimiento": "2026-10-25",
               "asignacion": "1PV", "pago_minimo": "500", "saldo_total": "2000", "corte": "3"}


def test_e12_valid_negotiation_retains_amount_date_and_places():
    r = run("Habla MRS. Soy yo. Confirmo su convenio. Me comprometo a pagar 600 pesos el 23 de octubre de 2026. "
            "Puede pagar en Chedraui y Farmacias del Ahorro. Envíe su comprobante por WhatsApp.", **NEGOTIATION)
    n = r["negotiation_validation"]
    assert n["monto_detectado"] == 600 and n["promise_date"] == "2026-10-23"
    assert n["validacion_monto"] == "VALIDA"
    assert r["score"] == 100 and r["final_result"] == "APROBADA"


@pytest.mark.parametrize("amount", ["100", "3000"])
def test_e12_confirmed_amount_outside_minimum_total_is_not_approved(amount):
    r = run(f"Habla MRS. Soy yo. Confirmo su convenio. Me comprometo a pagar {amount} pesos el 23 de octubre de 2026.", **NEGOTIATION)
    assert r["negotiation_validation"]["validacion_monto"].startswith("INVALIDA")
    assert r["final_result"] != "APROBADA"


def test_e12_date_after_due_date_is_critical():
    r = run("Habla MRS. Soy yo. Me comprometo a pagar 600 pesos el 30 de octubre de 2026.", **NEGOTIATION)
    assert "PEN005" in ids(r)
    assert r["final_result"] == "INCORRECTA"


def test_e12_reported_past_liquidation_is_not_new_agent_offer():
    r = run("Habla MRS. Soy yo. Me dijeron que con ese pago liquidaba. Yo pagué 600 pesos para liquidar.", **NEGOTIATION)
    assert "PEN004" not in ids(r)
    assert not r["negotiation_validation"]["liquidation_detected"]


def test_e12_already_paid_does_not_require_new_convenio_or_whatsapp():
    r = run("Habla MRS. Soy yo. Ya pagué 600 pesos hoy. Registre mi pago.", **NEGOTIATION)
    assert r["negotiation_validation"]["payment_confirmation_case"] is True
    assert not ids(r) & {"PEN_CONV_LUGARES", "PEN_CONV_WHATSAPP", "PEN007", "PEN008", "PEN009"}


@pytest.mark.parametrize("base,expected", [
    ({"estatus_autorizado": True, "tiene_nombre_final": True}, "APROBADO"),
    ({"estatus_autorizado": False, "tiene_nombre_final": False}, "APROBADO_SIN_ETIQUETAR"),
    ({"estatus_autorizado": True, "tiene_nombre_final": False}, "REVISAR"),
])
def test_e01_e13_operational_categories_are_independent_of_score(base, expected):
    decision = A.shared_quality_decision({}, 95, duration_seconds=90, base_classification=base)
    assert decision["clasificacion"] == expected
    assert decision["aprobado"] is (expected == "APROBADO")


def test_e13_short_duration_blocks_even_untagged_approval():
    decision = A.shared_quality_decision({}, 100, duration_seconds=30,
                                        base_classification={"estatus_autorizado": False})
    assert decision["clasificacion"] == "REVISAR"


@pytest.mark.parametrize("word", ["Tontas", "Pendejos", "Puta", "Chinga tu madre"])
def test_e09_final_profanity_including_plurals_is_blocked(word):
    r = run("Habla MRS. Soy su madre. Gracias por su tiempo. " + word + ".")
    assert r["checks"]["groseria_bloquea_aprobacion"]
    assert r["final_result"] != "APROBADA"


def test_e09_regular_words_do_not_contain_standalone_profanity():
    r = run("La computadora tiene un problema de cómputo.")
    assert not r["checks"]["groseria_bloquea_aprobacion"]


def test_e10_hostile_customer_does_not_become_agent_confrontation():
    r = run("Titular: Es su problema, haga lo que quiera.\nGestor: Comprendo lo que me indica.")
    assert "PEN_TRATO_CONFRONTACION" not in ids(r)
    assert r["treatment_validation"]["hostile_interlocutor_review_required"]


def test_e10_confirmed_agent_confrontation_stays_critical():
    r = run("Gestor: Es su problema, haga lo que quiera.")
    assert "PEN_TRATO_CONFRONTACION" in ids(r)
    assert r["final_result"] == "INCORRECTA"


@pytest.mark.parametrize("role,critical", [("Interlocutor", False), ("Gestor", True)])
def test_e10_lascivious_comment_blocks_approval_and_preserves_speaker(role, critical):
    r = run(f"{role}: Quiero acostarme contigo.")
    assert r["checks"]["groseria_bloquea_aprobacion"]
    assert ("PEN_GROSERIA_GESTOR" in ids(r)) is critical
    assert r["final_result"] != "APROBADA"


def test_invalid_review_cannot_supply_an_exception(tmp_path):
    path = tmp_path/"synthetic.json"
    path.write_text('{}')
    ReviewService.save(path, FLAGS)
    (tmp_path/".reviews"/"synthetic.json").write_text('not JSON')
    assert ReviewService.load(path) is None


def test_e07_prior_payment_does_not_reintroduce_payment_places_in_shared_gate():
    t = TranscriptionModel("synthetic.wav", "synthetic.wav",
                           "Habla MRS. Soy yo. Ya pagué 600 pesos hoy. Registre mi pago.", duration_seconds=90)
    a = A.analyze_transcription(t, NEGOTIATION)
    assert a.metadata["negotiation_validation"]["payment_confirmation_case"]
    assert "dos lugares" not in a.metadata["shared_classification"]["motivo"]


def test_e01_e12_excel_distinguishes_review_from_confirmed_invalidity():
    from app.services.batch_report_service import BatchReportService
    t = TranscriptionModel("synthetic.wav", "synthetic.wav",
                           "Habla MRS. No sé cuándo podré pagar.", duration_seconds=90)
    a = A.analyze_transcription(t, NEGOTIATION)
    row = BatchReportService._row_from_item({"path": "synthetic.wav", "result": {"texto": t.text},
          "analytics": a.to_dict(), "analytics_metadata": a.metadata,
          "classification": a.metadata["shared_classification"], "compliance_score": a.compliance_score})
    assert row["Validación Dictamen"] == "REVISAR"
    assert row["Validación Negociación"] == "REVISAR"
    assert row["Clasificación física"] == a.metadata["final_result"] == "REVISAR"


def test_e02_audio_only_family_identity_does_not_prove_recado():
    r = run("Habla MRS. Soy su madre. Gracias por su tiempo.")
    assert r["status_validation"]["recado_evidence"]["confirmed_recado"] is False
    assert r["final_result"] == "REVISAR"


def test_e13_invalid_status_without_reasons_still_blocks_approval():
    decision = A.shared_quality_decision({"status_validation": {"valid": False}}, 100, duration_seconds=90)
    assert decision["clasificacion"] == "REVISAR"
