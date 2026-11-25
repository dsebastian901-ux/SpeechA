"""Regresión de respuesta afirmativa explícita a solicitud nominal de identidad."""
from app.services.conversation_evidence import holder_confirmation


def test_exatamente_after_name_confirms_holder():
    text = ("Gestor: Tengo el gusto con Vargas Mosqueda Luis Angel Antonio. "
            "Titular: Exactamente. Gestor: Mucho gusto, me presento.")
    result = holder_confirmation(text)
    assert result["confirmed"] is True
    assert result["method"] == "RESPUESTA_A_IDENTIFICACION"


def test_exactamente_without_nominal_request_does_not_confirm_holder():
    result = holder_confirmation(
        "Gestor: ¿Está de acuerdo con el pago? Titular: Exactamente.")
    assert result["confirmed"] is False


def test_exactamente_with_third_party_denial_does_not_confirm_holder():
    result = holder_confirmation(
        "Gestor: Tengo el gusto con Luis Angel Antonio. Tercero: Exactamente. "
        "Tercero: Pero no soy el titular, soy su hermano.")
    assert result["confirmed"] is False


def test_si_soy_yo_after_full_name_confirms_holder():
    result = holder_confirmation(
        "Gestor: ¿Me puede comunicar con Persona Ejemplo? "
        "Titular: Sí, soy yo.")
    assert result["confirmed"] is True


def test_si_soy_yo_without_nominal_request_does_not_confirm_holder():
    result = holder_confirmation(
        "Gestor: ¿Puede realizar el pago? Titular: Sí, soy yo.")
    assert result["confirmed"] is False


def test_si_soy_yo_with_explicit_third_party_denial_stays_unconfirmed():
    result = holder_confirmation(
        "Gestor: ¿Me puede comunicar con Persona Ejemplo? "
        "Tercero: Sí, soy yo. Tercero: No soy el titular, soy su hermano.")
    assert result["confirmed"] is False


def test_repeated_suffix_requires_two_matching_card_mentions():
    from app.services.analytics_service import AnalyticsService
    context = {"estatus_grabacion": "NO DEFINE FECHA DE PAGO",
               "numero_de_tarjeta": "0000000000005222",
               "asignacion": "1PV", "fecha": "2026-11-20",
               "pago_minimo": 200, "saldo_total": 1000}
    text = ("Gestor: La tarjeta termina en 52-22. "
            "Gestor: Confirmo terminación, 52-22. "
            "Gestor: Repito terminación 52 22 22.")
    checked = AnalyticsService.calculate_basic_compliance(text, context)
    assert checked["card_validation"]["result"] == "TARJETA CORRECTA"


def test_repeated_suffix_without_two_confirmations_remains_unverified():
    from app.services.analytics_service import AnalyticsService
    context = {"estatus_grabacion": "NO DEFINE FECHA DE PAGO",
               "numero_de_tarjeta": "0000000000005222",
               "asignacion": "1PV", "fecha": "2026-11-20",
               "pago_minimo": 200, "saldo_total": 1000}
    checked = AnalyticsService.calculate_basic_compliance(
        "Gestor: La tarjeta termina en 52 22 22.", context)
    assert checked["card_validation"]["result"] == "REVISAR - NUMERO NO CONFIABLE"


def test_nominal_request_without_me_with_personal_response():
    from app.services.contact_evidence_graph import nominal_requests, contextual_contact
    text = (
        "Gestor: ¿Podrá comunicar con Saúcedo Ramírez María Guadalupe? "
        "Interlocutor: Sí, soy yo. "
        "Gestor: ¿Ya pudo hacer el pago? "
        "Interlocutor: No he podido pagar, estoy sin trabajo."
    )
    assert list(nominal_requests(text))
    assert contextual_contact(text)["confirmed"] is True


def test_estoy_buscando_nominal_does_not_confirm_third_party():
    from app.services.contact_evidence_graph import nominal_requests, contextual_contact
    text = (
        "Gestor: Estoy buscando a Laura Ríos Sánchez. "
        "Tercero: Es mi hermana, no está en casa. "
        "Gestor: ¿Puede realizar el pago? "
        "Tercero: No, yo no puedo."
    )
    assert list(nominal_requests(text))
    assert contextual_contact(text)["confirmed"] is False


def test_word_recado_alone_is_not_evidence_of_third_party():
    from app.services.contact_evidence_graph import nonholder_context
    text = ("Gestor: ¿Me comunica con Aurora Méndez Lara? "
            "Titular: Sí, soy yo. "
            "Gestor: Le comento que ya le dejé un recado la semana pasada. "
            "Titular: Sí, lo recuerdo, mi tarjeta está al corriente.")
    assert nonholder_context(text) is False


def test_declared_relative_still_prevents_holder_inference():
    from app.services.contact_evidence_graph import nonholder_context, contextual_contact
    text = ("Gestor: ¿Me comunica con Aurora Méndez Lara? "
            "Tercero: No soy la persona, soy su hermana. No está. "
            "Gestor: Le dejo un recado para su hermana.")
    assert nonholder_context(text) is True
    assert contextual_contact(text)["confirmed"] is False


def test_saying_hablo_por_su_producto_is_not_third_party():
    from app.services.contact_evidence_graph import nonholder_context
    text = ("Gestor: Tengo el gusto con Clara Pérez Mejía. "
            "Titular: Sí, soy yo. "
            "Gestor: Hablo por su producto de tarjeta Visa, "
            "porque presenta un saldo vencido.")
    assert nonholder_context(text) is False


def test_hablo_por_el_mismo_motivo_is_not_third_party():
    from app.services.contact_evidence_graph import nonholder_context
    text = ("Gestor: Me comunica con Clara Pérez Mejía. Titular: Sí. "
            "Titular: Me habló por el mismo motivo su compañera ayer, "
            "ya hice el pago.")
    assert nonholder_context(text) is False


def test_explicit_paying_for_relative_still_blocked():
    from app.services.contact_evidence_graph import nonholder_context
    text = ("Gestor: Me comunica con Clara Pérez Mejía. "
            "Tercero: Soy su hermana. Yo pago por ella, no está en casa.")
    assert nonholder_context(text) is True


def test_confirmed_partial_payment_penalty_below_80_is_rejected_with_alerts():
    from app.services.quality_decision import evaluate_quality
    metadata = {
        "negotiation_validation": {
            "partial_payment": True, "partial_explanation": False,
            "valid": False, "review_required": True,
            "reasons": ["Importe del compromiso aún no confirmado."],
        },
        "penalties": [
            {"id": "PEN001", "points": 20, "invalidates": False,
             "reason": "Identificación del despacho omitida."},
            {"id": "PEN_CONV_LUGARES", "points": 20, "invalidates": False,
             "reason": "No proporcionó dos lugares de pago."},
            {"id": "PEN015", "points": 30, "invalidates": False,
             "reason": "Pago parcial sin explicar la falta de regularización."},
        ],
    }
    result = evaluate_quality(metadata, score=30)
    assert result["clasificacion"] == "NO_APROBADO_MENOR_80"
    assert any(f["code"] == "NEGOTIATION_INVALID_OR_UNCERTAIN"
               and f["severity"] == "PENDING_ALERT"
               for f in result["decision_findings"])


def test_unconfirmed_partial_payment_does_not_invent_a_rejection():
    from app.services.approval_resolution import ordinary_score_rejection
    metadata = {
        "negotiation_validation": {
            "partial_payment": False, "partial_explanation": False,
        },
        "penalties": [
            {"id": "PEN001", "points": 20},
            {"id": "PEN_CONV_LUGARES", "points": 20},
            {"id": "PEN015", "points": 30},
        ],
    }
    assert not ordinary_score_rejection(metadata, 30, 80, None)


def test_repeated_settlement_amount_does_not_become_two_payments():
    from app.services.payment_sequence_evidence import bounded_two_payment_sequence
    text = ("Se paga el día de hoy un descuento de 6400. "
            "Si me confirma el pago de hoy y mañana, 6400. "
            "Los 6400 están perfectos.")
    first = text.index("6400")
    second = text.index("6400", first + 1)
    candidates = [
        (10, 0, (first, first+4, 6400.0, "6400")),
        (10, 0, (second, second+4, 6400.0, "6400")),
    ]
    assert bounded_two_payment_sequence(text, candidates) == []


def test_explicit_two_identical_payments_remain_countable():
    from app.services.payment_sequence_evidence import bounded_two_payment_sequence
    text = "Acordamos dos pagos: primer pago de 600 hoy y segundo pago de 600 mañana."
    first = text.index("600")
    second = text.index("600", first + 1)
    candidates = [
        (10, 0, (first, first+3, 600.0, "600")),
        (10, 0, (second, second+3, 600.0, "600")),
    ]
    assert bounded_two_payment_sequence(text, candidates) == [600.0, 600.0]


def test_asr_augusto_conn_nominal_plus_own_payment_confirms_context():
    from app.services.contact_evidence_graph import contextual_contact
    text = ("Gestor: Soy de MRS Consultores, tengo Augusto Conn "
            "Miranda Rodríguez Óscar Enrique. "
            "Gestor: ¿Ya realizó el pago de su tarjeta? "
            "Titular: Sí, de hecho ya lo realicé, lo hice en la aplicación.")
    assert contextual_contact(text)["confirmed"] is True


def test_asr_augusto_conn_without_own_reply_does_not_confirm_holder():
    from app.services.contact_evidence_graph import contextual_contact
    text = ("Gestor: Soy de MRS Consultores, tengo Augusto Conn "
            "Miranda Rodríguez Óscar Enrique. Interlocutor: Sí.")
    assert contextual_contact(text)["confirmed"] is False


def test_never_paid_minimum_is_not_historical_payment():
    from app.services.conversation_evidence import completed_payment
    assert not completed_payment("Yo nunca pagué el mínimo, nunca me atrasé.", [])["confirmed"]


def test_genuine_paid_minimum_still_counts():
    from app.services.conversation_evidence import completed_payment
    assert completed_payment("Yo pagué el mínimo ayer.", [])["confirmed"]


def test_previous_agent_complaint_not_definitive_rejection():
    from app.services.definitive_rejection import definitive_rejection
    metadata = {
        "quality_contact_type": "TITULAR",
        "treatment_validation": {
            "mistreatment_report_evidence": [{
                "text": "La señorita de la llamada anterior se puso muy grosera.",
                "phrase": "se puso muy grosera",
                "speaker_role": "TITULAR"
            }],
            "current_agent_mistreatment_unverified": False
        }
    }
    findings = [{
        "rule_group": 11, "code": "MISTREATMENT_REPORT",
        "severity": "REVIEW", "reasons": ["Queja de trato anterior"]
    }]
    assert definitive_rejection(metadata, findings, 462.34) is None


def test_installment_days_are_not_accepted_amounts():
    from app.services.conversation_evidence import normalize
    from app.services.payment_sequence_evidence import accepted_amount_values
    evidence = "Quedaría de la siguiente manera, 2000 pesos el día lunes 23-30 y 7 de diciembre, correcto? Sí."
    source = normalize(evidence)
    import re
    mentions = [(m.start(), m.end(), float(m.group()), m.group())
                for m in re.finditer(r'\b(?:2000|20|30|23|7)\b', source)]
    assert accepted_amount_values(evidence, mentions) == {2000.0}


def test_small_payment_with_currency_is_not_discarded_as_calendar_day():
    from app.services.conversation_evidence import normalize
    from app.services.payment_sequence_evidence import accepted_amount_values
    evidence = "Hoy pago 20 pesos y mañana pago 30 pesos."
    source = normalize(evidence)
    import re
    mentions = [(m.start(), m.end(), float(m.group()), m.group())
                for m in re.finditer(r'\b(?:2000|20|30|23|7)\b', source)]
    assert accepted_amount_values(evidence, mentions) == {20.0, 30.0}


def test_installment_amounts_match_accepted_three_payment_recap():
    from app.services.conversation_evidence import normalize
    from app.services.payment_sequence_evidence import accepted_amount_values
    evidence = "Entonces quedaría de la siguiente manera: 2000 pesos el día lunes 23-30 y 7 de diciembre, correcto? Sí, sí."
    source = normalize(evidence)
    import re
    mentions = [(m.start(), m.end(), float(m.group()), m.group())
                for m in re.finditer(r'\b(?:2000|23|30|7)\b', source)]
    accepted = accepted_amount_values(evidence, mentions)
    assert accepted.issubset({2000.0})


def test_generic_bank_list_no_longer_requires_two_retail_venues():
    from app.services.payment_instruction_validation import transfer_is_option_listing
    wording = ("Puede realizar su pago en Farmacias del Ahorro, o por "
               "transferencia por medio de Santander, BBVA o Banamex.")
    assert transfer_is_option_listing(wording, [], ["FARMACIAS DEL AHORRO"])


def test_specific_bank_account_instruction_never_treated_as_generic_list():
    from app.services.payment_instruction_validation import transfer_is_option_listing
    wording = ("Puede pagar por transferencia por medio de Santander "
               "a la cuenta bancaria 123456789012345678.")
    assert not transfer_is_option_listing(wording, [], ["FARMACIAS DEL AHORRO"])
