import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A


def analyze(text, **relation):
    return A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo':'sample.wav','texto':text,'duracion_segundos':120}),relation)


@pytest.mark.parametrize('alias',['M.A.R.S.', 'MARS', 'M.R.', 'DMRS', 'MIRS', 'M.R.C.'])
def test_confirmed_company_asr_alias_in_presentation_is_not_omission(alias):
    a=analyze(f'Mi nombre es Ana de Jurídico {alias} Consultores en representación del banco.')
    assert a.metadata['quality_checks']['identifica_mrs']
    assert 'PEN001' not in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['quality_checks']['identificacion_mrs_evidencia_asr']


@pytest.mark.parametrize('text',[
    'El planeta MARS.', 'M.A.R.S.', 'MIRS.', 'DMRS.', 'El señor M.R. Pérez.',
    'Cliente: Me presento, soy de Jurídico M.A.R.S.',
    'Gestor: No hablo del Jurídico M.A.R.S.',
    'Me dijeron del Jurídico MIRS.',
])
def test_alias_without_agent_presentation_does_not_invent_company_identity(text):
    a=analyze(text)
    assert not a.metadata['quality_checks']['identificacion_mrs_evidencia_asr']


@pytest.mark.parametrize('phrase',[
    'Espero su ticket.', 'Esperamos su ticker.', 'Espero su comprobante.',
    'Quedamos a la espera de su ticket de pago.',
    'Quedamos al pendiente de la fotografía de su tiquete de pago.',
    'Nos mande su comprobante de pago al número que le doy.',
    'Una vez que pague envíenos su comprobante.',
    'Cada que realice su pago me estará mandando sus comprobantes.',
    'Por favor nos envía la captura de pantalla de su pago.',
    'Nos quedamos en espera del comprobante.',
    'Sea tan amable de enviarme el comprobante.',
    'Envíeme el ticket.', 'Mándeme su comprobante.',
    'Me regala la captura del pago.',
    'El número de WhatsApp para reportar el comprobante.',
    'Le voy a pedir de favor que sea tan amable de fiarme su comprobante.',
    'Le toma fotografía al recibo de su pago y lo envía mediante WhatsApp.',
    'Se pide de favor nos pueda reportar el pago a un número de WhatsApp.',
    'Nos puede reportar ese pago a un número de WhatsApp que le voy a dar.',
    'Le dejo un número donde tiene que ir reportando sus pagos mediante WhatsApp.',
])
def test_ticket_request_or_expectation_is_not_missing_receipt(phrase):
    a=analyze('Habla MRS. Soy yo. '+phrase,estatus_grabacion='CONVENIO')
    p=a.metadata['convenio_payment_validation']
    assert p['requests_payment_receipt']
    assert 'PEN_CONV_WHATSAPP' not in {x['id'] for x in a.metadata['penalties']}


@pytest.mark.parametrize('phrase',[
    'Tengo un ticket.', 'Cliente: Espero su ticket.',
    'No espero su ticket.', 'No es necesario enviar el ticket.',
    'Diga que mande su comprobante.',
    'No nos envíe el ticket.',
    'No le voy a pedir que reporte el pago por WhatsApp.',
    'Envíe su INE y comprobante de la línea telefónica.',
    'Le doy el número de WhatsApp.',
])
def test_bare_receipt_agent_quote_negation_and_arco_are_not_payment_receipt_request(phrase):
    a=analyze(phrase,estatus_grabacion='CONVENIO')
    assert not a.metadata['convenio_payment_validation']['requests_payment_receipt']


def test_receipt_does_not_invent_whatsapp_channel():
    a=analyze('Gestor: Espero su ticket.',estatus_grabacion='CONVENIO')
    p=a.metadata['convenio_payment_validation']
    assert p['requests_payment_receipt'] and not p['requests_receipt_whatsapp']
    assert p['receipt_channel']=='NO CONFIRMADO'


def test_established_whatsapp_channel_and_later_ticket_expectation_are_joined():
    a=analyze('Gestor: Le doy el número de WhatsApp. Titular: Ya lo tengo. '
              'Gestor: Quedamos a la espera de su ticket.',estatus_grabacion='CONVENIO')
    assert a.metadata['convenio_payment_validation']['requests_receipt_whatsapp']


def test_full_noisy_payment_list_recognizes_distinct_authorized_brands():
    a=analyze('Habla MRS. Soy yo. Lo puede realizar en establecimientos como farmacia de la horro, '
              '7 11, círculo que, kiosco, Abarray, che dragui y bulbor.',estatus_grabacion='CONVENIO')
    p=a.metadata['convenio_payment_validation']
    assert set(p['authorized_places_detected'])=={
        'FARMACIAS DEL AHORRO','7-ELEVEN','CIRCLE K','KIOSKO','ABARREY','CHEDRAUI','WOOLWORTH'}
    assert 'PEN_CONV_LUGARES' not in {p['id'] for p in a.metadata['penalties']}


def test_store_list_can_continue_across_sentences_but_not_unrelated_topics():
    a=analyze('Puede pagar en estos establecimientos. Chedraui. Woolworth. '
              'Le hablo por su tarjeta Suburbia.',estatus_grabacion='CONVENIO')
    assert set(a.metadata['convenio_payment_validation']['authorized_places_detected'])=={'CHEDRAUI','WOOLWORTH'}


def test_origin_before_payment_instruction_is_not_a_second_payment_offer():
    a=analyze('Su tarjeta es C&A y puede pagar en Kiosco.',estatus_grabacion='CONVENIO')
    assert a.metadata['convenio_payment_validation']['authorized_places_count']==1


def test_repeated_aliases_are_one_place_and_bank_name_alone_is_not_authorized():
    a=analyze('Puede pagar en farmacia de la horro, Farmacias del Ahorro o Santander.',estatus_grabacion='CONVENIO')
    assert a.metadata['convenio_payment_validation']['authorized_places_count']==1


@pytest.mark.parametrize('phrase',[
    'No puede pagar en farmacia de la horro ni en bulbor.',
    'Titular: Puede pagar en bulbor y che dragui.',
    'Su tarjeta es de bulbor y che dragui.',
])
def test_new_store_spellings_do_not_count_negations_customer_words_or_card_origin(phrase):
    a=analyze(phrase,estatus_grabacion='CONVENIO')
    assert a.metadata['convenio_payment_validation']['authorized_places_count']==0


def test_report_distinguishes_receipt_request_from_channel_and_preserves_arco_tail():
    from app.services.batch_report_service import BatchReportService as B
    a=analyze('Gestor: Espero su ticker.',estatus_grabacion='CONVENIO')
    row=B._row_from_item({'path':'sample.wav','analytics_metadata':a.metadata})
    assert row['Solicitud comprobante/ticket']=='SI'
    assert row['Canal comprobante']=='NO CONFIRMADO'
    assert row['Comprobante WhatsApp']=='NO'
    assert B.HEADERS[-5:]==B.MODE_B_HEADERS[-5:]==B.ARCO_HEADERS


def test_receipt_asr_uncertainty_is_reviewed_without_asserting_omission():
    a=analyze('Habla MRS. Soy yo. A este WhatsApp más a llegar su tiqueta pago.',estatus_grabacion='CONVENIO')
    p=a.metadata['convenio_payment_validation']
    assert p['receipt_request_review_required']
    assert 'PEN_CONV_WHATSAPP' not in {p['id'] for p in a.metadata['penalties']}
    assert not a.metadata['shared_classification']['aprobado']


def test_correct_payment_list_does_not_exempt_offensive_closing():
    a=analyze('Habla MRS. Soy yo. Puede pagar en bulbor y che dragui. Espero su ticket. Maldita.',estatus_grabacion='CONVENIO')
    assert a.metadata['quality_checks']['groseria_bloquea_aprobacion']
    assert not a.metadata['shared_classification']['aprobado']


def test_financial_negative_payment_status_in_recado_requires_voice_attribution():
    a=analyze('Habla MRS. Soy su hermana. Yo le paso su recado. '
              'De su tarjeta hoy se le está ditaminando a su negativa, hoy se inicia cobro.',
              estatus_grabacion='MENSAJE CON FAMILIAR')
    assert a.metadata['privacy_validation']['review_required']
    assert not a.metadata['shared_classification']['aprobado']


def test_refusal_to_receive_message_is_not_negative_payment_status():
    from app.services.conversation_evidence import sensitive_financial_matches
    assert not sensitive_financial_matches('Por el pago se está registrando su negativa a recibir el recado.')


def test_legacy_receipt_and_channel_without_clear_request_is_uncertain_not_omission():
    a=analyze('Habla MRS. Soy yo. Comprobante del pago. Le doy el número de WhatsApp.',estatus_grabacion='CONVENIO')
    p=a.metadata['convenio_payment_validation']
    assert p['receipt_request_review_required']
    assert not p['requests_payment_receipt']
    assert 'PEN_CONV_WHATSAPP' not in {p['id'] for p in a.metadata['penalties']}
    assert not a.metadata['shared_classification']['aprobado']


def test_explicit_refusal_is_not_hidden_by_receipt_plus_channel_fallback():
    a=analyze('Habla MRS. Soy yo. No envíe el ticket por WhatsApp.',estatus_grabacion='CONVENIO')
    p=a.metadata['convenio_payment_validation']
    assert not p['requests_payment_receipt'] and not p['receipt_request_review_required']


def test_receipt_followup_does_not_approve_new_unaccepted_remaining_payment():
    a=analyze('Habla MRS. Soy yo. Ya pagué 2000 pesos hoy. '
        'Gestor: Espero su comprobante por WhatsApp. Le había dado otra propuesta de 3923 el día cuatro. '
        '¿Puede confirmar ese pago el día cuatro? Cliente: No, tendría que ser hasta el día quince.',
        estatus_grabacion='CONVENIO',pago_minimo='2000',saldo_total='5923')
    n=a.metadata['negotiation_validation']
    assert n['unaccepted_new_payment_instruction']
    assert n['new_payment_proposal_evidence']
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'


def test_plain_paid_followup_with_bank_remaining_information_stays_permitted():
    a=analyze('Habla MRS. Soy yo. Ya pagué 2000 pesos hoy. '
              'Gestor: Espero su comprobante por WhatsApp. El restante lo paga como indique el banco.',
              estatus_grabacion='CONVENIO',pago_minimo='2000',saldo_total='5923')
    assert not a.metadata['negotiation_validation']['unaccepted_new_payment_instruction']
    assert a.metadata['shared_classification']['clasificacion']=='APROBADO'


@pytest.mark.parametrize('text',[
    'Otra propuesta de pago. Gestor: ¿Puede confirmar ese pago del día cuatro?',
    'Otra propuesta de pago. Cliente: ¿Puede confirmar ese pago el día cuatro?',
])
def test_past_payment_or_known_customer_question_is_not_new_agent_proposal(text):
    from app.services.operational_script_evidence import remaining_payment_proposals
    assert not remaining_payment_proposals(text)


def test_passive_payment_instruction_does_not_turn_places_into_card_origin():
    a=analyze('Los pagos se realizan directamente a su tarjeta, puede ser en la tienda, '
              'en alguna formacia de la ORO, 7-11 y tienda 3B como pago de servicio.',
              estatus_grabacion='CONVENIO')
    p=a.metadata['convenio_payment_validation']
    assert set(p['authorized_places_detected'])=={'FARMACIAS DEL AHORRO','7-ELEVEN','TIENDAS 3B'}
    assert 'PEN_CONV_LUGARES' not in {x['id'] for x in a.metadata['penalties']}


def test_implicit_card_origin_is_not_an_additional_payment_offer():
    a=analyze('Su tarjeta C&A y puede pagar en Kiosco.',estatus_grabacion='CONVENIO')
    assert a.metadata['convenio_payment_validation']['authorized_places_count']==1
