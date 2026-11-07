"""Casos sintéticos de banca, fechas, respuestas y quejas; sin datos reales."""
import pytest
from app.services.bank_service_evidence import bank_service_payment
from app.services.conversation_evidence import holder_confirmation, payment_commitment, completed_payment
from app.services.contextual_identity_evidence import contextual_holder_confirmation
from app.services.dialogue_confirmation_evidence import future_confirmation_events
from app.services.treatment_evidence import mistreatment_reports
from app.services.payment_instruction_validation import transfer_instructions
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel


def analyze(text, **context):
    return A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo': 'ejemplo.wav', 'texto': text, 'duracion_segundos': 150}),
        dict({'fecha': '2026-11-05', 'asignacion': '1PV',
              'pago_minimo': 900, 'saldo_total': 3000}, **context))


@pytest.mark.parametrize('bank,code,expected', [
    ('BBVA', '1042378', 'BBVA'), ('Santander', '3411', 'SANTANDER'),
    ('Santander', 'treinta y cuatro once', 'SANTANDER'),
    ('Banamex', '4626', 'BANAMEX'), ('BBVA', '1042378 1042378', 'BBVA'),
])
def test_complete_literal_service_code_is_not_clabe(bank, code, expected):
    r = bank_service_payment(f'Gestor: En {bank} ingrese el número de convenio {code}.')
    assert r['authorized_banks'] == [expected]
    assert r['separates_from_clabe'] and not r['review_required']


@pytest.mark.parametrize('code', ['3412', '34113412', '34 11 7', '1233411'])
def test_no_sliding_or_truncating_bad_bank_codes(code):
    r = bank_service_payment(f'En Santander el convenio es {code}.')
    assert r['review_required'] and not r['separates_from_clabe']
    assert not r['authorized_banks']


@pytest.mark.parametrize('text', [
    'En Santander puede revisar información.',
    'Titular: En Santander el convenio es 3411.',
    'Tercero: En Santander el convenio es 3411.',
    'En Santander no corresponde al convenio 3411.',
    'En Santander el convenio es 2 pagos.',
])
def test_bank_mention_caller_or_installment_count_cannot_authorize_place(text):
    assert not bank_service_payment(text)['authorized_banks']


@pytest.mark.parametrize('destination', [
    'la CLABE', 'la cuenta bancaria', 'el número de cuenta', 'SPEI',
    'transferir a otra cuenta', 'transfiera a otra cuenta',
])
def test_service_does_not_validate_an_actual_transfer_destination(destination):
    r = bank_service_payment('Seleccione pagos de servicios en BBVA. '
                             'El convenio es 1042378. Ahora use '+destination+'.')
    assert not r['separates_from_clabe']


def test_service_with_no_dictated_code_does_not_count_a_bank():
    r = bank_service_payment('Seleccione pagos de servicios en la aplicación BBVA.')
    assert not r['authorized_banks'] and r['service_only']


def test_receipt_request_is_not_a_destination_instruction():
    assert not transfer_instructions('Cuando realice su pago tome captura de la transferencia.')
    assert transfer_instructions('Realice transferencia a la CLABE 123456789012345678.')


@pytest.mark.parametrize('declaration', [
    'He intentado hacer mi transferencia, pero la aplicación no funciona.',
    'No he podido ir hasta el fin de semana a pagar.',
    'Ya les digo si puedo o no pagar esa cantidad.',
    '¿Cuál pago? Si yo no he usado esa tarjeta.',
    'Para pagar yo requeriría que me entreguen primero la carta finiquito.',
])
def test_own_account_statements_after_a_named_request(declaration):
    assert holder_confirmation('Buenas tardes con la señora Persona Ejemplo. '+declaration)['confirmed']


@pytest.mark.parametrize('reply', [
    'Sí, gracias.', 'Soy su hija. Voy a pagar mañana.',
    'Gestor: He intentado hacer mi transferencia.',
    'Si yo tuviera mi tarjeta, pagaría mañana.',
    'Yo requeriría que me entreguen primero un número de WhatsApp.',
    '¿Ya hizo mi pago?',
])
def test_context_identity_still_requires_an_own_financial_statement(reply):
    assert not contextual_holder_confirmation('Me puede comunicar con Persona Ejemplo. '+reply, (), r'me puede comunicar con')['confirmed']


@pytest.mark.parametrize('text', [
    '¿Me podría confirmar nada más el monto que va a realizar y qué día? Sí 6800 el viernes.',
    'Vamos a ponerlo el día 8 para el pago, ¿le parece bien? Está bien.',
    'Contaríamos con su pago para el día de mañana sí perfecto.',
    'Le recuerdo el pago de 1500 pesos. Lo hago el día de hoy.',
    'Su pago de 1500. Hoy mismo lo realizo.',
    'Su pago de 1500. Yo creo que sí, pero mañana queda perfecto claro que sí.',
])
def test_concrete_future_confirmation(text):
    r = payment_commitment(text)
    assert r['accepted'] and r['contextual_confirmation_events']


@pytest.mark.parametrize('text', [
    'El monto sería 1500. Ok, gracias.',
    'Contaríamos con su pago para mañana sí perfecto, si consigo dinero.',
    'Contaríamos con su pago para mañana sí perfecto, no tengo dinero.',
    'Vamos a ponerlo el día 8 para enviar el comprobante de pago, ¿le parece bien? Está bien.',
    '¿Me podría confirmar el monto que va a realizar y qué día? Gestor: Sí 6800 el viernes.',
    '¿Me podría confirmar el monto que va a realizar y qué día? Tercero: Sí 6800 el viernes.',
    'Su número de WhatsApp. Lo hago el día de hoy.',
    'Diga que lo hago el día de hoy para el pago.',
])
def test_no_contextual_future_event_for_uncertainty_wrong_role_or_receipt(text):
    assert not future_confirmation_events(text)


def test_confirmed_payment_response_completes_named_context_but_not_family():
    text = ('Buenas tardes con la señora Persona Ejemplo. '
            '¿Me podría confirmar el monto que va a realizar y qué día? Sí 6800 el viernes.')
    assert holder_confirmation(text)['confirmed']
    assert not holder_confirmation(text+' Soy su hermana.')['confirmed']


@pytest.mark.parametrize('text', [
    'Titular: Mi cuenta ya está liquidada.',
    'Titular: Ya está en cero mi cuenta.',
])
def test_zero_account_is_reported_payment_not_bank_verification(text):
    r = completed_payment(text)
    assert r['confirmed']
    assert all(not e.get('human_verified', False) for e in r['evidence'])


@pytest.mark.parametrize('text', [
    'Gestor: Mi cuenta ya está liquidada.',
    'Titular: Si mi cuenta ya está liquidada, ¿qué tendría que hacer?',
    'Titular: ¿Mi cuenta ya está liquidada?',
])
def test_hypothetical_question_and_agent_are_not_previous_payment(text):
    assert not completed_payment(text)['confirmed']


@pytest.mark.parametrize('text', [
    'Titular: Me colgó y no pude resolver el problema.',
    'Titular: Me dices que me calle para que entienda.',
    'Titular: Mi cuenta ya está liquidada. ¿A qué se debe que me sigan llamando? Respecto a esta molestia no he tenido buenos comentarios anteriores.',
])
def test_explicit_bad_service_still_blocks_approval(text):
    assert mistreatment_reports(text, [], [])
    assert not analyze('Soy yo. '+text).metadata['shared_classification']['clasificacion'].startswith('APROBADO')


@pytest.mark.parametrize('text', [
    'Titular: No me colgó.', 'Gestor: Me colgó.',
    'Titular: Mi esposa me colgó.', 'Titular: Me están marcando seguido.',
])
def test_no_invented_bad_service_from_negation_agent_family_or_frequency(text):
    assert not mistreatment_reports(text, [], [])


def test_next_monthly_payment_is_not_current_promise():
    r = A._extract_payment_promise_date_details(
        'Su pago sería el día 8 de noviembre. Su próximo pago sería hasta el 16 de diciembre.', '2026-11-05')
    assert r['date'].isoformat() == '2026-11-08'


def test_day_range_does_not_become_next_year_date():
    r = A._extract_payment_promise_date_details(
        'Se puede pagar el día 7-8. Confirmamos su pago para el día 8 de noviembre.', '2026-11-05')
    assert r['date'].isoformat() == '2026-11-08'


def test_space_grouped_currency_is_one_amount_not_last_three_digits():
    r = analyze('Soy yo. Puede liquidar con 11 100 pesos. Voy a pagar mañana.',
                asignacion='C3', pago_minimo=11016, saldo_total=22032)
    assert r.metadata['negotiation_validation']['monto_detectado'] == 11100


def test_covering_overdue_balance_does_not_state_a_total_balance():
    r = analyze('Soy yo. Puede pagar 1800 pesos para cubrir su saldo vencido. No puedo pagar.')
    assert r.metadata['negotiation_validation']['saldo_informado_detectado'] is None


def test_past_third_person_realizo_cannot_override_a_future_agreement():
    text = ('¿Me podría confirmar el monto que va a realizar y qué día? Sí 6800 el viernes. '
            'Y lo realizó el día de hoy, se hace la actualización aproximada en cuatro horas.')
    events = future_confirmation_events(text)
    assert len(events) == 1 and 'viernes' in events[0]['evidence']


def test_fused_uncertain_asr_word_does_not_create_a_payment_promise():
    assert not future_confirmation_events('El pago es de 1500. ¡Lagó el día de hoy!')


@pytest.mark.parametrize('prefix', ['Si', 'Cuando', 'Para que', 'Usted dice que'])
def test_conditional_or_quoted_statement_is_not_own_promise(prefix):
    assert not future_confirmation_events('El pago es de 1500. '+prefix+' lo hago el día de hoy.')


def test_amount_and_date_confirmation_bind_both_literal_values():
    r = analyze('Soy yo. ¿Me podría confirmar el monto que va a realizar y qué día? '
                'Sí 1800 el viernes. Y lo realizó el día de hoy, se actualiza en cuatro horas.')
    v = r.metadata['negotiation_validation']
    assert v['monto_detectado'] == 1800
    assert v['promise_date'] == '2026-11-06'
    assert v['commitment_confirmed']


def test_percentage_reply_supersedes_old_option_without_imputing_from_excel():
    text = ('Soy yo. Le requiere un pago de 300 pesos para cubrir saldo vencido. '
            'Ahorita podría realizar un pago por el 50%, y el día 18 el otro 50%. '
            '¿Cuánto sería del 50? En este caso sería 900, sí, 900 pesos. '
            'Hoy mismo lo realizo.')
    r = analyze(text, pago_minimo=267, saldo_total=3926)
    assert r.metadata['negotiation_validation']['monto_detectado'] == 900
    assert r.metadata['negotiation_validation']['promise_date'] == '2026-11-05'


def test_percentage_without_current_payment_or_money_reply_does_not_supply_an_amount():
    from app.services.current_payment_amounts import explicit_current_amounts
    assert not explicit_current_amounts('El interés sería 50%. ¿Cuánto sería del 50? 900.')
    assert not explicit_current_amounts('Ahorita podría realizar un pago por el 50%. ¿Cuánto sería del 50? No sé.')


def test_registration_problem_alone_does_not_set_payment_status():
    assert not payment_commitment('El pago es de 1500. No me puedo registrar en la aplicación.')['accepted']
    assert not payment_commitment('El pago es de 1500. No me puedo registrar en la aplicación.').get('conditional')


@pytest.mark.parametrize('word', ['Confirmo', 'Confirmamos', 'Confirma'])
def test_payment_mention_before_contact_question_does_not_make_contact_ack_a_promise(word):
    text = word+' ese pago de 1500 para hoy. ¿Tiene el número de WhatsApp correcto? Sí, yo lo tenía previsto para mañana.'
    assert not payment_commitment(text)['accepted']


@pytest.mark.parametrize('complaint', [
    'Les marqué y les mandé WhatsApp y no me respondía, hasta los dos días.',
    'Hablé y mandé muchos mensajes y no me contestaron.',
    'Les envié la información y no me respondieron.',
])
def test_collection_contact_ignored_is_a_service_complaint(complaint):
    assert mistreatment_reports('Titular: '+complaint, [], [])


@pytest.mark.parametrize('text', [
    'Gestor: Les marqué y no me contestaron.',
    'Titular: Les marqué. No es cierto que no me respondieron.',
    'Titular: Le marqué a mi esposa y no me respondió.',
    'Titular: ¿Si les envié mensajes y no me respondieron, qué debo hacer?',
])
def test_service_contact_complaint_preserves_speaker_negation_family_and_question_guards(text):
    assert not mistreatment_reports(text, [], [])


@pytest.mark.parametrize('phrase', [
    'No lo hago el día de hoy.', 'Nunca lo hago el día de hoy.',
    'Jamás lo hago el día de hoy.', '¿Lo hago el día de hoy?',
    'Lo hago el día de hoy?',
])
def test_negated_or_questioned_action_is_not_a_positive_payment_event(phrase):
    assert not future_confirmation_events('El pago sería de 1500. '+phrase)
