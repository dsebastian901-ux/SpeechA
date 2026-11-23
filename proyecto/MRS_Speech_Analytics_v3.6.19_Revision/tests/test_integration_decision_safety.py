"""Casos sintéticos: prioridades independientes de Whisper y de la aprobación."""
import pytest
from app.services.quality_decision import evaluate_quality
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel


@pytest.mark.parametrize('key,value',[
 ('privacy_validation',{'confirmed_disclosure':True}),
 ('critical_failures',[{'id':'PEN003','invalidates':True,'reason':'Hecho confirmado.'}]),
 ('penalties',[{'id':'PEN004','invalidates':True,'points':100,'reason':'Hecho confirmado.'}]),
])
def test_no_voice_candidate_cannot_erase_independent_confirmed_critical_evidence(key,value):
    metadata={'no_voice_validation':{'candidate':True},key:value}
    assert evaluate_quality(metadata,90,duration_seconds=90)['clasificacion']=='FALLA_GRAVE'


def test_positive_duration_empty_asr_reaches_no_voice_without_agent_penalties():
    result=A.analyze_transcription(TranscriptionModel('synthetic.wav','synthetic.wav','',duration_seconds=90),{})
    assert result.metadata['shared_classification']['clasificacion']=='SIN_VOZ'
    assert not result.metadata['penalties']
    assert result.metadata['no_voice_validation']['requires_audio_confirmation']


def test_text_lost_but_recognized_segments_is_a_technical_inconsistency_not_no_voice():
    with pytest.raises(ValueError):
        A.analyze_transcription(TranscriptionModel('synthetic.wav','synthetic.wav','',duration_seconds=90,
                             segments=[{'texto':'Sí hay conversación.','inicio':0,'fin':3}]),{})


@pytest.mark.parametrize('offer',['Le dejo el número de contacto.','El teléfono es 55512345.','Le voy a dictar el número telefónico.'])
def test_offered_but_unverified_callback_is_not_credited_as_an_ordinary_omission(offer):
    text=('Gestor: Habla MRS. ¿Le puedo dejar un recado? Tercero: Soy su hermana. Sí, dígame. '
          'Gestor: Dígale que se comunique con nosotros. '+offer+' Tercero: Sí, le paso el recado.')
    result=A.calculate_basic_compliance(text,{'estatus_grabacion':'MENSAJE CON FAMILIAR'})
    assert not result['message_workflow_validation']['recado_sin_contacto_confirmado']
    assert result['message_delivery_validation']['review_required']
    assert result['final_result']=='REVISAR'


def test_explicit_receipt_keeps_receipt_status_when_recipient_cannot_deliver_later():
    text=('Gestor: Habla MRS. Tercero: Soy su hermana. Gestor: Dígale que se comunique con MRS. '
          'Tercero: Sí, recibí el recado, pero no tengo forma de contactarla.')
    result=A.calculate_basic_compliance(text,{'estatus_grabacion':'MENSAJE CON FAMILIAR'})
    assert result['status_validation']['detected_status']=='MENSAJE CON FAMILIAR'
    assert result['message_workflow_validation']['recado_aceptado_sin_poder_transmitir']


@pytest.mark.parametrize('line',['Gestor: Ya recibí el recado.','Tercero: No recibí el recado.',
                               'Tercero: ¿Recibí el recado?','Tercero: Me dijo que recibí el recado.'])
def test_explicit_receipt_does_not_invent_recipient_acceptance(line):
    from app.services.message_contact_evidence import message_contact_evidence
    assert not message_contact_evidence(line)['acceptance']


def test_missing_terms_of_agent_declared_agreement_keep_existing_deductions():
    result=A.calculate_basic_compliance('Gestor: Habla MRS. Titular: Soy yo. Gestor: Confirmo su convenio.',
                                       {'estatus_grabacion':'CONVENIO'})
    penalties={p['id']:p['points']for p in result['penalties']}
    assert penalties['PEN007']==20
    assert penalties['PEN008']==20
    assert penalties['PEN_CONV_LUGARES']==20
    assert result['status_validation']['detected_status']!='CONVENIO'


def test_excel_agreement_alone_does_not_create_a_new_agreement_script():
    result=A.calculate_basic_compliance('Gestor: Habla MRS. Titular: Soy yo.',{'estatus_grabacion':'CONVENIO'})
    assert 'PEN_CONV_LUGARES'not in {p['id']for p in result['penalties']}
    assert result['final_result']!='APROBADO'
