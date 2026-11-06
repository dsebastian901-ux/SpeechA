"""Solicitar dictado del teléfono no equivale a aceptar una propuesta de pago."""
import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import assess_recado


def analyze(tail,**context):
    t=TranscriptionModel('sample.ogg','sample.ogg','Habla MRS. Es mi marido, ¿por qué? '+tail,
                         duration_seconds=120)
    return A.analyze_transcription(t,{'estatus_grabacion':'MENSAJE CON FAMILIAR',**context})


@pytest.mark.parametrize('answer',['A ver.','A ver, dígame.','Dígame.'])
def test_request_to_dictate_after_callback_offer_confirms_reception(answer):
    a=analyze('Le voy a dejar un número para que él se comunique con nosotros. '+answer+
              ' Mire, el número es el 555, 123, 4567. Ok, gracias.')
    recado=a.metadata['status_validation']['recado_evidence']
    assert recado['confirmed_recado'] and recado['recipient_acceptance_evidence']
    assert a.metadata['final_result']=='APROBADO'
    assert any(r.get('method')=='SOLICITA_DICTADO_TRAS_OFERTA_DE_CONTACTO'
               for r in recado['evidence']['acceptance'])
    assert not a.metadata['negotiation_validation']['commitment_confirmed']


@pytest.mark.parametrize('text',[
    'A ver. Mire, el número es el 555, 123, 4567.',
    'Le voy a dejar un número. A ver. Mire, el número es el 555, 123, 4567.',
    'Le voy a dejar un número para que él se comunique. Mire, el número es el 555, 123, 4567. Gracias por recibir el mensaje.',
    'Le voy a dejar un número para que él se comunique. ¿A ver? Mire, el número es el 555, 123, 4567.',
    'No le voy a dejar un número para que él se comunique. A ver. Mire, el número es el 555, 123, 4567.',
    'Dice que le voy a dejar un número para que él se comunique. A ver. Mire, el número es el 555, 123, 4567.',
    'Le voy a dejar un número para que él se comunique. Gestor: A ver. Mire, el número es el 555, 123, 4567.',
    'Le voy a dejar un número para que él se comunique. A ver. Mire, el número es el 555, 123.',
    'Le voy a dejar un número para que él se comunique. A ver.',
    'Le voy a dejar un número para que pague 1000 pesos. A ver. Mire, el número es el 555, 123, 4567.',
])
def test_incomplete_unrelated_negated_quoted_or_agent_turn_does_not_confirm_reception(text):
    assert not assess_recado(text)['acceptance']


@pytest.mark.parametrize('problem',[
    'No le voy a pasar el recado.', 'Me trataron mal.',
    'Gestor: Tiene una deuda de 500 pesos.', 'La tarjeta termina en 9999.',
])
def test_contact_offer_does_not_waive_refusal_privacy_treatment_or_wrong_card(problem):
    a=analyze('Le voy a dejar un número para que él se comunique con nosotros. A ver. '
              'Mire, el número es el 555, 123, 4567. '+problem,
              numero_de_tarjeta='1234567890123456')
    assert not a.metadata['shared_classification']['aprobado']


def test_accepting_contact_number_does_not_invent_family_from_tu_hija():
    text=('Habla MRS. No se encuentra. ¿Qué es usted del señor Carlos? Tu hija. '
          'Le voy a dejar un número para que él se comunique. A ver. Mire, el número es el 555, 123, 4567.')
    a=A.analyze_transcription(TranscriptionModel('sample.ogg','sample.ogg',text,duration_seconds=120),
                             {'estatus_grabacion':'MENSAJE CON FAMILIAR'})
    assert not a.metadata['status_validation']['recado_evidence']['family_phrases']
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('role,accepted',[('GESTOR',False),('TITULAR',False),('TERCERO',True)])
def test_segment_role_of_the_dictation_request_is_respected(role,accepted):
    offer='Le voy a dejar un número para que él se comunique con nosotros.'
    answer='A ver.';number='Mire, el número es el 555, 123, 4567.'
    segments=[{'text':offer,'speaker_role':'GESTOR','start':0,'end':10},
              {'text':answer,'speaker_role':role,'start':10,'end':11},
              {'text':number,'speaker_role':'GESTOR','start':11,'end':15}]
    evidence=assess_recado(' '.join([offer,answer,number]),segments)
    assert bool(evidence['acceptance']) is accepted
