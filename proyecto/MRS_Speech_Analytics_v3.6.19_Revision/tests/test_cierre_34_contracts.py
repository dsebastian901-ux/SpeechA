"""Contrastes nuevos para cerrar causas; las 112 pruebas existentes no cambian."""
from copy import deepcopy
import pytest
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel
from app.services.conversation_evidence import payment_commitment
from app.services.operational_outcome_resolution import amount_confirmed_for_agreement
from app.services.current_payment_amounts import explicit_current_amounts


@pytest.mark.parametrize('reply',['Sí, de acuerdo.','Hoy lo hago.','Me comprometo a pagar hoy.'])
def test_spoken_offer_and_own_acceptance_confirm_amount_without_excel(reply):
    text='Gestor: Puede pagar 1200 pesos hoy. Titular: '+reply
    commitment=payment_commitment(text)
    assert commitment['accepted']
    assert amount_confirmed_for_agreement(text,(),commitment)
    assert {e['amount']for e in explicit_current_amounts(text)}=={1200}


@pytest.mark.parametrize('reply',['Si consigo el dinero hoy lo hago.',
    'Me dijo que hoy lo hago.','No puedo pagar hoy.','El ticket lo mando hoy.'])
def test_conditions_quotes_refusal_and_receipt_do_not_accept_a_payment_offer(reply):
    text='Gestor: Puede pagar 1200 pesos hoy. Titular: '+reply
    assert not explicit_current_amounts(text)


def test_clarification_does_not_lose_the_only_spoken_amount_or_rewrite_source():
    text=('Gestor: Habla MRS. Titular: Soy yo. Gestor: Puede pagar 1200 hoy. Gestor: De preferencia completo para que no se vaya a tomar como un pago parcial. '
          'Titular: Hoy lo hago.')
    t=TranscriptionModel('synthetic.wav','synthetic.wav',text,duration_seconds=90)
    a=A.analyze_transcription(t,{'estatus_grabacion':'CONVENIO','fecha':'2026-11-23'})
    assert a.metadata['status_validation']['detected_status']=='CONVENIO'
    assert t.text==text


@pytest.mark.parametrize('explanation',['El WhatsApp es 5551234567.','Ahora el monto es de 1500 pesos.','El día es mañana.'])
def test_other_object_or_changed_terms_do_not_inherit_old_amount(explanation):
    text='Gestor: Puede pagar 1200 pesos hoy. Gestor: '+explanation+' Titular: Hoy lo hago.'
    events=explicit_current_amounts(text)
    assert not any(e['amount']==1200 for e in events)


def test_followup_checker_uses_current_policy_without_waiving_other_controls():
    from tools.regression_checkpoints import verified_followup_approval
    a=A.analyze_transcription(TranscriptionModel('synthetic.wav','synthetic.wav',
        'Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe comprobante por WhatsApp.',duration_seconds=90),
        {'estatus_grabacion':'CONVENIO','pago_minimo':'700'})
    m=a.metadata;assert verified_followup_approval(m)
    assert m['status_validation']['policy_source']=='CRITERIO_72_USUARIO_20261121'
    assert m['status_validation']['bank_payment_verified']is False
    for field,value in [('prior_payment_covers_minimum',False),('unaccepted_new_payment_instruction',True)]:
        other=deepcopy(m);other['negotiation_validation'][field]=value
        assert not verified_followup_approval(other)
    other=deepcopy(m);other['privacy_validation']['review_required']=True
    assert not verified_followup_approval(other)


@pytest.mark.parametrize('refusal',['No se lo puedo pasar.','No puedo recibir, disculpe.'])
def test_contextual_final_refusal_is_not_a_received_message(refusal):
    text='Habla MRS. Soy su hermana. ¿Le puedo dejar un recado? Sí. '+refusal+' Que se comunique con nosotros.'
    result=A.calculate_basic_compliance(text,{'estatus_grabacion':'MENSAJE CON FAMILIAR'})
    assert result['explicit_message_refusal']['confirmed']
    assert result['status_validation']['detected_status']=='SE NIEGAN A TOMAR RECADO'
    assert not result['message_workflow_validation']['recado_sin_contacto_confirmado']


@pytest.mark.parametrize('phrase',['No puedo recibir transferencias.','No se lo puedo pasar al banco.',
                                   'Dijo que no puedo recibir.','¿No puedo recibir?'])
def test_unrelated_object_or_quote_does_not_create_a_message_refusal(phrase):
    from app.services.definitive_rejection import explicit_message_refusal
    text='Gestor: Le puedo dejar un recado. Tercero: '+phrase
    assert not explicit_message_refusal(text)['confirmed']
