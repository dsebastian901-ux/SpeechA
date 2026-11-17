"""Identificar al receptor del recado no lo convierte en titular de la cuenta."""
import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.contact_dialogue_resolution import declared_intermediary


BODY=('Le puede mencionar que se comunique con nosotros a la brevedad. '
      'Habla Ana de Jurídico MRS. ¿Tiene con qué anotar un teléfono? '
      'Sí, dígame. El número de contacto es 55 12 34 56 78. '
      'Tengo el gusto con Persona Receptora, ¿correcto? Sí, correcto.')


@pytest.mark.parametrize('opening',[
    '¿Tiene contacto con él para poderle dejar un recado? Sí, no lo he visto, pero le aviso. ',
    '¿Pero sí conoce a Persona Buscada para dejar un recado? Sí, dígame. ',
    'Pero sí, conoce a Persona Buscada para dejar un recado. Sí, dígame. ',
    'No se encuentra. ',
])
def test_contact_for_a_message_remains_third_party_after_confirming_recipient_name(opening):
    text='Habla MRS. '+opening+BODY
    assert declared_intermediary(text)['confirmed']
    m=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'ejemplo.ogg',
        'texto':text,'duracion_segundos':120,'segmentos':[]}),{}).metadata
    assert m['quality_contact_type']=='TERCERO'
    assert 'PEN_SIN_INTENTO_NEGOCIACION' not in {p['id']for p in m['penalties']}


@pytest.mark.parametrize('text',[
    '¿Tiene contacto con él para poderle dejar un recado? No. ',
    'No conoce a Persona Buscada para dejar un recado. Sí. ',
    'Gestor: Sí, dígame. Tengo contacto con él. ',
    'El cliente dijo que le puede mencionar que se comunique con nosotros. ',
    '¿Me puede comunicar con Persona? Sí. Mi tarjeta está al corriente. ',
    '¿Me puede comunicar con Persona? Sí, soy yo. Ya hice el pago. '
      '¿Le puede mencionar a su hermana que me llame? ',
])
def test_questions_reports_and_own_account_context_do_not_invent_an_intermediary(text):
    assert not declared_intermediary(text)['confirmed']


def test_a_named_message_recipient_does_not_waive_financial_privacy():
    text=('Habla MRS. ¿Tiene contacto con él para dejarle un recado? Sí. '+BODY+
          '\nGestor: El titular tiene un saldo vencido de 1500 pesos.')
    m=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'ejemplo.ogg',
        'texto':text,'duracion_segundos':120,'segmentos':[]}),{}).metadata
    assert m['privacy_validation']['confirmed_disclosure']
    assert m['shared_classification']['clasificacion']=='FALLA_GRAVE'


@pytest.mark.parametrize('answer',['Sí, es su hermano.','Soy su hermano.','Su hermana.'])
def test_a_family_answer_remains_family_after_the_recipient_gives_own_name(answer):
    text=('Habla MRS. ¿Es familiar de él? '+answer+' '+BODY)
    m=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'ejemplo.ogg',
        'texto':text,'duracion_segundos':120,'segmentos':[]}),{}).metadata
    assert m['quality_contact_type']=='TERCERO / FAMILIAR'
    assert 'PEN_SIN_INTENTO_NEGOCIACION' not in {p['id']for p in m['penalties']}


@pytest.mark.parametrize('answer,received',[('Sí, dígame.',True),('Sí.',False)])
def test_knowing_the_target_and_asking_to_hear_the_message_are_separate(answer,received):
    text=('Habla MRS. ¿Tiene contacto con él para dejarle un recado? '+answer+
        ' Le puede mencionar que se comunique con nosotros al número de contacto 55 12 34 56 78.')
    m=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'ejemplo.ogg',
        'texto':text,'duracion_segundos':120,'segmentos':[]}),{}).metadata
    assert m['message_workflow_validation']['recipient_accepted'] is received
    assert m['message_workflow_validation']['complete'] is received
