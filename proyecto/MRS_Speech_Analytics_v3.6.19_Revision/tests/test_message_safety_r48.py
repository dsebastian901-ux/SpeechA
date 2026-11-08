"""Seguridad de recados, identificación y quejas; conversaciones sintéticas."""
import pytest
from app.services.conversation_evidence import holder_confirmation,assess_privacy,assess_recado
from app.services.message_contact_evidence import unfinished_callback_offer,directed_relay_message
from app.services.treatment_evidence import mistreatment_reports,offensive_asr_variants

@pytest.mark.parametrize('phrase',[
 'Presenta un incumplimiento de pago.',
 'Tiene una demanda de pago interpuesta por el banco.',
 'Es sobre el atraso que presenta la tarjeta.',
 'Su cuenta se canalizó al jurídico.',
 'Su tarjeta fue turnada al área de jurídico.',
 'Tiene siete mensualidades vencidas.',
 'Más de siete, de siete mensualidades vencidas.',
 'Tiene veintitrés mensualidades vencidas.',
 'Tiene más de un año que no se presenta pago alguno.',
 'Son ocho meses sin realizar pago.',
 'Tiene doce meses que no se ha recibido un abono.',
])
def test_concrete_arrears_and_collection_status_are_protected(phrase):
    explicit=assess_privacy('Tercero: Soy su hermano.\nGestor: '+phrase,third_party_confirmed=True)
    assert explicit['confirmed_disclosure'],explicit
    uncertain=assess_privacy('Soy su hermano. '+phrase,third_party_confirmed=True)
    assert uncertain['review_required'] and not uncertain['confirmed_disclosure']

@pytest.mark.parametrize('phrase',[
 'Tiene un saldo pendiente.', 'Presenta un saldo vencido.',
 'Habla el jurídico MRS.', 'Disculpe el atraso en la llamada.',
 'Hace ocho meses que no tenemos contacto para confirmar su pago.',
])
def test_generic_balance_office_name_and_lack_of_contact_are_not_arrears_disclosure(phrase):
    assert not assess_privacy('Tercero: Soy su hermano.\nGestor: '+phrase,third_party_confirmed=True)['confirmed_disclosure']

@pytest.mark.parametrize('text',[
 '¿Me comunica con Luisa Pérez? No está ya, pero dígame. Ya no se encuentra aquí actualmente en su domicilio. Estoy revisando sus estados de cuenta de ella. No tengo la cantidad completa para liquidarlo.',
 'No se encuentra aquí actualmente en su domicilio. No tengo la cantidad para pagar.',
 'Ya no se encuentra en casa. Sí. Mi tarjeta está pendiente.',
 '¿Me comunica con Luisa Pérez? No está ya, pero dígame. Yo voy a pagar la tarjeta de ella.',
])
def test_representative_or_absence_statement_cannot_be_used_as_nominal_holder_request(text):
    assert not holder_confirmation(text)['confirmed']

@pytest.mark.parametrize('text',[
 '¿Me comunica con Luisa Pérez? Sí. Mi tarjeta la pagué ayer.',
 '¿Se encuentra Luisa Pérez? Sí. Yo ya pagué mi tarjeta.',
 '¿Se encuentra Luisa Pérez? Ella habla.',
])
def test_valid_nominal_context_still_identifies_holder(text):
    assert holder_confirmation(text)['confirmed']

@pytest.mark.parametrize('offer',[
 'Le dictaría un número.', 'Sería dejarle un número telefónico.',
 'Le dejaría un número.', 'Le proporciono un número.',
 'Le puedo dejar un número. Se lo voy dictando.',
])
def test_offer_with_only_partial_phone_stays_pending(offer):
    text='Soy su hermana. '+offer+' Sí. Es cincuenta y cinco. Dígale que se comunique.'
    assert unfinished_callback_offer(text)['review_required']


def test_past_number_unavailable_is_not_current_callback_delivery():
    text='Me pasaron un número, pero no lo tengo aquí; lo tengo en la casa. Le puedo dejar un número. Se lo voy dictando.'
    assert unfinished_callback_offer(text)['review_required']


def test_explicit_existing_number_is_available():
    assert not unfinished_callback_offer('Ya lo tengo anotado. Le voy a dejar un número telefónico.')['review_required']


def test_negative_return_directive_is_not_positive_message_even_with_complete_phone():
    text='Soy su hermana. El número telefónico es 5551234567. Dígale que no se comunique con nosotros.'
    assert not directed_relay_message(text)
    assert unfinished_callback_offer(text)['review_required']


def test_alternative_positive_callback_after_old_number_prohibition_is_allowed():
    text='No llame al anterior. Dígale que se comunique al nuevo número telefónico 5551234567.'
    assert not unfinished_callback_offer(text)['review_required']

@pytest.mark.parametrize('return_phrase',['se contacte','se ponga en contacto','se comunique'])
def test_equivalent_callback_verbs_are_supported(return_phrase):
    text='Le puedo dejar un número telefónico. ¿Tiene dónde anotar? Sí. Es 5551234567. Dígale que '+return_phrase+' con nosotros.'
    assert directed_relay_message(text)
    assert assess_recado(text)['acceptance']
    assert not unfinished_callback_offer(text)['review_required']


def test_family_answer_to_family_question():
    assert assess_recado('¿Es familiar del señor Pérez? Primo.')['family']
    assert not assess_recado('¿Es familiar del señor Pérez? Gestor: Primo.')['family']

@pytest.mark.parametrize('text',[
 'La tarjeta nunca me dijeron que tenía costo.',
 'Nunca me informaron que la tarjeta tenía comisión.',
 'No me explicaron la anualidad de esa tarjeta.',
])
def test_undisclosed_card_cost_complaint_blocks(text):
    assert mistreatment_reports(text,[],[])
    assert not mistreatment_reports('Gestor: '+text,[],[])
    assert not mistreatment_reports('No es cierto que '+text.lower(),[],[])


def test_coarse_word_is_not_confused_with_cargando():
    assert offensive_asr_variants('Está cagando.')
    assert not offensive_asr_variants('Está cargando la aplicación.')

@pytest.mark.parametrize('reply',['Dígame el recado, por favor.','Páseme la razón.','Páseme el mensaje.'])
def test_explicit_request_to_receive_message_is_acceptance(reply):
    assert assess_recado(reply)['acceptance']
    assert not assess_recado('No '+reply.lower())['acceptance']
    assert not assess_recado('Diga que '+reply.lower())['acceptance']
    assert not assess_recado('Gestor: '+reply)['acceptance']


def test_a_ver_requires_note_question_and_actual_callback():
    text='Soy su hermana. ¿Puede tomar nota? A ver. El número telefónico es 5551234567. Dígale que se comunique.'
    assert assess_recado(text)['acceptance']
    assert not assess_recado(text.replace(' A ver.',' Gestor: A ver.'))['acceptance']
    assert not assess_recado('A ver. Dígale que se comunique.')['acceptance']


def test_actual_phone_after_a_schedule_is_not_hidden_by_earlier_time_numbers():
    text='Soy su hermano. Le puedo dejar el número para que se comunique. Es de lunes a sábado de ocho de la mañana a ocho de la noche. ¿Ya tiene dónde anotar? Voy a capturar. Ok, es el 222, 555, 1350 para que se comunique con nosotros.'
    assert not unfinished_callback_offer(text)['review_required']


def test_contradictory_denial_then_confirmed_spouse_requires_review_not_arco_failure():
    from app.services.analytics_service import AnalyticsService as A
    from app.models.transcriptions import TranscriptionModel
    text=('Habla MRS. ¿Le conoce? No. ¿Es usted su esposo, no? Sí. '
          '¿Le puedo dejar un recado? Sí. El número telefónico es 5551234567. Dígale que se comunique.')
    a=A.analyze_transcription(TranscriptionModel.from_dict(dict(archivo='sample.ogg',texto=text,duracion_segundos=150)),{'estatus_grabacion':'MENSAJE CON FAMILIAR'})
    assert a.metadata['contact_conflict_validation']['review_required']
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'
    assert not any(p['id']=='PEN_ARCO_OMISION'for p in a.metadata['penalties'])
    assert not a.metadata['arco_validation']['applies']


def test_confirmed_spouse_without_denial_still_receives_valid_message():
    from app.services.analytics_service import AnalyticsService as A
    from app.models.transcriptions import TranscriptionModel
    text=('Habla MRS. ¿Es usted su esposo, no? Sí. ¿Le puedo dejar un recado? Sí. '
          'El número telefónico es 5551234567. Dígale que se comunique.')
    a=A.analyze_transcription(TranscriptionModel.from_dict(dict(archivo='sample.ogg',texto=text,duracion_segundos=150)),{'estatus_grabacion':'MENSAJE CON FAMILIAR'})
    assert not a.metadata['contact_conflict_validation']['review_required']
    assert a.metadata['shared_classification']['aprobado']

@pytest.mark.parametrize('phrase',[
 'Tiene un saldo tal por la cantidad de 10330 pesos.',
 'El pago que se está requiriendo para que se ponga al corriente sería por la cantidad de 6200 pesos.',
 'Para liquidar es por la cantidad de 941 pesos.',
 'Para regularizar sería por 1250 pesos.',
 'La señora no ha realizado ningún pago en tres meses.',
 'Que se comunique para detener la demanda de tipo mercantil.',
])
def test_linking_words_do_not_hide_financial_amounts_or_arrears(phrase):
    assert assess_privacy('Tercero: Soy su hermano.\nGestor: '+phrase,third_party_confirmed=True)['confirmed_disclosure']
    uncertain=assess_privacy(phrase,third_party_confirmed=True)
    assert uncertain['review_required'] and not uncertain['confirmed_disclosure']
    received=assess_privacy('Tercero: '+phrase,third_party_confirmed=True)
    assert not received['review_required'] and not received['confirmed_disclosure']


def test_phonetic_arrears_variant_is_review_not_confirmed_disclosure():
    v=assess_privacy('Gestor: Es por la trazo de su tarjeta.',third_party_confirmed=True)
    assert v['review_required'] and not v['confirmed_disclosure']
    assert not assess_privacy('Gestor: Trazó su firma en la tarjeta.',third_party_confirmed=True)['review_required']
