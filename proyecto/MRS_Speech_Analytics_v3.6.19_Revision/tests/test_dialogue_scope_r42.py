import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import holder_confirmation, payment_commitment, reported_card_clarification, completed_payment
from app.services.balance_context_evidence import balance_corrections


def analyze(text,**relation):
    return A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':150}),relation)


@pytest.mark.parametrize('phrase',[
    'Voy a hacer lo posible para el sábado.',
    'Voy a hacerlo posible para pagar.',
    'Aún no lo tengo así confirmado.',
    'No quisiera que me hiciera el convenio.',
    'No cuento con una cierta cantidad de dinero.',
    'No tengo todo el dinero.',
    'Estoy esperando un dinero.',
])
def test_unfirm_payment_reply_is_not_an_accepted_agreement(phrase):
    text='Gestor: ¿Confirma el pago para el sábado? Titular: '+phrase
    r=payment_commitment(text)
    assert not r['accepted'] and (r.get('declined') or r.get('conditional'))


def test_statement_before_embedded_question_keeps_explicit_inability():
    r=payment_commitment('Gestor: ¿Puede pagar? Titular: No cuento con una cierta cantidad de dinero, ¿sí?')
    assert r['declined']
    assert not payment_commitment('Gestor: ¿No cuento con dinero?')['declined']


def test_later_firm_acceptance_is_not_erased_by_old_uncertainty():
    r=payment_commitment('Titular: Estoy esperando un dinero para el pago. '
                         'Gestor: ¿Podemos contar con su pago para mañana? Titular: Sí. '
                         'Titular: Mañana deposito 900 pesos.')
    assert r['accepted']


@pytest.mark.parametrize('intro',[
    '¿Me puede comunicar con Persona de Ejemplo? Sí.',
    '¿Me puedo comunicar con Persona de Ejemplo? Sí.',
    '¿Me pude comunicar con Persona de Ejemplo? Sí.',
    'Buenas tardes con Persona de Ejemplo, gracias, me presento.',
])
def test_named_request_requires_independent_own_card_declaration(intro):
    assert not holder_confirmation(intro)['confirmed']
    assert holder_confirmation(intro+' Cuando yo saqué la tarjeta la tramité en tienda.')['confirmed']


@pytest.mark.parametrize('tail',[
    'Soy su hermana. Yo solicité la tarjeta para mi hermana.',
    'No se encuentra. Yo tengo una tarjeta.',
    'Yo solicité la tarjeta para mi esposa.',
    'Si yo tuviera mi tarjeta le diría.',
])
def test_family_absence_on_behalf_and_hypothesis_do_not_become_holder(tail):
    assert not holder_confirmation('¿Me puede comunicar con Persona de Ejemplo? Sí. '+tail)['confirmed']


CANCELLATION=('Esta tarjeta la tengo cancelada. ¿Tendrá un número de folio de cancelación? Claro. '
              'Es AB 10 11 52 26. Lo estoy poniendo aquí en sistema para que ya no le generen más llamadas.')


def test_cancellation_case_with_folio_and_system_followup_is_clarification():
    r=reported_card_clarification(CANCELLATION)
    assert r['confirmed'] and r['cancellation_followup']
    a=analyze('Habla MRS. Soy yo. '+CANCELLATION,estatus_grabacion='ACLARACION')
    assert a.metadata['status_validation']['matches']
    assert a.metadata['shared_classification']['clasificacion']=='APROBADO'
    assert 'Cancelación reportada' in a.metadata['status_validation']['evidence']
    assert 'Pérdida' not in a.metadata['status_validation']['evidence']


@pytest.mark.parametrize('text',[
    '¿Esta tarjeta la tengo cancelada? '+CANCELLATION.split('. ',1)[1],
    'Esta tarjeta la tengo cancelada. No tengo folio. Lo pondré en sistema.',
    'Esta tarjeta la tengo cancelada. ¿Tendrá un número de folio de cancelación? Claro. '
    'Le doy mi teléfono 5511223344. Lo estoy poniendo aquí en sistema para que ya no le generen más llamadas.',
    'Gestor: Esta tarjeta la tengo cancelada. ¿Tendrá un número de folio de cancelación? Claro. AB 10115226.',
])
def test_question_missing_folio_phone_or_agent_word_do_not_confirm_cancellation(text):
    assert not reported_card_clarification(text).get('cancellation_followup')


def test_explicit_balance_self_correction_is_parsed_without_excel_guess():
    text='Tengo en mi sistema un saldo por dos mil trescientos, veintidós mil trescientos nueve, perdón.'
    corrected=balance_corrections(text)
    assert corrected[0]['amount']==22309
    a=analyze('Habla MRS. Soy yo. '+text, saldo_total='22309')
    n=a.metadata['negotiation_validation']
    assert n['saldo_informado_detectado']==22309
    assert n['validacion_saldo_informado']=='SALDO INFORMADO CORRECTO'
    b=analyze('Habla MRS. Soy yo. '+text, saldo_total='24000')
    assert b.metadata['negotiation_validation']['saldo_informado_detectado']==22309
    assert b.metadata['negotiation_validation']['validacion_saldo_informado']!='SALDO INFORMADO CORRECTO'


def test_later_wrong_explicit_balance_after_correction_stays_reviewed():
    a=analyze('Habla MRS. Soy yo. Saldo de 2300, 22309, perdón. Su saldo total es 21000.',saldo_total='22309')
    assert a.metadata['negotiation_validation']['saldo_contradictorio_tras_correccion']
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'


def test_customer_historical_amount_is_not_wrong_current_agent_balance():
    a=analyze('Habla MRS. Soy yo. Titular: Yo llamé antes y tenía un saldo de 13 en ese momento.',saldo_total='18000')
    assert a.metadata['negotiation_validation']['saldo_informado_detectado'] is None


def test_discount_offered_as_saldo_is_not_total_balance_comparison():
    a=analyze('Habla MRS. Soy yo. No se le está cobrando esa cantidad; se le está dando el saldo de 1800 pesos. '
              'Y con eso estaría liquidando la cuenta.',saldo_total='11000',pago_minimo='1700',asignacion='C2')
    assert a.metadata['negotiation_validation']['saldo_informado_detectado'] is None


def test_explicit_total_balance_is_still_compared_even_near_settlement_wording():
    a=analyze('Habla MRS. Soy yo. Su saldo total es 1800 pesos. Con eso estaría liquidando.',saldo_total='11000')
    assert a.metadata['negotiation_validation']['saldo_informado_detectado']==1800
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'


def test_repeated_call_harassment_complaint_blocks_after_other_alert_removed():
    a=analyze('Habla MRS. Soy yo. No dejan a uno ni al baño tranquilo, llame y llame.',estatus_grabacion='NO DEFINE FECHA DE PAGO')
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert not a.metadata['shared_classification']['aprobado']


def test_promissory_note_does_not_become_customer_future_commitment():
    r=payment_commitment('Titular: No cuento con una cierta cantidad de dinero para pagar. '
                         'Se hará válido el pagaré de garantía.')
    assert r['declined'] and not r['accepted']
    assert payment_commitment('Titular: Yo pagaré 800 pesos el viernes.')['accepted']
    a=analyze('Habla MRS. Soy yo. No cuento con una cierta cantidad de dinero para pagar. '
              'Se hará válido el pagaré de garantía.',estatus_grabacion='NO DEFINE FECHA DE PAGO')
    assert a.metadata['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'


def test_recurring_month_day_is_not_a_reported_balance():
    a=analyze('Habla MRS. Soy yo. El pago de 2050 pone al corriente el saldo vencido y el restante '
              'lo iría pagando mes con mes, antes de los días 18 de cada mes.',saldo_total='5963',pago_minimo='2050')
    assert a.metadata['negotiation_validation']['saldo_informado_detectado'] is None


def test_fragmented_thousands_are_reviewed_not_called_eleven_pesos():
    a=analyze('Habla MRS. Soy yo. El saldo total llegó a los 11 mil 1221.',saldo_total='11521')
    n=a.metadata['negotiation_validation']
    assert n['saldo_informado_detectado'] is None and n['saldo_fragmentado_evidencia']
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'


@pytest.mark.parametrize('reply', ['¡Igualmente!', '¡Reptigualmente!', 'Gracias.', 'Titular: A usted.'])
def test_courtesy_after_explicit_goodbye_does_not_extend_wait(reply):
    from app.services.call_wait_evidence import assess_call_wait
    units = [{'start':0,'end':20,'text':'Que tenga buen día.'},
             {'start':20,'end':22,'text':reply}]
    assert not assess_call_wait(' '.join(u['text'] for u in units),units,200)['review_required']


@pytest.mark.parametrize('reply', ['¿Bueno? ¿Me escucha?', 'Un momento.', 'No he terminado.', '¡Reptigualmente! Un momento.'])
def test_resumed_exchange_after_goodbye_still_requires_recontact(reply):
    from app.services.call_wait_evidence import assess_call_wait
    units = [{'start':0,'end':20,'text':'Que tenga buen día.'},
             {'start':20,'end':22,'text':reply}]
    assert assess_call_wait(' '.join(u['text'] for u in units),units,200)['review_required']


def test_courtesy_without_goodbye_or_with_preceding_long_gap_keeps_wait():
    from app.services.call_wait_evidence import assess_call_wait
    for units in [
        [{'start':0,'end':5,'text':'¡Reptigualmente!'}],
        [{'start':0,'end':5,'text':'Que tenga buen día.'},
         {'start':80,'end':82,'text':'¡Reptigualmente!'}],
    ]:
        assert assess_call_wait(' '.join(u['text'] for u in units),units,200)['review_required']


@pytest.mark.parametrize('intro',[
    'Buen día, jurídico M.R.S. con el señor Persona de Ejemplo. Al habla.',
    'Hola, buen día. Con la señora Persona de Ejemplo. Sí, díganme.',
    '¿Me podría comunicar con Persona de Ejemplo? Sí, dime.',
    'Me puedo comunicar con Persona de Ejemplo, dígame, gracias.',
    '¿Me podría comunicar con Persona de Ejemplo? Sí, servidor.',
])
def test_explicit_nominal_response_survives_asr_punctuation(intro):
    assert holder_confirmation(intro)['confirmed']


@pytest.mark.parametrize('intro',[
    'Buen día, jurídico M.R.S. con el señor Persona de Ejemplo. Sí.',
    '¿Me podría comunicar con Persona de Ejemplo? Sí.',
    'Me puedo comunicar con Persona de Ejemplo, dígame, soy su hermana.',
    'Buen día, jurídico M.R.S. con el señor Persona de Ejemplo. Al habla. No se encuentra.',
    'Gestor: Buen día, jurídico M.R.S. con el señor Persona de Ejemplo. Gestor: Al habla.',
    'Buen día, con la tarjeta. Al habla.',
])
def test_punctuation_does_not_bypass_holder_identity_safeguards(intro):
    assert not holder_confirmation(intro)['confirmed']


@pytest.mark.parametrize('text',[
    'Le recomiendo que lo pague directamente en tienda.',
    'Le pido que lo pague para mañana.',
    'Espero que lo pague en cuanto tenga dinero.',
    'Me indicó que usted lo pague.',
])
def test_future_payment_instruction_is_not_a_completed_deposit(text):
    assert not completed_payment(text)['confirmed']


@pytest.mark.parametrize('text',[
    'Ya lo pagué.', 'Yo le dije que lo pagué ayer.', 'Ya lo pague ayer.',
])
def test_actual_past_payment_still_supports_followup(text):
    assert completed_payment(text)['confirmed']


def test_funds_not_received_and_future_instruction_do_not_become_paid_followup():
    text=('Habla MRS. Soy yo. No tengo dinero. Si me cae el dinero luego lo hago. '
          'Le recomiendo que lo pague directamente en tienda.')
    a=analyze(text,estatus_grabacion='CONVENIO')
    assert not a.metadata['negotiation_validation']['payment_followup_case']
    assert not a.metadata['shared_classification']['aprobado']


def test_future_performance_after_payment_question_is_firm_not_historical_followup():
    text=('Habla MRS. Soy yo. Titular: Hice mi pago el mes pasado. '
          'Gestor: ¿Podemos contar con su pago para hoy? '
          'Titular: Para el día de mañana lo voy a realizar directamente en tienda.')
    assert payment_commitment(text)['accepted']
    a=analyze(text,fecha='2026-11-04',estatus_grabacion='CONVENIO')
    assert not a.metadata['negotiation_validation']['payment_followup_case']
    assert not payment_commitment('Titular: Lo voy a realizar directamente en la oficina de cancelaciones.')['accepted']


def test_repeated_call_complaint_blocks_paid_followup_too():
    a=analyze('Habla MRS. Soy yo. Ya lo pagué. Ya me han marcado varias veces, '
              'por eso hice el pago total para que no me siguieran molestando. '
              'Gestor: Mande su comprobante por WhatsApp.',estatus_grabacion='CONVENIO')
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert not a.metadata['shared_classification']['aprobado']
