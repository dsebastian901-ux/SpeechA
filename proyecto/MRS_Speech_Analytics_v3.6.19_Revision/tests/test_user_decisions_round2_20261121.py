"""Casos definidos en monitoreo: segunda ronda 21/nov/2026.

No hay datos reales ni voces ficticiamente atribuidas; los ejemplos se usan
para verificar decisiones del motor, no para validar transcripción acústica.
"""
import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import payment_commitment
from app.services.operational_outcome_resolution import (
    amount_confirmed_for_agreement, offered_payment_alternatives,
    prior_agreement_breached, recipient_has_contact)
from app.services.definitive_rejection import definitive_rejection

RELATION={
    'numero_de_tarjeta':'1234567890123456',
    'nombre_final':'1234567890123456_1PV_352_TH_PERSONA_MRS_20261121',
    'estatus_grabacion':'NO DEFINE FECHA DE PAGO',
    'asignacion':'1PV','fecha':'2026-11-21','vencimiento':'2026-11-30',
    'pago_minimo':'1000','saldo_total':'3000','corte':'23',
}


def analyze(text,status='NO DEFINE FECHA DE PAGO'):
    relation=dict(RELATION,estatus_grabacion=status)
    return A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo':'ejemplo.ogg','texto':text,'duracion_segundos':92}),relation)


def test_recado_refusal_is_valid_management_not_automatic_agent_rejection():
    text=('Gestor: Habla MRS. ¿Me permite dejarle un recado? '
          'Tercero: Soy su hermana. No quiero recibir ningún recado. '
          'Gestor: Entiendo, gracias por atender.')
    analysis=analyze(text,'SE NIEGAN A TOMAR RECADO')
    status=analysis.metadata['status_validation']
    assert status['detected_status']=='SE NIEGAN A TOMAR RECADO'
    assert status['matches'] is True
    assert status['valid'] is True
    assert analysis.metadata['explicit_message_refusal']['confirmed']
    assert definitive_rejection({'quality_contact_type':'TERCERO',
        'explicit_message_refusal':{'confirmed':True,'reason':'Rechaza recibir el recado.'}},[],92) is None
    assert not analysis.metadata['message_delivery_validation']['review_required']


@pytest.mark.parametrize('text,expected',[
    ('Gestor: Habla MRS. Titular: Soy yo. Voy a colgar.', 'TITULAR CUELGA'),
    ('Gestor: Habla MRS. Titular: Soy yo. Gestor: Puede pagar 1000 pesos mañana. '
     'Titular: Voy a colgar.', 'NO DEFINE FECHA DE PAGO'),
    ('Gestor: Habla MRS. Titular: Soy yo. Titular: No voy a pagar. Voy a colgar.',
     'NEGATIVA DE PAGO'),
])
def test_titular_hangup_ordering(text,expected):
    a=analyze(text,'TITULAR CUELGA')
    assert a.metadata['status_validation']['detected_status']==expected
    if expected=='TITULAR CUELGA':
        assert 'PEN_SIN_INTENTO_NEGOCIACION' not in {p['id'] for p in a.metadata['penalties']}


def test_alternatives_are_extracted_before_holder_hangup_only():
    text=('Gestor: Habla MRS. Titular: Soy yo. Voy a colgar. '
          'Gestor: Le puedo ofrecer realizar un pago de 1000 pesos mañana.')
    assert not offered_payment_alternatives(text,before_hangup=True)['confirmed']
    assert offered_payment_alternatives(text)['confirmed']


@pytest.mark.parametrize('text,expected',[
    ('Gestor: Habla MRS. Titular: Soy yo. No cumplí con el convenio anterior. '
     'Gestor: Entiendo, gracias.', 'CONVENIO INCUMPLIDO'),
    ('Gestor: Habla MRS. Titular: Soy yo. No cumplí con el convenio anterior. '
     'Gestor: Podemos ofrecer un acuerdo de pago. Titular: Lo voy a revisar.',
     'NO DEFINE FECHA DE PAGO'),
])
def test_previous_agreement_breach_and_followup_options(text,expected):
    assert prior_agreement_breached(text)
    a=analyze(text,'CONVENIO INCUMPLIDO')
    assert a.metadata['status_validation']['detected_status']==expected


def test_known_callback_does_not_require_redictating_number():
    text=('Gestor: Habla MRS. ¿Le puedo dejar un recado para su hermana? '
          'Tercero: Soy su hermana. Sí, dígame. '
          'Gestor: Dígale que se comunique conmigo. '
          'Tercero: Sí, ya tengo su número.')
    assert recipient_has_contact(text)
    a=analyze(text,'MENSAJE CON FAMILIAR')
    assert a.metadata['message_workflow_validation']['callback_available']
    assert not a.metadata['explicit_message_refusal']['confirmed']


@pytest.mark.parametrize('evidence,expected',[
    ('Me comprometo a pagar el 25 de noviembre.', False),
    ('Me comprometo a pagar 1000 pesos el 25 de noviembre.', True),
])
def test_date_is_not_a_money_amount(evidence,expected):
    commitment={'accepted':True,'declined':False,'evidence':evidence}
    assert amount_confirmed_for_agreement(evidence,[],commitment)==expected


@pytest.mark.parametrize('text,status',[
    ('Gestor: Habla MRS. Titular: Soy yo. Titular: Me comprometo a pagar el 25 de noviembre.',
     'NO DEFINE FECHA DE PAGO'),
    ('Gestor: Habla MRS. Titular: Soy yo. Titular: Me comprometo a pagar 1000 pesos el 25 de noviembre.',
     'CONVENIO'),
])
def test_agreement_requires_amount_and_date(text,status):
    a=analyze(text,'CONVENIO')
    assert a.metadata['status_validation']['detected_status']==status
    if status=='NO DEFINE FECHA DE PAGO':
        assert not a.metadata['negotiation_validation']['is_negotiation']
