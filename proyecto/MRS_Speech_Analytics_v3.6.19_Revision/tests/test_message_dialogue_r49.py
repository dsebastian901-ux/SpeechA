"""Respuestas naturales, rechazo comprobable y seguridad: ejemplos sintéticos."""
import pytest
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import assess_recado,holder_confirmation
from app.services.message_contact_evidence import unfinished_callback_offer
from app.models.transcriptions import TranscriptionModel

def analyze(text,status='MENSAJE CON FAMILIAR',duration=130):
    return A.analyze_transcription(TranscriptionModel.from_dict(dict(archivo='sample.ogg',texto=text,duracion_segundos=duration)),{'estatus_grabacion':status})

@pytest.mark.parametrize('reply',['Ajá, dígame.','Claro, la escucho.','Ya.','A ver, démelo.','Ah, sí.'])
def test_note_preparation_answers_are_receipt_with_actual_message(reply):
    text='Habla MRS. Soy su hermana. Le dejo un recado. ¿Tiene dónde escribir? '+reply+' El número telefónico es 5551234567. Dígale que se comunique.'
    assert assess_recado(text)['acceptance']
    assert analyze(text).metadata['shared_classification']['aprobado']
    assert not assess_recado(text.replace(reply,'Gestor: '+reply))['acceptance']


def test_sender_le_digo_hablamos_is_not_recipient_acceptance():
    text='Habla MRS. El número telefónico es 5551234567. Dígale que se comunique con nosotros. Le digo, hablamos de jurídico MRS.'
    assert not assess_recado(text)['acceptance']
    assert not analyze(text,'MENSAJE CON TERCERO').metadata['shared_classification']['aprobado']


def test_relatives_and_arco_instructions_are_not_nominal_holder_identity():
    text='No la conozco. Habló con su hija para que ya su hija pueda solicitar el derecho ARCO. Sí, está bien.'
    assert not holder_confirmation(text)['confirmed']


def test_phone_readback_confirms_receipt_not_an_amount_or_card():
    text='Habla MRS. Soy su hermana. Le voy a proporcionar un número telefónico para que se comunique. El número es 55, 51, 23, 45, 67. ¿Me lo podría repetir de favor? 55, 51, 23, 45, 67. Dígale que se comunique.'
    assert any(e.get('method')=='LECTURA_DE_VUELTA_TRAS_SOLICITUD_TELEFONICA'for e in assess_recado(text)['acceptance'])
    assert analyze(text).metadata['shared_classification']['aprobado']
    financial=text.replace('¿Me lo podría repetir','Su saldo es 1000 pesos. ¿Me lo podría repetir')
    assert not any(e.get('method')=='LECTURA_DE_VUELTA_TRAS_SOLICITUD_TELEFONICA'for e in assess_recado(financial)['acceptance'])

@pytest.mark.parametrize('text',[
 'Habla MRS. ¿Qué relación que presenta con la señora? Mi mamá.',
 'Habla MRS. ¿Qué es de usted? Prima.',
 'Habla MRS. Es compañero mío de trabajo.',
])
def test_contextual_relationship_answers(text):
    assert assess_recado(text)['family']or assess_recado(text)['work_relationships']


def test_explicit_refusal_is_closed_without_approving_or_clearing_security():
    text='Habla MRS. Soy su hermana. No quiero recibir el recado.'
    a=analyze(text);d=a.metadata['shared_classification']
    assert d['clasificacion']=='NO_APROBADO'and not d['aprobado']
    assert a.metadata['explicit_message_refusal']['confirmed']
    unsafe=analyze(text+' Tiene una deuda de 1500 pesos.').metadata['shared_classification']
    assert unsafe['clasificacion']=='REVISAR'

@pytest.mark.parametrize('text',[
 'Gestor: No quiero recibir el recado.',
 'Habla MRS. Diga que no quiero recibir el recado.',
 'Habla MRS. ¿No quiero recibir el recado?',
 'Habla MRS. Si no quiero recibir el recado, ¿qué pasa?',
])
def test_quoted_question_or_sender_refusal_is_not_recipient_failure(text):
    assert analyze(text).metadata['shared_classification']['clasificacion']!='NO_APROBADO'


def test_short_duration_with_security_uncertainty_remains_review():
    assert analyze('Habla MRS. Soy su hermana.',duration=40).metadata['shared_classification']['clasificacion']=='NO_APROBADO'
    assert analyze('Habla MRS. Soy su hermana. Tiene una deuda de 1500 pesos.',duration=40).metadata['shared_classification']['clasificacion']=='REVISAR'


def test_declined_note_without_contact_is_definitive_but_later_delivery_is_not():
    text='Habla MRS. Soy su hermana. Le voy a dejar un número telefónico. No tengo dónde anotar. Nos comunicamos más tarde.'
    assert analyze(text).metadata['shared_classification']['clasificacion']=='NO_APROBADO'
    delivered=text.replace('Nos comunicamos más tarde.','Ya tengo papel. El número telefónico es 5551234567. Dígale que se comunique.')
    assert not analyze(delivered).metadata['explicit_message_refusal']['confirmed']
    alternative=text.replace('Nos comunicamos más tarde.','Mándelo por mensaje de texto.')
    assert not analyze(alternative).metadata['explicit_message_refusal']['confirmed']


def test_indirect_contact_return_and_bare_friend_reply_are_supported():
    text='Habla MRS. ¿Qué parentesco presenta con el caballero? Amigo. ¿Tiene dónde escribir? Ya. El número telefónico es 5551234567. Dígale que se pueda poner en contacto con nosotros.'
    a=analyze(text,'MENSAJE CON TERCERO')
    assert a.metadata['quality_contact_type']=='TERCERO'
    assert a.metadata['shared_classification']['aprobado']
    assert not assess_recado(text.replace('Amigo.','Gestor: Amigo.'))['third_party_relationships']


def test_nominal_relative_reply_requires_positive_family_utterance():
    assert assess_recado('¿Es usted el titular? No, su hermano.')['family']
    assert not assess_recado('¿Es usted el titular? Gestor: No, su hermano.')['family']


def test_accepted_question_can_be_the_message_purpose_when_number_is_delivered():
    text=('Habla MRS. ¿Le podría dejar un número telefónico para que la señorita Luisa se pueda comunicar con nosotros? '
          'Ah, ok. El número es 5551234567.')
    a=analyze(text,'MENSAJE CON TERCERO');assert a.metadata['quality_contact_type']=='TERCERO'
    assert a.metadata['shared_classification']['aprobado']
    assert not analyze(text.replace('Ah, ok.',''),'MENSAJE CON TERCERO').metadata['shared_classification']['aprobado']
    assert not analyze(text.replace('El número es 5551234567.',''),'MENSAJE CON TERCERO').metadata['shared_classification']['aprobado']
    assert not analyze(text+' Tiene una deuda de 1500 pesos.','MENSAJE CON TERCERO').metadata['shared_classification']['aprobado']


def test_callback_word_variant_accredits_dictation_without_reconstructing_digits():
    from app.services.message_contact_evidence import callback_dictation_fragments
    from app.services.payment_reference_validation import callback_numbers
    text='El número telefónico es cincuenta y cinco, veinticuatro, cincuenta y dos, veinticiete, treinta y siete.'
    r=callback_dictation_fragments(text);assert r and not r[0]['contact_digits_verified']
    assert r[0]['uncertain_number_words']==['veinticiete']
    assert not callback_numbers(text)


def test_wait_then_readiness_and_actual_phone_is_reception():
    text='Habla MRS. Soy su hermana. Le dejo un recado. No sé si tenga dónde anotar. Permítame tantito. Claro. A ver. El número telefónico es 5551234567. Dígale que se comunique.'
    assert analyze(text).metadata['shared_classification']['aprobado']
    assert not analyze(text.replace('A ver. El número telefónico es 5551234567.','No puedo.')).metadata['shared_classification']['aprobado']


def test_recipient_promise_before_vale_question_is_reception():
    text='Habla MRS. El número telefónico es 5551234567. Que se comunique con nosotros. Yo le paso su recado, ¿vale?'
    assert analyze(text,'MENSAJE CON TERCERO').metadata['shared_classification']['aprobado']
    assert not assess_recado('¿Yo le paso su recado?')['acceptance']


def test_information_offer_and_contact_are_an_accepted_message():
    text=('Habla MRS. Soy su hermano. ¿Cree que le pueda dejar una pequeña información a usted para que se lo deje al caballero? Sí. '
          'Le estaría otorgando lo que es un número telefónico para que el caballero se pueda poner en contacto con nosotros. '
          'No sé si tenga dónde anotar. Permítame tantito. Claro. A ver. Mire, sería el 55, 51, 23, 45, 67.')
    assert analyze(text).metadata['shared_classification']['aprobado']


def test_split_arrears_asr_word_remains_review_not_confirmed_disclosure():
    from app.services.conversation_evidence import assess_privacy
    v=assess_privacy('Gestor: Presenta un mes de atrás o.',third_party_confirmed=True)
    assert v['review_required']and not v['confirmed_disclosure']

@pytest.mark.parametrize('phrase',[
 'Tiene lo que es una cuenta extrajudicial.',
 'Su cuenta se encuentra en extrajudicial.',
 'Se encuentra en extrajudicial su tarjeta.',
 'Su cuenta se encuentra en el área de cobranza.',
 'Presenta una falta de pago.',
])
def test_account_legal_state_is_protected_but_office_name_is_not(phrase):
    from app.services.conversation_evidence import assess_privacy
    assert assess_privacy('Gestor: '+phrase,third_party_confirmed=True)['confirmed_disclosure']
    assert assess_privacy(phrase,third_party_confirmed=True)['review_required']
    assert not assess_privacy('Gestor: Habla del área extrajudicial de MRS.',third_party_confirmed=True)['confirmed_disclosure']


def test_existing_phone_confirmation_can_replace_repeated_dictation():
    text=('Habla MRS. Soy su hermana. ¿Le puedo dejar un número telefónico para que la señora se pueda comunicar con nosotros? '
          'Sí. Ya lo tenemos anotado aquí. Yo le paso su recado.')
    assert analyze(text).metadata['shared_classification']['aprobado']
    assert not analyze(text.replace('Ya lo tenemos anotado aquí.','No lo tenemos anotado aquí.')).metadata['shared_classification']['aprobado']


def test_explicit_recognition_of_given_callback_is_not_inventing_digits():
    from app.services.message_dialogue_evidence import existing_callback_confirmation
    text=('Habla MRS. Le dejo un número telefónico para que la señora se comunique. '
          'A ver, dígame. Es un conmutador para que se pueda comunicar. '
          '¿Es el número que usted me dio? Así es.')
    assert existing_callback_confirmation(text)
    assert not existing_callback_confirmation(text.replace('Así es.','No, no es.'))


def test_modal_return_and_already_written_phone_are_valid_reception():
    text='Habla MRS. Soy su hermana. El señor se tiene que comunicar con nosotros. Le voy a dejar un número telefónico. Ya lo tenemos anotado aquí.'
    assert analyze(text).metadata['shared_classification']['aprobado']
    negative=text.replace('El señor se tiene que comunicar','El señor no se tiene que comunicar')
    from app.services.message_dialogue_evidence import callback_modal_instruction
    assert not callback_modal_instruction(negative)
    assert not analyze(negative).metadata['shared_classification']['aprobado']


def test_message_direction_and_acceptance_may_be_in_separate_turns():
    text=('Habla MRS. ¿Le puedo dejar un recado con usted? Mi nombre es Ana. '
          '¿Tiene dónde escribir? Claro, la escucho. El número telefónico es 5551234567. '
          'Que se comunique con nosotros.')
    assert analyze(text,'MENSAJE CON TERCERO').metadata['shared_classification']['aprobado']
    assert not analyze(text.replace('Claro, la escucho.',''),'MENSAJE CON TERCERO').metadata['shared_classification']['aprobado']
    assert not analyze(text.replace('El número telefónico es 5551234567.',''),'MENSAJE CON TERCERO').metadata['shared_classification']['aprobado']
    assert not analyze(text.replace('¿Le puedo dejar','Dijo que le puedo dejar'),'MENSAJE CON TERCERO').metadata['shared_classification']['aprobado']


def test_return_instruction_without_a_delivered_contact_never_approves():
    text=('Habla MRS. No se encuentra. Le puedo dejar un mensaje con usted. Yo le paso su recado. '
          'Dígale al señor que se debe de comunicar al siguiente número. Sí, yo le digo. Gracias.')
    r=analyze(text,'MENSAJE CON TERCERO').metadata
    assert not r['shared_classification']['aprobado']
    assert r['message_delivery_validation']['review_required']


def test_bare_no_to_positive_message_offer_is_an_explicit_refusal():
    text='Habla MRS. Soy su hermana. ¿Le puedo dejar un recado con usted? No, gracias. Nos comunicamos después.'
    assert analyze(text).metadata['shared_classification']['clasificacion']=='NO_APROBADO'
    assert analyze(text.replace('? No, gracias.','? Gestor: No, gracias.')).metadata['shared_classification']['clasificacion']!='NO_APROBADO'
    assert analyze(text.replace('¿Le puedo','¿No le puedo')).metadata['shared_classification']['clasificacion']!='NO_APROBADO'


@pytest.mark.parametrize('ending',[
 'Que se comunique al número. Es 555123.',
 'Que se comunique al número. Son 1500 pesos.',
 'Que se comunique al número. Dice que el número es 5551234567.',
 '¿Tendrá dónde anotar el número? Me comunico con ella más tarde.',
])
def test_explicit_return_number_must_be_delivered_not_promised(ending):
    text='Habla MRS. Soy su hermana. Le puedo dejar información con usted. Sí. '+ending
    assert not analyze(text).metadata['shared_classification']['aprobado']


def test_corrected_phone_dictation_can_follow_interruption():
    from app.services.message_contact_evidence import callback_dictation_fragments
    text=('El número telefónico es cincuenta y cinco veinticuatro. ¿Cuál perdón? '
          'Cincuenta y cinco veinticuatro cincuenta y dos veinticiete treinta y siete.')
    assert callback_dictation_fragments(text)
    assert not unfinished_callback_offer('Le voy a dejar un número telefónico. '+text)['review_required']


def test_holder_unable_to_note_whatsapp_is_not_third_party_refusal():
    text=('Habla MRS. ¿Me comunico con Ana García? Sí. Mi tarjeta la voy a pagar mañana. '
          'Le voy a dejar un número de WhatsApp para su comprobante. No tengo dónde anotar.')
    a=analyze(text,'CONVENIO')
    assert a.metadata['quality_contact_type']=='TITULAR'
    assert not a.metadata['explicit_message_refusal']['confirmed']


def test_malformed_debt_word_is_uncertainty_not_financial_clearance():
    from app.services.conversation_evidence import assess_privacy
    v=assess_privacy('Gestor: La llamada es referente a la deudo que presenta con su tarjeta.',third_party_confirmed=True)
    assert v['review_required'] and not v['confirmed_disclosure']



def test_repeated_partial_number_at_cutoff_is_not_complete_contact():
    from app.services.message_contact_evidence import callback_dictation_fragments
    text=('Habla MRS. Soy su hermana. Le dejo un recado. Dígale que se tiene que comunicar. '
          '¿Tiene dónde tomar nota? A ver, dígame. ¿222? 222. ¿Ya? ¿222? 222. ¿500?')
    assert not callback_dictation_fragments(text)
    assert unfinished_callback_offer(text)['review_required']
    assert not analyze(text).metadata['shared_classification']['aprobado']



def test_truncated_monthly_arrears_word_remains_uncertain():
    from app.services.conversation_evidence import assess_privacy
    p=assess_privacy('Gestor: Tiene solidades vencidas.',third_party_confirmed=True)
    assert p['review_required']and not p['confirmed_disclosure']
    assert not analyze('Habla MRS. Soy su hermana. Le paso el recado. Tiene solidades vencidas.').metadata['shared_classification']['aprobado']
