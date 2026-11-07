"""Criterio operativo de identificación contextual; datos sintéticos."""
import pytest
from app.services.conversation_evidence import holder_confirmation,completed_payment
from app.services.reported_payment_amounts import money_value,mixed_digit_thousands
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A

QUESTION='¿Me puede comunicar con Persona de Ejemplo? Sí.'

@pytest.mark.parametrize('response',[
    'No he podido pagar todavía.',
    'Ya lo pagué ayer. ¿Necesita el comprobante?',
    'Yo hice el pago. Fueron 950 pesos.',
    'Mi tarjeta ya está al corriente.',
    'Yo no he usado esa tarjeta.',
    'Yo voy a pagar el viernes.',
    'Ya he pagado en tienda.',
    'Lo hice por 950 pesos.',
])
def test_nominal_yes_and_own_account_conversation_identifies_holder(response):
    text=QUESTION+' Gracias. Habla MRS sobre el pago de su tarjeta. '+response
    r=holder_confirmation(text)
    assert r['confirmed'] and r['evidence']


@pytest.mark.parametrize('response',[
    '', 'Gracias por recibir el recado.', 'No tengo trabajo.',
    'Soy su hermana. Ya lo pagué ayer.',
    'No se encuentra. Yo tengo una tarjeta.',
    'Espere, le paso al titular. Ya hice el pago.',
    'Yo pagué por mi padre.',
    'No es mi tarjeta, yo tengo otra cuenta.',
    'Si yo tuviera mi tarjeta, le diría.',
    'El cliente dice que mi tarjeta ya está pagada.',
    'Para que lo pague, primero tiene que ir a la tienda.',
])
def test_context_does_not_invent_holder_from_incomplete_or_third_party_reply(response):
    text=QUESTION+' Habla MRS sobre el pago de su tarjeta. '+response
    assert not holder_confirmation(text)['confirmed']


def test_known_agent_cannot_supply_own_account_evidence_for_a_bare_yes():
    text=QUESTION+' Gestor: Mi tarjeta ya está pagada.'
    assert not holder_confirmation(text)['confirmed']


def test_known_third_party_reply_is_not_holder_even_with_payment_statement():
    text=QUESTION+' Ya lo pagué ayer.'
    segments=[{'texto':text,'inicio':0,'fin':10,'speaker_role':'TERCERO'}]
    assert not holder_confirmation(text,segments)['confirmed']


@pytest.mark.parametrize('opening',[
    '¿Lo vendía con el señor Persona de Ejemplo? Sí, servidor.',
    '¿Me podría convocar con la señorita Persona de Ejemplo? Sí, dígame.',
    '¿Con la señora Persona de Ejemplo? Al habla.',
])
def test_explicit_identity_reply_survives_damaged_prefix(opening):
    assert holder_confirmation(opening)['confirmed']


def test_identity_does_not_certify_that_an_unpaid_account_is_paid():
    text=QUESTION+' Sobre su tarjeta. No he podido pagar todavía.'
    assert holder_confirmation(text)['confirmed']
    assert not completed_payment(text)['confirmed']


@pytest.mark.parametrize('phrase,value',[
    ('8 mil',8000),('8 mil 792',8792),('8 mil setecientos noventa y dos',8792),
    ('11 mil',11000),('11 mil 221',11221),('mil 216',1216),('dos mil 150',2150),
])
def test_explicit_mixed_thousands_are_parsed_without_account_guesses(phrase,value):
    assert money_value(phrase)==value


def test_malformed_thousands_are_not_completed_from_expected_balance():
    assert money_value('11 mil 1221') is None


def test_mixed_thousands_cover_the_whole_amount_not_just_eight_pesos():
    r=mixed_digit_thousands('El pago mínimo es de 8 mil pesos.')
    assert len(r)==1 and r[0][2]==8000 and r[0][3]=='8 mil pesos'
    a=A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo':'synthetic.wav','texto':'Habla MRS. Soy yo. Su saldo total es de 8 mil pesos.',
        'duracion_segundos':100}),{'saldo_total':'8300'})
    assert a.metadata['negotiation_validation']['saldo_informado_detectado']==8000
    assert a.metadata['negotiation_validation']['validacion_saldo_informado']!='SALDO INFORMADO CORRECTO'


def test_telephone_thousands_are_not_a_negotiated_payment():
    a=A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo':'synthetic.wav','texto':'Habla MRS. Soy yo. Su teléfono es 8 mil 792.',
        'duracion_segundos':100}),{})
    assert a.metadata['negotiation_validation']['monto_detectado'] is None


@pytest.mark.parametrize('question',[
    '¿Confirmaría su pago para mañana? Sí, por favor.',
    '¿Confirmaría entonces su pago para mañana? Sí.',
    '¿Se confirmaría ese pago para mañana? Sí, por favor.',
    '¿Sería posible su pago para el día 7? Claro que sí.',
])
def test_payment_question_does_not_require_the_word_payment_twice(question):
    from app.services.conversation_evidence import payment_commitment
    assert payment_commitment('Gestor: '+question)['accepted'] is False
    # Etiquetas separadas: el sí lo dice el interlocutor, no el gestor.
    q,answer=question.split('?',1)
    assert payment_commitment('Gestor: '+q+'? Titular: '+answer)['accepted']
    assert payment_commitment(question)['accepted']


@pytest.mark.parametrize('question',[
    '¿Confirmaría su pago para mañana? Sí, si consigo dinero.',
    '¿Se confirmaría ese pago para mañana? No tengo esa cantidad.',
    '¿Podemos confirmar el pago realizado ayer? Sí.',
])
def test_conditional_reply_or_completed_payment_is_not_a_firm_future_acceptance(question):
    from app.services.conversation_evidence import payment_commitment
    assert not payment_commitment(question)['accepted']


@pytest.mark.parametrize('statement',[
    'Ese pago ya se realizó el martes.',
    'Yo ya hice ese pago.',
    'Ya hice el depósito ayer.',
    'Yo deposité el lunes.',
])
def test_completed_deposit_and_demonstrative_payment_are_reports(statement):
    assert completed_payment(statement)['confirmed']


@pytest.mark.parametrize('statement',[
    'Cuando recibamos su dinero le enviaremos que ese pago ya se realizó.',
    'En caso de que ese pago ya se realizó se revisará el recibo.',
    'Vamos a enviar un mensaje de que ese pago ya se realizó.',
])
def test_future_receipt_notice_does_not_certify_a_current_deposit(statement):
    assert not completed_payment(statement)['confirmed']


def test_a_new_accepted_dated_agreement_cannot_use_old_payment_followup_exemption():
    from app.services.conversation_evidence import payment_commitment
    text=('Habla MRS. Soy yo. Ya hice mi pago anterior. '
          'Gestor: Podemos poner su convenio para el día 8. Titular: Ajá, sí, está bien.')
    assert payment_commitment(text)['accepted']
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':100}),
        {'fecha':'2026-11-05','asignacion':'1PV','pago_minimo':'900','saldo_total':'3000','estatus_grabacion':'CONVENIO'})
    assert not a.metadata['negotiation_validation']['payment_followup_case']
    assert 'PEN_CONV_LUGARES' in {p['id'] for p in a.metadata['penalties']}


def test_sending_captures_repeatedly_is_a_report_not_bank_confirmation():
    from app.services.operational_script_evidence import receipt_request_evidence
    r=receipt_request_evidence('Ya los pasé diez veces las capturas de que ya pagué, a WhatsApp.')
    assert r['reported_sent']


def test_paid_customer_requesting_an_end_to_repeated_calls_remains_blocked():
    text='Habla MRS. Soy yo. Ya no estarme hablando, ya les pasé las capturas de que ya pagué.'
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':100}),
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO'})
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert not a.metadata['shared_classification']['aprobado']


def test_named_person_can_say_dime_after_company_identification():
    text='Buen día con Persona de Ejemplo. ¿Quién habla? Corporativo MRS. Dime.'
    assert holder_confirmation(text)['confirmed']


def test_payment_confirmation_in_progressive_form_is_still_an_answered_question():
    from app.services.conversation_evidence import payment_commitment
    assert payment_commitment('¿Estarías confirmando el pago en tres? Sí, el 6, 12 y 18.')['accepted']


def test_repeated_paid_collection_disrupting_work_is_a_complaint():
    text=('Habla MRS. Soy yo. Hoy me han estado hablando toda la mañana y me estoy saliendo de mi trabajo. '
          'Ese pago ya se realizó. Le mandé el comprobante.')
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':100}),
        {'estatus_grabacion':'CONVENIO'})
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('text',[
    'Tengo el gusto con Persona de Ejemplo. En dado caso si es que se realice el pago por 4800 hoy.',
    '¿Me puede comunicar con Persona de Ejemplo? Sí. Para que se realice el pago, espere al lunes.',
    '¿Me podría comunicar con la señorita? Lo hice ayer, el pago de mi tarjeta.',
])
def test_impersonal_payment_instruction_or_missing_name_cannot_identify_holder(text):
    assert not holder_confirmation(text)['confirmed']


def test_transfer_amounts_contradicting_the_reported_total_require_review():
    from app.services.reported_payment_amounts import reported_amounts
    text=('Ya realicé el pago por transferencia, el total es de 3660. '
          'Yo hice una transferencia de 2660 hace una hora.')
    binding=reported_amounts(text,completed_payment(text))
    assert binding['review_required'] and binding['total'] is None


def test_nonconflicting_completed_transfer_remains_a_valid_report():
    from app.services.reported_payment_amounts import reported_amounts
    text='Yo hice una transferencia de 2660 hace una hora.'
    binding=reported_amounts(text,completed_payment(text))
    assert binding['total']==2660 and not binding['review_required']


def test_unanswered_service_and_abandoned_transfer_are_complaints():
    text=('Habla MRS. Soy yo. No puedo hablar con nadie, nadie me contesta. '
          'Me dejó en la línea y nadie me contestó.')
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':100}),{})
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert not a.metadata['shared_classification']['aprobado']


def test_explicit_remaining_payment_cannot_hide_under_a_paid_followup():
    text=('Habla MRS. Soy yo. Ya pagué 1100 pesos ayer. '
          'Gestor: Le queda un pago de 2305. Ese pago lo puede realizar el 7 de noviembre. '
          'Espero su comprobante por WhatsApp.')
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':100}),
        {'estatus_grabacion':'CONVENIO','fecha':'2026-10-31','pago_minimo':'1083','saldo_total':'3405'})
    assert a.metadata['negotiation_validation']['unaccepted_new_payment_instruction']
    assert not a.metadata['shared_classification']['aprobado']


def test_paid_total_and_transfer_conflict_remains_blocked_in_full_analysis():
    text=('Habla MRS. Soy yo. Ya realicé el pago por transferencia, el total es de 3660. '
          'Yo hice una transferencia de 2660 hace una hora. Gestor: Comparta el comprobante.')
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':100}),
        {'estatus_grabacion':'CONVENIO','pago_minimo':'1070','saldo_total':'4760'})
    assert not a.metadata['shared_classification']['aprobado']
