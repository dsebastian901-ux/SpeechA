"""Aceptar información más teléfono de retorno no equivale a un sí aislado."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import assess_recado
from app.services.payment_reference_validation import callback_numbers

PREFIX = 'Habla MRS. Soy su prima. '
OFFER = 'Le puedo dejar una información con usted. Sí. '
CONTACT = ('Es para que se comunique al número de contacto. '
           'Es cincuenta y cinco cincuenta y uno veintitrés cuarenta y cinco sesenta y siete.')


def analyze(text, status='MENSAJE CON FAMILIAR', **extra):
    data={'archivo':'sample.ogg','texto':text,'duracion_segundos':120,'segmentos':[]}
    return A.analyze_transcription(TranscriptionModel.from_dict(data),
        {'estatus_grabacion':status,'numero_de_tarjeta':'1234567890123456','asignacion':'1PV',**extra})


@pytest.mark.parametrize('phone', [
    '5551234567', '55, 51, 23, 45, 67',
    'cincuenta y cinco cincuenta y uno veintitrés cuarenta y cinco sesenta y siete',
    'cincuenta y cinco. Sí. Cincuenta y uno. Ajá. Veintitrés. Sí. Cuarenta y cinco. Sí. Sesenta y siete.',
])
def test_explicit_information_acceptance_followed_by_complete_callback_proves_delivery(phone):
    a=analyze(PREFIX+OFFER+'Se puede comunicar al número de contacto. Es '+phone+'.')
    recado=a.metadata['status_validation']['recado_evidence']
    assert a.metadata['final_result']=='APROBADO'
    assert recado['recipient_acceptance_evidence'] and recado['message_transmitted'] and recado['confirmed_recado']
    evidence=recado['evidence']['acceptance'][0]
    assert evidence['method']=='ACEPTA_INFORMACION_Y_RECIBE_CONTACTO'
    assert evidence['callback_evidence']['digits']=='5551234567'
    assert not a.metadata['negotiation_validation']['commitment_confirmed']


@pytest.mark.parametrize('text', [
    OFFER,
    OFFER+'Es 5551234567.',
    OFFER+'Que se comunique al número. Es 555123.',
    OFFER+'Que se comunique al número. Es 1234567890123456.',
    OFFER+'Que se comunique al número de tarjeta 1234567890123456.',
    OFFER+'Que se comunique al número. Son 1500 pesos.',
    'Le puedo dejar una información con usted. '+CONTACT,
    'Gracias por recibir la información. '+CONTACT,
    'No le puedo dejar una información con usted. Sí. '+CONTACT,
    'Dice que le puedo dejar una información con usted. Sí. '+CONTACT,
    'Le puedo dejar una información con usted. ¿Sí? '+CONTACT,
    'Le puedo dejar una información con usted. Sí, si tengo tiempo. '+CONTACT,
    'Le puedo dejar una información con usted. Sí. Pero no quiero. '+CONTACT,
    'Le puedo dejar una información con usted. Gestor: Sí. '+CONTACT,
    OFFER+'No le voy a dar un número de contacto. Es 5551234567.',
    OFFER+'Dice que le dejo un número de contacto. Es 5551234567.',
    OFFER+'Por ejemplo el número de contacto es 5551234567.',
    OFFER+'El número es para que no se comunique. Es 5551234567.',
])
def test_missing_unrelated_incomplete_hypothetical_quoted_or_agent_answer_cannot_approve(text):
    result=assess_recado(text)
    assert not any(e.get('method')=='ACEPTA_INFORMACION_Y_RECIBE_CONTACTO' for e in result['acceptance'])
    assert not analyze(PREFIX+text).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('problem', [
    'No le voy a pasar el recado.', 'Me trataron mal.', 'La tarjeta termina en 9999.',
    'Gestor: Tiene una deuda de 500 pesos.', 'Gestor: Vamos a realizar una visita a su domicilio.',
])
def test_information_reception_does_not_override_independent_safety_checks(problem):
    a=analyze(PREFIX+OFFER+CONTACT+' '+problem)
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('status', ['MENSAJE CON FAMILIAR','RECADO REF1','RECADO REF2'])
def test_information_callback_acceptance_works_for_recado_aliases(status):
    assert analyze(PREFIX+OFFER+CONTACT,status).metadata['final_result']=='APROBADO'


def test_information_reception_does_not_create_family_from_excel_label():
    assert not analyze('Habla MRS. '+OFFER+CONTACT).metadata['shared_classification']['aprobado']


def test_contact_number_given_by_known_recipient_does_not_prove_agent_delivered_message():
    offer=OFFER.strip();contact=CONTACT
    text=PREFIX+offer+' '+contact
    segments=[{'text':PREFIX.strip(),'speaker_role':'TERCERO'},
              {'text':offer,'speaker_role':'NO DETERMINADO'},
              {'text':contact,'speaker_role':'TERCERO'}]
    result=assess_recado(text,segments)
    assert not any(e.get('method')=='ACEPTA_INFORMACION_Y_RECIBE_CONTACTO' for e in result['acceptance'])


def test_phone_parser_does_not_reinterpret_card_or_amount_as_callback():
    assert not callback_numbers('Que se comunique al número de tarjeta 1234567890123456.')
    assert not callback_numbers('Que se comunique al número. Son 5551234567 pesos.')
    assert not callback_numbers('Que se comunique al número. Es 555123.')
