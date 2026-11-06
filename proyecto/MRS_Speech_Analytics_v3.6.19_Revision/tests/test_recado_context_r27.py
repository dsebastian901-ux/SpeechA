"""Recados: aceptación contextual y rechazos que realmente hablan del mensaje."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import assess_recado, associate_relationship


def analyze(text, status='MENSAJE CON FAMILIAR', **context):
    t=TranscriptionModel('sample.ogg','sample.ogg',text,duration_seconds=120)
    return A.analyze_transcription(t,{'estatus_grabacion':status,**context})


@pytest.mark.parametrize('phrase',[
    'No puedo dar cantidades.', 'No le puedo dar información.',
    'No quiero dar cantidades.', 'No puedo transmitir datos personales.',
    'No puedo pasar la llamada.', 'No le puedo dar un descuento.',
])
def test_refusing_financial_information_or_a_transfer_is_not_refusing_the_message(phrase):
    assert not assess_recado(phrase)['refusal']


@pytest.mark.parametrize('phrase',[
    'No puedo dar el recado.', 'No quiero pasar su mensaje.',
    'No voy a transmitir el mensaje.', 'No le voy a dar el recado.',
    'No se lo puedo pasar.', 'No tengo dónde anotar.',
    'No puedo recibir, disculpe.', 'No soy su mensajero.',
])
def test_actual_message_refusals_still_block(phrase):
    text='Habla MRS. Soy su hermana. ¿Le puedo dejar un recado? Sí. '+phrase+' Que se comunique con nosotros.'
    assert assess_recado(text)['refusal']
    assert not analyze(text).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('question',[
    '¿Podré dejar un recado con usted, señor?',
    '¿Podría dejarle un mensaje?',
    '¿Con usted podríamos dejar algún tipo de recado?',
    '¿Le puedo dejar algún recado?',
    'Le puedo dejar un recado con usted.',
])
def test_explicit_acceptance_of_request_variants_is_recognized(question):
    a=analyze('Habla MRS. Soy su hermana. '+question+' Sí, claro. '
              'Le comento que se comunique al número telefónico 5551234567.')
    assert a.metadata['status_validation']['recado_evidence']['confirmed_recado']
    assert a.metadata['final_result']=='APROBADO'


@pytest.mark.parametrize('question',[
    '¿Tendrá usted dónde anotar?', '¿Tiene con qué anotar el número?',
    '¿Tiene dónde tomar nota para proporcionarle un número?',
])
def test_accepting_to_take_number_in_message_context_counts_as_reception(question):
    a=analyze('Habla MRS. Es mi mamá. Puedo dejarle un mensaje para ella. '
        'Es importante que se comunique al siguiente número telefónico. '
        +question+' Sí, a ver, espéreme. Es 5551234567. Puede comunicarse de ocho a nueve.')
    assert a.metadata['final_result']=='APROBADO'


@pytest.mark.parametrize('phrase',[
    '¿Tiene dónde anotar? Sí. Su pago es de 1000 pesos.',
    '¿Le puedo dejar un recado? ¿Sí?',
    'No puedo dejar un recado. Sí.',
    'Dice que puedo dejar un recado. Sí.',
    'Dice que le puedo dejar un recado. Sí.',
    'No le puedo dejar un recado. Sí.',
    '¿Le puedo dejar un recado? Gestor: Sí.',
    '¿Tiene dónde anotar? Gestor: Sí. Que se comunique con nosotros.',
    'Gracias por recibir el recado.',
])
def test_unrelated_question_quotation_agent_answer_or_thanks_is_not_acceptance(phrase):
    assert not assess_recado(phrase)['acceptance']


def test_acceptance_does_not_prove_a_callback_message_was_actually_given():
    a=analyze('Habla MRS. Soy su hermana. ¿Podré dejar un recado? Sí.')
    assert a.metadata['status_validation']['recado_evidence']['recipient_acceptance_evidence']
    assert not a.metadata['shared_classification']['aprobado']


def test_a_number_does_not_prove_recipient_accepted_it():
    a=analyze('Habla MRS. Soy su hermana. Le puedo dejar un mensaje. '
              'Que se comunique al número telefónico 5551234567. Gracias por recibir el recado.')
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('reply',[
    '¿Qué parentesco tiene con la titular? Mi hermana.',
    '¿Qué es usted del señor Carlos? Mi primo.',
    '¿Qué es de la señora? Mi hermana.',
    '¿Con quién tuve el gusto? Con su hermana.',
])
def test_contextual_kinship_answer_is_evidence(reply):
    assert assess_recado(reply)['family']


@pytest.mark.parametrize('phrase',[
    'Es mi marido, ¿por qué?', 'Sí, es mi mamá. ¿Hasta qué hora?',
])
def test_a_following_question_does_not_erase_an_explicit_family_statement(phrase):
    assert assess_recado(phrase)['family']


@pytest.mark.parametrize('phrase',[
    '¿Es mi hermana?', 'Gestor: Es mi hermana, ¿por qué?',
    'No es mi esposa.', '¿Qué parentesco tiene con la titular? ¿Mi hermana?',
    'Es mi hermano, ¿verdad?', 'Diga que es mi hermana.',
    '¿Qué cantidad necesita? Mi hermana.',
])
def test_question_agent_negative_or_unrelated_response_does_not_prove_kinship(phrase):
    assert not assess_recado(phrase)['family']


def test_excel_family_label_does_not_replace_missing_relationship():
    a=analyze('Habla MRS. ¿Podré dejar un recado? Sí. '
              'Que se comunique al número telefónico 5551234567.')
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('problem',[
    'Me trataron mal.', 'La tarjeta termina en 9999.',
    'Gestor: Tiene una deuda de 500 pesos.',
])
def test_contextual_recado_does_not_waive_other_quality_rules(problem):
    a=analyze('Habla MRS. Soy su hermana. ¿Podré dejar un recado? Sí. '
        'Que se comunique al número telefónico 5551234567. '+problem,
        numero_de_tarjeta='1234567890123456')
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('text',[
    '¿Es usted conocido, amigo, familiar? Conocido.',
    '¿Solo conocida? Conocida, me dejó este teléfono.',
    '¿Me puede indicar qué es usted de la señora? Una conocida.',
])
def test_direct_acquaintance_answers_are_third_parties(text):
    assert associate_relationship(text)['confirmed']
    a=analyze('Habla MRS. '+text+' ¿Podré dejar un recado? Sí. '
              'Que se comunique al número telefónico 5551234567.',status='MENSAJE CON TERCERO')
    assert a.metadata['quality_contact_type']=='TERCERO'
    assert a.metadata['final_result']=='APROBADO'


@pytest.mark.parametrize('text',[
    '¿Es usted conocido, amigo, familiar? ¿Conocido?',
    '¿Es usted conocido, amigo, familiar? Gestor: Conocido.',
    'Conocida.', '¿Es usted conocido? No.',
])
def test_isolated_question_or_agent_words_do_not_confirm_acquaintance(text):
    assert not associate_relationship(text)['confirmed']


def test_disjunctive_relationship_question_requires_an_explicit_kin_answer():
    assert assess_recado('¿Usted es familiar, conocida? Sí, su hermano.')['family']
    assert not assess_recado('¿Usted es familiar, conocida? Sí.')['family']


@pytest.mark.parametrize('reply',[
    'No, por el momento no está.', 'No, en ese momento no está.',
    'No, no llega.', 'No ha llegado.',
])
def test_absence_reply_is_third_party_evidence_without_inventing_family(reply):
    a=analyze('Habla MRS. ¿Se encuentra la señora Ana? '+reply+
              ' ¿Podré dejar un recado? Sí. Que se comunique al número telefónico 5551234567.',
              status='MENSAJE CON TERCERO')
    assert a.metadata['quality_contact_type']=='TERCERO'
    assert a.metadata['final_result']=='APROBADO'


def test_message_accepted_for_named_other_person_identifies_intermediary():
    a=analyze('Habla MRS. ¿Puedo dejarle un mensajito con usted? Sí. '
        'Solo es para que el señor Carlos se pueda comunicar al siguiente número telefónico 5551234567.',
        status='MENSAJE CON TERCERO')
    assert a.metadata['final_result']=='APROBADO'
    assert a.metadata['intermediary_contact_validation']['method']=='RECADO_ACEPTADO_PARA_OTRA_PERSONA'
    assert not a.metadata['intermediary_contact_validation']['human_verified']


@pytest.mark.parametrize('text',[
    '¿Puedo dejarle un mensajito con usted? Sí.',
    'El señor Carlos se puede comunicar al número telefónico. Gracias por recibir el mensaje.',
])
def test_partial_named_message_does_not_identify_intermediary(text):
    a=analyze('Habla MRS. '+text,status='MENSAJE CON TERCERO')
    assert not a.metadata['intermediary_contact_validation']['confirmed']
    assert not a.metadata['shared_classification']['aprobado']


def test_reported_debt_to_intermediary_stays_blocked_even_after_message_is_accepted():
    a=analyze('Habla MRS. ¿Puedo dejar un mensajito? Sí. '
        'El señor Carlos se puede comunicar al número telefónico 5551234567. Es sobre su adeudo.',
        status='MENSAJE CON TERCERO')
    assert a.metadata['privacy_validation']['review_required']
    assert not a.metadata['shared_classification']['aprobado']


def test_a_clarification_is_not_penalized_for_missing_collection_attempt():
    a=analyze('Habla MRS. Soy yo. Perdí mi tarjeta y ya levanté una aclaración con folio. '
              'Me indicaron esperar la resolución.',status='ACLARACION')
    assert 'PEN_SIN_INTENTO_NEGOCIACION' not in {p['id'] for p in a.metadata['penalties']}
    assert not a.metadata['shared_classification']['aprobado']  # No certifica todo el trámite.


def test_the_excel_clarification_label_does_not_exempt_actual_new_negotiation():
    a=analyze('Habla MRS. Soy yo. Generamos su convenio. '
              '¿Podemos contar con su pago de 1000 pesos mañana? Sí.',status='ACLARACION')
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('offer',['¿Se gusta dejarle un recado?','Si gusta dejar un mensaje.',
                                '¿Quiere dejar un recado?'])
def test_recipient_offer_to_take_message_is_acceptance(offer):
    a=analyze('Habla MRS. Soy su hermana. '+offer+
              ' Le puede indicar que nos pueda regalar una llamada. Le dejare un número de contacto 5551234567.')
    assert a.metadata['final_result']=='APROBADO'


@pytest.mark.parametrize('phrase',['Gestor: ¿Quiere dejar un recado?',
                                 'No me gusta dejar un mensaje.','Dice que quiere dejar un recado.'])
def test_agent_negative_or_reported_offer_is_not_recipient_acceptance(phrase):
    assert not assess_recado(phrase)['acceptance']


def test_readback_after_contact_number_instruction_confirms_reception():
    a=analyze('Habla MRS. Soy su hermana. Le dejaré un número telefónico. '
              'Es importante que se comunique al siguiente número. '
              '¿Me lo rectifica para ver si está correcto? 55, 51, 23, 45, 67.')
    assert a.metadata['final_result']=='APROBADO'
    assert any(u.get('method')=='REPETICION_NUMERO_CONTACTO_SOLICITADA'
               for u in a.metadata['status_validation']['recado_evidence']['evidence']['acceptance'])


@pytest.mark.parametrize('text',[
    '¿Me lo rectifica para ver si está correcto? 55, 51, 23, 45, 67.',
    'Le dejaré un mensaje. ¿Me lo rectifica para ver si está correcto? Gestor: 55, 51, 23, 45, 67.',
    'Le dejaré un mensaje. ¿Me lo rectifica para ver si está correcto? 55, 51, 23.',
])
def test_readback_without_context_role_or_complete_number_does_not_prove_reception(text):
    assert not assess_recado(text)['acceptance']


@pytest.mark.parametrize('phrase',['¿Me comenta que es su prima? Sí.',
                                 '¿Usted es su hermano? Así es.'])
def test_explicit_confirmation_of_kinship_is_not_an_unanswered_agent_question(phrase):
    assert assess_recado(phrase)['family']


@pytest.mark.parametrize('phrase',['¿Es su prima?', '¿Es su prima? Gestor: Sí.',
                                 '¿Es su prima? Sí, creo.', '¿Es su prima? ¿Sí?'])
def test_kinship_confirmation_still_requires_a_positive_recipient_answer(phrase):
    assert not assess_recado(phrase)['family']
