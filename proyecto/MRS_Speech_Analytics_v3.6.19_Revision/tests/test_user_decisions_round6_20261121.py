"""Reglas 85, 89 y 141; confirmación 142.

Pruebas sintéticas, sin transcripciones reales y sin afirmar verificación
acústica. Deben ejecutarse antes de fusionar el PR.
"""
import pytest
from app.services.quality_decision import evaluate_quality
from app.services.analytics_service import AnalyticsService
from app.models.transcriptions import TranscriptionModel
from app.services.operational_outcome_resolution import family_payment_without_own_name


def _analyze(text,status='MENSAJE CON FAMILIAR'):
    return AnalyticsService.analyze_transcription(
        TranscriptionModel.from_dict({
            'archivo':'audio_sintetico.ogg','texto':text,
            'duracion_segundos':78,
        }),
        {'numero_de_tarjeta':'1234567890123456',
         'nombre_final':'1234567890123456_1PV_352_3EROS_PERSONA_MRS_20261121',
         'estatus_grabacion':status,
         'asignacion':'1PV','fecha':'2026-11-21',
         'vencimiento':'2026-11-30','pago_minimo':'1000',
         'saldo_total':'3000','corte':'23'})


def test_family_agrees_to_take_responsibility_without_name_10_points():
    text=('Gestor: Habla MRS. Tercero: Soy su hermana. '
          'Tercero: Yo me hago responsable del pago.')
    a=_analyze(text)
    penalties=[p for p in a.metadata['penalties']
               if p['id']=='PEN_FAMILIAR_PAGADOR_SIN_NOMBRE']
    assert len(penalties)==1
    assert penalties[0]['points']==10
    assert a.metadata['family_payer_name_validation']['confirmed']


def test_naming_family_payer_avoids_penalty():
    text=('Gestor: Habla MRS. Tercero: Soy su hermana, mi nombre es Carmen Martínez. '
          'Tercero: Yo me hago responsable del pago.')
    a=_analyze(text)
    assert not any(p['id']=='PEN_FAMILIAR_PAGADOR_SIN_NOMBRE'
                   for p in a.metadata['penalties'])


def test_no_voice_is_not_agent_failure_and_uses_separate_folder():
    a=_analyze('',status='NO CONTESTA')
    decision=a.metadata['shared_classification']
    assert decision['clasificacion']=='SIN_VOZ'
    assert decision['quality_not_applicable']
    assert not decision['aprobado']
    assert a.metadata['penalties']==[]
    assert a.metadata['no_voice_validation']['candidate']
    assert a.metadata['no_voice_validation']['requires_audio_confirmation']


def test_blank_asr_does_not_prove_silence_if_segments_contain_speech():
    a=_analyze('Gestor: Habla MRS. Titular: Soy yo.',status='NO DEFINE FECHA DE PAGO')
    assert not a.metadata['no_voice_validation']['candidate']
    assert a.metadata['shared_classification']['clasificacion']!='SIN_VOZ'


def test_current_agent_mistreatment_accusation_unproven_is_approved_with_alert():
    report={
        'quality_contact_type':'TITULAR',
        'treatment_validation':{
            'current_agent_mistreatment_unverified':True,
            'mistreatment_report_evidence':[
                {'text':'me esta hablando muy fuerte',
                 'phrase':'me esta hablando muy fuerte',
                 'speaker_role':'TITULAR'}]},
        'quality_checks':{'queja_maltrato_detectada':['me esta hablando muy fuerte']},
        'penalties':[{'id':'PEN_QUEJA_MALTRATO','category':'Trato',
                      'points':0,'invalidates':False}],
    }
    result=evaluate_quality(report,95,duration_seconds=90)
    assert result['clasificacion']=='APROBADO_CON_ALERTA'
    assert result['aprobado']
    assert any(f['code']=='MISTREATMENT_REPORT'
               and f['severity']=='ALERTA_INFORMATIVA'
               for f in result['decision_findings'])


def test_unverified_accusation_does_not_overrule_confirmed_critical_failure():
    report={
        'treatment_validation':{
            'current_agent_mistreatment_unverified':True,
            'mistreatment_report_evidence':[
                {'text':'me esta hablando muy fuerte',
                 'phrase':'me esta hablando muy fuerte','speaker_role':'TITULAR'}]},
        'privacy_validation':{
            'confirmed_disclosure':True,'reason':'Divulgación a tercero corroborada'},
    }
    result=evaluate_quality(report,95,duration_seconds=90)
    assert result['clasificacion']=='FALLA_GRAVE'
    assert not result['aprobado']



def test_132_company_name_is_allowed_to_third_party_without_financial_disclosure():
    from app.services.conversation_evidence import assess_privacy
    text=('Tercero: ¿Qué empresa está llamando? '
          'Gestor: Soy de MRS Consultores. '
          'Tercero: Gracias.')
    result=assess_privacy(text, third_party_confirmed=True)
    assert result['confirmed_disclosure'] is False
    assert result['review_required'] is False


def test_132_company_name_does_not_exempt_financial_disclosure():
    from app.services.conversation_evidence import assess_privacy
    text=('Tercero: ¿Qué empresa está llamando? '
          'Gestor: Soy de MRS Consultores. Su familiar debe 2000 pesos.')
    result=assess_privacy(text, third_party_confirmed=True)
    assert result['confirmed_disclosure'] is True or result['review_required'] is True
