"""Regresión de respuestas de recados y dictado ARCO; ejemplos sintéticos."""
import pytest
from app.services.conversation_evidence import assess_recado,dictated_privacy_email
from app.services.message_contact_evidence import message_contact_evidence,directed_relay_message
from app.services.arco_validation import assess_arco,document_requests
from app.services.arco_context_evidence import line_tenure_reply,wrong_number_reply
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel


@pytest.mark.parametrize('text',[
    '¿Qué relación presenta con la señora? Mi mamá.',
    '¿Qué relación tiene con el señor? Con mi hermano.',
    '¿Qué relación presenta con la titular? Su hija.',
    'Es mi esposa, quién la busca?',
])
def test_family_relationship_from_local_answer_not_erased_by_following_question(text):
    assert assess_recado(text)['family']


@pytest.mark.parametrize('text',[
    '¿Qué relación presenta con la señora? Gestor: Mi mamá.',
    '¿Qué relación presenta con la señora? ¿Mi mamá?',
    'Diga que es mi esposa.',
    'No es mi esposa, quién la busca?',
    'Es mi esposa, ¿verdad?',
    'Titular: Es mi esposa.',
])
def test_family_requires_recipient_assertion_without_negation_quote_or_question(text):
    assert not assess_recado(text)['family']


@pytest.mark.parametrize('reply',[
    '¿Tiene dónde notar? Ajá.',
    '¿Tiene con qué anotar? Me indica por favor. Sí, dígame.',
    '¿Tiene dónde anotar para proporcionarle el número del teléfono? Ajá.',
])
def test_accepting_a_callback_dictation_in_message_context_is_reception(reply):
    text='Es mi hermana. Le puedo dejar un recado. '+reply+' Es 5551234567. Dígale que se comunique con nosotros.'
    assert assess_recado(text)['acceptance']


@pytest.mark.parametrize('reply',[
    '¿Tiene dónde notar? Gestor: Ajá.',
    'No tiene dónde anotar. Sí.',
    '¿Tiene dónde anotar? ¿Sí?',
    'Dice que tiene dónde anotar. Sí.',
])
def test_dictation_does_not_infer_acceptance_from_agent_quote_negative_or_question(reply):
    text=reply+' Dígale que se comunique con nosotros.'
    assert not assess_recado(text)['acceptance']


@pytest.mark.parametrize('reply',[
    'Me lo dicta, por favor?', 'A ver, dígame.', 'Dígame usted el número, por favor.',
])
def test_explicit_request_to_dictate_callback_number_is_reception(reply):
    text='Le voy a dejar un número para que ella se comunique con nosotros. '+reply+' El número es 5551234567.'
    assert assess_recado(text)['acceptance']


@pytest.mark.parametrize('reply',[
    'No me lo dicta, por favor.', 'Gestor: A ver, dígame.',
    'Diga que me lo dicta, por favor.',
])
def test_dictation_request_has_role_negation_and_quote_guards(reply):
    text='Le voy a dejar un número para que ella se comunique con nosotros. '+reply+' El número es 5551234567.'
    assert not assess_recado(text)['acceptance']


def test_actual_return_message_and_acceptance_identify_generic_third_party_not_family():
    text=('Habla MRS. Le puedo dejar un recado y un número de teléfono con usted para que se lo proporcione. '
          'Claro. El número es 5551234567. Indíquele al señor que se comunique con nosotros.')
    model=TranscriptionModel.from_dict(dict(archivo='sample.ogg',texto=text,duracion_segundos=120))
    a=A.analyze_transcription(model,{'estatus_grabacion':'MENSAJE CON TERCERO'})
    assert a.metadata['quality_contact_type']=='TERCERO'
    assert a.metadata['status_validation']['detected_status']=='MENSAJE CON TERCERO'
    assert a.metadata['shared_classification']['clasificacion']=='APROBADO'
    assert not assess_recado(text)['family']


@pytest.mark.parametrize('text',[
    'Gracias por aceptar el mensaje. Indíquele al señor que se comunique con nosotros.',
    'Indíquele al señor que se comunique con nosotros.',
])
def test_unilateral_callback_or_thanks_does_not_certify_recipient_acceptance(text):
    assert not assess_recado(text)['acceptance']


@pytest.mark.parametrize('text',[
    'No indique al señor que se comunique con nosotros.',
    'Dijo que indique al señor que se comunique con nosotros.',
    '¿Le dice que se comunique con nosotros?',
    'Titular: Indique al señor que se comunique con nosotros.',
])
def test_directed_return_message_requires_agent_or_unattributed_declaration(text):
    assert not directed_relay_message(text)


@pytest.mark.parametrize('dictation',[
    'El correo es privacidad uno arroba bradesco punto com punto mx.',
    'Privacidad. Número uno. Arroba. Bradesco. Punto com punto mx.',
    'El correo es privacidad. Privacidad. Número uno. ¿Arroba? Bradesco. Punto com punto mx.',
    'Privacidad1. Arroba. Bradesco. B de bueno. .com.mx.',
])
def test_complete_spoken_domain_is_parsed_without_guessing_missing_components(dictation):
    result=dictated_privacy_email(dictation)
    assert result['detected'] and result['address']=='privacidad1@bradesco.com.mx'


@pytest.mark.parametrize('text',[
    'Privacidad uno arroba bradesco punto mx.',
    'Privacidad dos arroba bradesco punto com punto mx.',
    'Privacidad uno arroba bradescard punto com punto mx.',
    'Privacidad uno arroba gmail punto com. Bradesco punto com punto mx.',
    'Privacidad uno arroba bradesco punto com punto mx punto estafa.',
    'No es privacidad uno arroba bradesco punto com punto mx.',
    'Titular: Privacidad uno arroba bradesco punto com punto mx.',
])
def test_incomplete_wrong_negated_or_recipient_email_stays_unconfirmed(text):
    assert not dictated_privacy_email(text)['detected']


@pytest.mark.parametrize('text',[
    '¿Cuánto tiempo tiene con este número? Más de ocho años.',
    '¿Cuánto tiempo lleva con su línea? Aproximadamente dos meses.',
    '¿Cuánto tiempo tiene con el número? Como un mes.',
])
def test_tenure_response_after_line_question_is_not_omitted(text):
    assert line_tenure_reply(text)['confirmed']


@pytest.mark.parametrize('text',[
    '¿Cuánto tiempo tiene con este número? Gestor: Más de ocho años.',
    '¿Cuánto tiempo lleva recibiendo llamadas a este número? Dos meses.',
    'Ocho años.',
])
def test_tenure_does_not_use_agent_answer_or_time_receiving_calls(text):
    assert not line_tenure_reply(text)['confirmed']


def test_document_request_is_not_negated_by_unrelated_account_name_denial():
    text='El número ya no pertenece a esa persona; adjunte su INE y el comprobante de la línea.'
    assert document_requests(text)['both_documents_requested']


@pytest.mark.parametrize('text',[
    'No adjunte su INE ni el comprobante de la línea.',
    'No es necesario enviar su INE ni el comprobante de la línea.',
    'Titular: Voy a enviar mi INE y el comprobante de la línea.',
    '¿Cuenta con INE y comprobante de la línea?',
])
def test_documents_remain_required_and_are_not_invented_from_mention(text):
    assert not document_requests(text)['both_documents_requested']


def test_explicit_removal_process_with_rights_is_not_restricted_to_word_ejercer():
    text=('Envíe al correo la leyenda: deseo mi derecho ARCO y sea borrado mi número de su base de datos. '
          'Adjunte su INE y comprobante de la línea.')
    result=assess_arco(text,email_given=True)
    assert result['rights_mentioned'] and result['process_explained'] and result['complete_procedure']
    assert not assess_arco(text.replace('mi derecho ARCO','la baja'),email_given=True)['complete_procedure']


def test_fragmented_rights_words_still_require_both_documents():
    text=('El correo es privacidad uno arroba bradesco punto com punto mx. '
          'Escriba deseo mi derecho. ARCO. Y sea borrado mi número de su base de datos. Envíe su INE.')
    result=assess_arco(text,email_given=True)
    assert result['rights_mentioned'] and result['process_explained']
    assert not result['complete_procedure']


@pytest.mark.parametrize('generic',['saldo pendiente','saldo vencido'])
@pytest.mark.parametrize('role',['GESTOR','NO DETERMINADO'])
def test_user_allows_both_generic_balances_with_last_four_and_callback_phone(generic,role):
    from app.services.conversation_evidence import assess_privacy
    text='Es por el '+generic+' de la tarjeta, terminación 4455. Llame al 5551234567.'
    p=assess_privacy(text,[{'text':text,'speaker_role':role}],third_party_confirmed=True)
    assert not p['review_required'] and not p['confirmed_disclosure']
    assert p['allowed_generic_balance_mentions']


@pytest.mark.parametrize('generic',['saldo pendiente','saldo vencido'])
@pytest.mark.parametrize('suffix',[' de 1500 pesos.',' de mil quinientos pesos.','. Son 1500 pesos.'])
def test_generic_balance_permission_does_not_allow_its_amount(generic,suffix):
    from app.services.conversation_evidence import assess_privacy
    text='Tiene un '+generic+suffix
    p=assess_privacy(text,[{'text':text,'speaker_role':'GESTOR'}],third_party_confirmed=True)
    assert p['confirmed_disclosure']


@pytest.mark.parametrize('text',[
    'Tiene cuatro años de atraso.',
    'Presenta cinco meses que no se ha efectuado pago.',
    'Tiene tres mensualidades vencidas.',
    'La tarjeta es 1111222233334444.',
    'Tiene una deuda.',
])
def test_mora_and_other_protected_information_are_still_protected_without_balance_amount(text):
    from app.services.conversation_evidence import assess_privacy
    assert assess_privacy(text,[{'text':text,'speaker_role':'GESTOR'}],third_party_confirmed=True)['confirmed_disclosure']


def test_offered_callback_without_dictation_does_not_approve_a_recado():
    text=('Habla MRS. Soy su hermana. Dígale que se comunique inmediatamente. '
          'Le dejaré un número telefónico. ¿Tiene dónde anotar? Ok. No tengo otro número disponible.')
    model=TranscriptionModel.from_dict(dict(archivo='sample.ogg',texto=text,duracion_segundos=120))
    a=A.analyze_transcription(model,{'estatus_grabacion':'MENSAJE CON FAMILIAR'})
    assert a.metadata['message_delivery_validation']['review_required']
    assert not a.metadata['shared_classification']['aprobado']


def test_explicit_complaint_of_repeated_calls_after_cancellation_is_not_approved():
    from app.services.treatment_evidence import mistreatment_reports
    assert mistreatment_reports('La tarjeta ya está cancelada. Es molesto que estén marque y marque.',[],[])
    assert not mistreatment_reports('Gestor: La tarjeta ya está cancelada. Gestor: Es molesto que estén marque y marque.',[],[])


@pytest.mark.parametrize('text',[
    '¿Le conoce? No.', '¿La conoce, señorita? No.', '¿Lo conoce? No, señorita.',
])
def test_denial_to_positive_knowledge_question_is_explicit_unknown_contact(text):
    from app.services.arco_context_evidence import positive_knowledge_denial
    assert positive_knowledge_denial(text)['confirmed']


@pytest.mark.parametrize('text',[
    '¿No le conoce? No.', '¿Le conoce? ¿No?',
    '¿Le conoce? Gestor: No.',
    '¿Le conoce? No. Es mi hermana.',
])
def test_ambiguous_negative_question_agent_and_family_contradiction_do_not_confirm_unknown(text):
    from app.services.arco_context_evidence import positive_knowledge_denial
    assert not positive_knowledge_denial(text)['confirmed']


@pytest.mark.parametrize('text',[
    '¿Cuánto tiempo lleva con su línea? Yo tengo como un mes.',
    '¿Cuánto tiempo tiene con el número? Ya tengo como tres años.',
    'Cuánto tiempo lleva con su línea de teléfono. Aproximadamente dos meses.',
])
def test_explicit_line_ownership_duration_survives_asr_point_and_approximation(text):
    assert line_tenure_reply(text)['confirmed']


def test_taking_message_at_work_is_a_recipient_statement():
    assert assess_recado('Le tomamos el recado, dígame.')['acceptance']
    assert not assess_recado('Gestor: Le tomamos el recado, dígame.')['acceptance']


def test_echoed_phone_dictation_is_not_claimed_as_a_reconstructed_number():
    from app.services.message_contact_evidence import callback_dictation_fragments,unfinished_callback_offer
    text=('Le dejaré un número telefónico. El número es 55, 24. Sí. 52. Ajá. 27, 37. '
          'Dígale que se comunique con nosotros.')
    evidence=callback_dictation_fragments(text)
    assert evidence and evidence[0]['contact_digits_verified'] is False
    assert not unfinished_callback_offer(text)['review_required']


@pytest.mark.parametrize('question',[
    '¿Podría dictarle un número de llamada para que se comunique con nosotros?',
    '¿Le puedo dejar lo que es un recado con usted?',
    '¿Lo puede anotar?',
    '¿Me puede anotar un número?',
])
def test_callback_permission_variants_do_not_require_word_dejar_recado(question):
    text='Soy su hermana. '+question+' Sí. Es el número 5551234567 para que se comunique con nosotros.'
    assert assess_recado(text)['acceptance']


@pytest.mark.parametrize('prefix', ['No ', 'Dice que ', 'Diga que '])
def test_callback_permission_still_rejects_negation_and_quotation(prefix):
    text=prefix+'le puedo dejar lo que es un recado con usted. Sí. Que se comunique al número 5551234567.'
    assert not assess_recado(text)['acceptance']


@pytest.mark.parametrize('question',[
    '¿Le podría entonces dejar un número de contacto con usted y en cuanto llegue se lo pudiera proporcionar?',
    '¿Me permite dejarle el número?',
    '¿Le puedo dejar un aviso y un número de teléfono para que se lo proporcione?',
    '¿Tienen dónde tomar notas?',
])
def test_natural_permission_frames_still_require_the_recipient_answer(question):
    text='Soy su hermana. '+question+' Sí. El número es 5551234567. Dígale que se comunique con nosotros.'
    assert assess_recado(text)['acceptance']
    text='Soy su hermana. '+question+' Gestor: Sí. El número es 5551234567. Dígale que se comunique con nosotros.'
    assert not assess_recado(text)['acceptance']


def test_name_directed_callback_plus_acceptance_is_actual_message_content():
    text=('Habla MRS. No se encuentra. Le puedo dejar un número para que se lo proporcione. '
          '¿Tiene dónde anotar? Sí. El número es 5551234567. '
          'Indica al señor Carlos que se comunique con nosotros.')
    a=A.analyze_transcription(TranscriptionModel.from_dict(dict(archivo='sample.ogg',texto=text,duracion_segundos=120)),
                              {'estatus_grabacion':'MENSAJE CON TERCERO'})
    assert a.metadata['quality_contact_type']=='TERCERO'
    assert a.metadata['shared_classification']['aprobado']


def test_spoken_email_suffix_with_readback_acknowledgements_is_explicit_not_completed():
    e=dictated_privacy_email('Privacidad uno arroba bradesco. Punto com. Sí. Punto mx.')
    assert e['detected'] and e['address']=='privacidad1@bradesco.com.mx'


def test_unknown_contact_extensions_do_not_override_explicit_holder_identity():
    text='Habla MRS. Soy yo. ¿Le conoce? No. Esta es mi tarjeta. No puedo pagar.'
    a=A.analyze_transcription(TranscriptionModel.from_dict(dict(archivo='sample.ogg',texto=text,duracion_segundos=120)),
                              {'estatus_grabacion':'NEGATIVA DE PAGO'})
    assert a.metadata['quality_contact_type']=='TITULAR'
    assert not a.metadata['arco_validation']['applies']


def test_email_sentence_can_be_followed_by_instructions_without_becoming_a_domain_extension():
    email=dictated_privacy_email('El correo es privacidad uno arroba bradesco punto com punto mx. Adjunte su INE.')
    assert email['detected']
    assert not dictated_privacy_email('Privacidad uno arroba bradesco punto com punto mx punto estafa.')['detected']


def test_role_labelled_line_duration_keeps_the_actual_answer_role():
    assert line_tenure_reply('Gestor: ¿Cuánto tiempo tiene con su línea? Tercero: Más de ocho años.')['confirmed']
    assert not line_tenure_reply('Gestor: ¿Cuánto tiempo tiene con su línea? Gestor: Más de ocho años.')['confirmed']


@pytest.mark.parametrize('denial',[
    'No es necesario ejercer derechos ARCO.',
    'No se requiere tramitar derechos ARCO.',
    'No hace falta solicitar derechos ARCO.',
])
def test_explicit_denial_of_arco_does_not_pass_through_removal_explanation(denial):
    text=denial+' Envíe al correo deseo mi derecho ARCO y sea borrado mi número de su base de datos. Adjunte INE y comprobante de la línea.'
    r=assess_arco(text,email_given=True)
    assert r['process_denied'] and not r['complete_procedure']


def test_remote_arco_does_not_require_visiting_bank_and_recipient_denial_is_not_agent_denial():
    body='Envíe al correo deseo mi derecho ARCO y sea borrado mi número de su base de datos. Adjunte INE y comprobante de la línea.'
    assert assess_arco('No es necesario ir al banco para ejercer derechos ARCO. '+body,email_given=True)['complete_procedure']
    assert assess_arco('Tercero: No es necesario ejercer derechos ARCO.\nGestor: '+body,email_given=True)['complete_procedure']
