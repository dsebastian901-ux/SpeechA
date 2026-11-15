"""Decisiones operativas explícitas; todos los datos son sintéticos."""
from pathlib import Path
from copy import deepcopy
import pytest
from openpyxl import Workbook,load_workbook
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import assess_privacy
from app.services.batch_report_service import BatchReportService


def analyze(text,seconds=90,**overrides):
    relation={'estatus_grabacion':'NO DEFINE FECHA DE PAGO','fecha':'2026-11-15','asignacion':'1PV',
              'numero_de_tarjeta':'1234567890123456','pago_minimo':'1000','saldo_total':'3000',
              'corte':'23','vencimiento':'2026-11-23',
              'nombre_final':'1234567890123456_1PV_352_TH_PERSONA_MRS_20261115'}
    relation.update(overrides)
    return A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav',
        'texto':text,'duracion_segundos':seconds}),relation)


@pytest.mark.parametrize('phrase',[
    'Presenta atraso.','Le llamo por el atraso de su tarjeta.',
    'Nos comunicamos de jurídico MRS por atraso de su tarjeta.',
    'Respecto a su atraso.','Presenta un atraso.','Tiene un atraso.',
])
def test_authorized_generic_arrears_do_not_trigger_privacy_even_for_third_party(phrase):
    r=assess_privacy('Gestor: '+phrase,third_party_confirmed=True)
    assert not r['confirmed_disclosure'] and not r['review_required']
    assert r['allowed_generic_arrears_mentions']


@pytest.mark.parametrize('phrase',[
    'Presenta dos mensualidades vencidas.','Tiene tres meses de atraso.',
    'Su saldo vencido es de 1500 pesos.','Su atraso es de 1500 pesos.',
    'La tarjeta es 1234567890123456.','Tiene una deuda de 500 pesos.',
])
def test_authorized_generic_does_not_exempt_specific_protected_facts(phrase):
    r=assess_privacy('Gestor: Presenta atraso. '+phrase,third_party_confirmed=True)
    assert r['confirmed_disclosure']


def test_generic_notice_is_not_reintroduced_by_legacy_word_detectors():
    a=analyze('Habla MRS. Soy su hermana. Presenta atraso. Dígale que se comunique. Le paso el recado.',
              estatus_grabacion='MENSAJE CON FAMILIAR')
    assert not a.metadata['privacy_validation']['review_required']
    assert not a.metadata['privacy_validation']['confirmed_disclosure']


def test_confirmed_refusal_closes_quality_and_keeps_unattributed_financial_alert():
    a=analyze('Habla MRS. Soy su madre. Tiene una deuda de 500 pesos. No le voy a pasar el recado.',
              estatus_grabacion='MENSAJE CON FAMILIAR')
    d=a.metadata['shared_classification']
    assert d['clasificacion']=='NO_APROBADO' and not d['calidad_aprobada']
    assert d['requires_alert_review'] and any(f['code']=='UNCERTAIN_DISCLOSURE'for f in d['pending_alerts'])
    assert any(r['state']=='ALERTA_PENDIENTE'for r in d['rule_evaluation'])


def test_confirmed_critical_failure_has_priority_over_refusal_and_score():
    a=analyze('Tercero: Soy su madre.\nGestor: Tiene una deuda de 500 pesos.\nTercero: No le voy a pasar el recado.',
              estatus_grabacion='MENSAJE CON FAMILIAR')
    assert a.metadata['shared_classification']['clasificacion']=='FALLA_GRAVE'


SHORT_AGREEMENT=('Gestor: Habla MRS. ¿Me puede comunicar con Persona Ejemplo?\n'
    'Titular: Soy yo.\nGestor: ¿Podemos confirmar su pago de 1000 pesos para mañana?\n'
    'Titular: Sí.\nGestor: Puede pagar en Farmacias del Ahorro y 7-Eleven. '
    'Envíe su comprobante por WhatsApp. Gracias, hasta luego.\nTitular: Gracias, hasta luego.')


def test_short_complete_safe_agreement_is_approved_in_its_own_category():
    a=analyze(SHORT_AGREEMENT,seconds=40,estatus_grabacion='CONVENIO',
              nombre_final='1234567890123456_1PV_352_PP_PERSONA_MRS_20261115')
    d=a.metadata['shared_classification']
    assert d['clasificacion']=='APROBADO_DURACION_MENOR' and d['aprobado']
    assert d['management_completeness']['complete']


def test_short_greeting_without_management_is_not_approved():
    a=analyze('Habla MRS. Buen día.',seconds=12)
    assert not a.metadata['shared_classification']['calidad_aprobada']


def test_short_approval_does_not_waive_a_confirmed_critical_failure():
    a=analyze(SHORT_AGREEMENT+'\nGestor: Lo vamos a embargar y retirar bienes.',seconds=40,
              estatus_grabacion='CONVENIO')
    assert a.metadata['shared_classification']['clasificacion']=='FALLA_GRAVE'


def test_pending_alert_is_visible_in_excel_and_valid_word_without_external_library(tmp_path):
    from app.services.pending_alert_report import write_pending_alerts_word
    from docx import Document
    a=analyze('Habla MRS. Soy su madre. Tiene una deuda de 500 pesos. No le voy a pasar el recado.',
              estatus_grabacion='MENSAJE CON FAMILIAR')
    item={'file_name':'synthetic.wav','status':'completado','classification':a.metadata['shared_classification'],
          'analytics_metadata':a.metadata,'analytics':a.to_dict(),'compliance_score':a.compliance_score,
          'relation':{'gestor':'Persona Ejemplo','numero_de_tarjeta':'1234567890123456'}}
    p=BatchReportService.generate_report([item],tmp_path/'project/02_Audios/Transcripciones')
    w=load_workbook(p,data_only=True)
    try:
        assert w['ALERTAS_PENDIENTES'].max_row>1
        assert dict(w['RESUMEN'].values)['Revisión manual']==0
        assert dict(w['RESUMEN'].values)['Llamadas rechazadas con alertas pendientes']==1
    finally:w.close()
    path=write_pending_alerts_word([item],p)
    assert any('UNCERTAIN_DISCLOSURE'in q.text for q in Document(path).paragraphs)


def test_mislabeled_excel_does_not_create_convenio_deductions_for_a_refused_offer():
    text='Habla MRS. Soy yo. ¿Podemos confirmar su pago de 1000 pesos para mañana? No, no puedo pagar ahora.'
    a=analyze(text,estatus_grabacion='CONVENIO',nombre_final='1234567890123456_1PV_352_PP_PERSONA_MRS_20261115')
    ids={p['id']for p in a.metadata['penalties']}
    assert not ids.intersection({'PEN_CONV_LUGARES','PEN_CONV_WHATSAPP','PEN007','PEN009'})
    assert a.metadata['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'


def test_unknown_followup_amount_is_pending_but_confirmed_insufficient_is_rejected():
    unknown=analyze('Habla MRS. Soy yo. Ya pagué ayer. Envíe su comprobante por WhatsApp.')
    assert unknown.metadata['shared_classification']['clasificacion']=='REVISAR'
    below=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos ayer. Envíe su comprobante por WhatsApp.')
    assert below.metadata['shared_classification']['clasificacion']=='NO_APROBADO'
    covered=analyze('Habla MRS. Soy yo. Ya pagué 1000 pesos ayer. Envíe su comprobante por WhatsApp.')
    assert covered.metadata['shared_classification']['aprobado']


def test_generic_notice_does_not_waive_a_collection_request_to_third_party():
    p=assess_privacy('Gestor: Le requiere cubrir el atraso.',third_party_confirmed=True)
    assert p['confirmed_disclosure']

@pytest.mark.parametrize('minimum',[None,'','   '])
def test_missing_minimum_is_not_converted_to_a_covered_zero(minimum):
    a=analyze('Habla MRS. Soy yo. Ya pagué 1000 pesos ayer. Envíe su comprobante por WhatsApp.',pago_minimo=minimum)
    assert not a.metadata['negotiation_validation']['prior_payment_covers_minimum']
    assert not a.metadata['shared_classification']['aprobado']

@pytest.mark.parametrize('code,field',[
 ('WAIT_WITHOUT_RESUMPTION','wait_validation'),('CALL_END','call_end_validation'),
 ('NO_COLLECTION_ATTEMPT','negotiation_validation'),('SHORT_MANAGEMENT_INCOMPLETE','management_completeness'),
])
def test_pending_cause_without_extracted_quote_has_original_context_without_invented_timing(code,field):
 from app.services.pending_review_report import review_steps
 original='Texto sintético original para cotejar la causa pendiente.'
 item={'result':{'texto':original},'analytics_metadata':{},'classification':{'clasificacion':'REVISAR',
  'decision_findings':[{'code':code,'severity':'REVIEW','source_field':field,'reasons':['Causa pendiente explícita.']}]}}
 step=review_steps(item)[0]
 assert step['evidence'][0]['text']==original
 assert step['evidence'][0]['start']is None and step['evidence'][0]['end']is None
 assert step['evidence'][0]['speaker_role']=='NO DETERMINADO'
