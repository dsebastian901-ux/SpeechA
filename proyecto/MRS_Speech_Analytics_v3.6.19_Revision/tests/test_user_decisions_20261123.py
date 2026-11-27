"""Criterios nuevos de la usuaria; datos y audios de prueba sintéticos."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from openpyxl import Workbook, load_workbook
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.classification_policy import saved_result, OPERATIONAL_LABELS


CONTEXT = {'numero_de_tarjeta':'1234567890123456',
    'nombre_final':'1234567890123456_1PV_352_PP_PERSONA_MRS_20261121',
    'estatus_grabacion':'CONVENIO', 'asignacion':'1PV', 'fecha':'2026-11-21',
    'vencimiento':'2026-11-30', 'corte':23, 'pago_minimo':1000, 'saldo_total':3000}


def analyze(text, **context):
    return A.analyze_transcription(TranscriptionModel('synthetic.wav','synthetic.wav',
        'Gestor: Habla MRS. Titular: Soy yo. '+text, duration_seconds=95),dict(CONTEXT,**context))


def test_outside_operational_window_is_grave_not_customer_refusal():
    tail=' Gestor: Puede pagar en Kiosko o tiendas 3B. Envíe el comprobante por WhatsApp.'
    valid=analyze('Titular: Me comprometo a pagar 1000 pesos el 23 de noviembre.'+tail)
    late=analyze('Titular: Me comprometo a pagar 1000 pesos el 25 de noviembre.'+tail)
    m=late.metadata;d=m['shared_classification']
    assert m['status_validation']['detected_status']=='CONVENIO'
    assert m['status_validation']['evidence_method']=='CONVENIO_CON_FECHA_FUERA_DE_POLITICA'
    # Decisión posterior expresa del 26/11: gravedad sin modificar puntos.
    assert d['clasificacion']=='FALLA_GRAVE' and not d['aprobado']
    assert d['score']==valid.metadata['shared_classification']['score']
    assert [(p['id'],p['points'])for p in m['penalties']]==[(p['id'],p['points'])for p in valid.metadata['penalties']]


@pytest.mark.parametrize('text',[
    'Titular: Ya pagué 900 pesos. Gestor: Envíe su comprobante por WhatsApp.',
    'Titular: Ya pagué 900 pesos. Gestor: Quedo en espera del ticket de pago.',
])
def test_reported_sufficient_amount_and_receipt_request_is_followup(text):
    m=analyze(text,pago_minimo=700).metadata
    assert m['status_validation']['detected_status']=='CONVENIO'
    assert m['negotiation_validation']['prior_payment_total']==900
    assert m['negotiation_validation']['reported_payment_management']['receipt_requested']
    assert not m['status_validation']['bank_payment_verified']
    assert m['shared_classification']['clasificacion']=='APROBADO'


def test_insufficient_payment_only_receipt_is_minor_failure_with_original_deduction():
    m=analyze('Titular: Ya pagué 500 pesos. Gestor: Envíe comprobante por WhatsApp.').metadata
    assert m['negotiation_validation']['prior_payment_total']==500
    assert m['shared_classification']['clasificacion']=='FALLA_MINIMA'
    assert m['shared_classification']['score']==85
    assert 'PEN_SIN_INTENTO_NEGOCIACION'in {p['id']for p in m['penalties']}


@pytest.mark.parametrize('action',[
    'Gestor: ¿Cuánto puede pagar para completar la diferencia?',
    'Gestor: Puede pagar 500 pesos para completar la diferencia hoy.',
])
def test_managed_difference_without_acceptance_is_no_define(action):
    m=analyze('Titular: Ya pagué 500 pesos. Gestor: Envíe comprobante por WhatsApp. '+action+
        ' Titular: No puedo confirmar lo que falta.').metadata
    assert m['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'
    facts=m['negotiation_validation']['reported_payment_management']
    assert facts['has_collection_action'] and not facts['confirmed_receipt_only_shortfall']
    assert m['shared_classification']['clasificacion']!='FALLA_MINIMA'
    if action.startswith('Gestor: ¿Cuánto'):
        assert m['negotiation_validation']['valid']
        assert m['negotiation_validation']['tipo_monto_detectado']=='PAGO PREVIO REPORTADO'
        assert m['shared_classification']['clasificacion']=='APROBADO_ETIQUETA_CORREGIDA'


def test_receipt_only_without_amount_is_minor_and_does_not_invent_coverage():
    m=analyze('Titular: Ya pagué. Gestor: Envíe su comprobante por WhatsApp.').metadata
    n=m['negotiation_validation']
    assert n['prior_payment_total']is None and not n['prior_payment_covers_minimum']
    assert m['shared_classification']['clasificacion']=='FALLA_MINIMA'


def test_question_without_understandable_amount_remains_uncertainty():
    m=analyze('Titular: Ya pagué. Gestor: ¿Qué cantidad pagó? Titular: No se escucha bien. '
        'Gestor: Envíe comprobante por WhatsApp.').metadata
    assert not m['negotiation_validation']['reported_payment_management']['confirmed_receipt_only_without_amount']
    assert m['shared_classification']['clasificacion']=='REVISAR'


def test_known_payment_but_no_receipt_request_is_minor_not_aclaracion():
    m=analyze('Titular: Ya pagué 1500 pesos. Gestor: Llame hoy al banco para verificar la aplicación.').metadata
    assert m['shared_classification']['clasificacion']=='FALLA_MINIMA'
    assert m['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'


def test_collection_action_does_not_waive_receipt_for_reported_payment():
    m=analyze('Titular: Ya pagué 500 pesos. Gestor: Puede pagar 500 pesos para completar la diferencia hoy. '
        'Titular: No puedo confirmar lo que falta.').metadata
    assert m['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'
    f=m['negotiation_validation']['reported_payment_management']
    assert f['has_collection_action'] and not f['confirmed_receipt_only_shortfall']
    assert f['confirmed_missing_receipt_request']
    assert m['shared_classification']['clasificacion']=='FALLA_MINIMA'


def test_tomorrow_without_confirmed_amount_is_no_define():
    m=analyze('Titular: Mañana hago el depósito. Gestor: El pago es de 1200 pesos mañana. '
        'Envíe el comprobante por WhatsApp.').metadata
    assert m['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'
    assert not m['status_validation']['amount_confirmed_from_dialogue']


@pytest.mark.parametrize('period,expected',[('', 'FALLA_MINIMA'),(' el mes pasado', 'APROBADO')])
def test_prior_billing_period_does_not_create_a_false_current_receipt_omission(period,expected):
    m=analyze('Titular: Ya pagué 500 pesos'+period+'. '
        'Gestor: Le ofrecemos una opción de pago mínimo de 1000 pesos hoy. '
        'Titular: No voy a poder pagar más dinero.',estatus_grabacion='NO DEFINE FECHA DE PAGO',
        nombre_final=CONTEXT['nombre_final'].replace('_PP_','_TH_')).metadata
    assert m['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'
    assert m['shared_classification']['clasificacion']==expected
    assert m['negotiation_validation']['reported_payment_management']['applies'] is (not bool(period))


@pytest.mark.parametrize('problem',['critical','privacy_pending','missing_excel'])
def test_minor_failure_does_not_waive_independent_controls(problem):
    m=deepcopy(analyze('Titular: Ya pagué 500 pesos. Gestor: Envíe el comprobante por WhatsApp.').metadata)
    base={}
    if problem=='critical':m['privacy_validation']['confirmed_disclosure']=True
    elif problem=='privacy_pending':m['privacy_validation']['review_required']=True
    else:base={'missing_excel_relation':True}
    d=A.shared_quality_decision(m,85,80,95,base)
    assert not d['aprobado']
    if problem=='critical':assert d['clasificacion']=='FALLA_GRAVE'
    elif problem=='privacy_pending':
        assert d['clasificacion']=='FALLA_MINIMA' and d['requires_alert_review']
        assert any(f['rule_group']==3 for f in d['pending_alerts'])
        from app.services.batch_report_service import BatchReportService
        assert BatchReportService._nivel_atencion(d,m)=='ALTA'
    else:assert d['clasificacion']=='SIN_RELACION_EXCEL'


def test_confirmed_expiry_failure_keeps_original_penalty_priority():
    m=analyze('Titular: Me comprometo a pagar 1000 pesos el 2 de diciembre.').metadata
    assert m['shared_classification']['clasificacion']=='FALLA_GRAVE'
    assert any(p['id']=='PEN005'and p['invalidates']for p in m['penalties'])


def test_minor_failure_saved_label_is_not_an_approval():
    assert saved_result({'classification':{'clasificacion':'FALLA_MINIMA'}})=='FALLA_MINIMA'
    assert OPERATIONAL_LABELS['FALLA_MINIMA']=='FALLA MÍNIMA'


def test_rejected_recado_can_pass_quality_without_inventing_receipt_or_code():
    a=A.analyze_transcription(TranscriptionModel('synthetic.wav','synthetic.wav',
        'Gestor: Habla MRS. Tercero: Soy su hermana. No quiero recibir el recado.',duration_seconds=95),
        dict(CONTEXT,estatus_grabacion='MENSAJE CON FAMILIAR'))
    m=a.metadata;d=m['shared_classification']
    assert m['status_validation']['detected_status']=='SE NIEGAN A TOMAR RECADO'
    assert not m['message_workflow_validation']['complete']
    assert d['clasificacion']=='APROBADO_SIN_ETIQUETAR' and d['calidad_aprobada']
    assert not d['output_label_correction']['valid']
    assert d['output_label_pending']['detected_status']=='SE NIEGAN A TOMAR RECADO'


def test_known_followup_and_unparseable_name_keep_original_with_pending_label():
    m=analyze('Titular: Ya pagué 1500 pesos. Gestor: Envíe el comprobante por WhatsApp.',
        estatus_grabacion='NO DEFINE FECHA DE PAGO', nombre_final='sin_bloque.ogg').metadata
    d=m['shared_classification']
    assert d['clasificacion']=='APROBADO_SIN_ETIQUETAR' and d['calidad_aprobada']
    assert d['output_label_pending']['original_name']=='sin_bloque.ogg'
    assert not d['output_label_correction']['valid']


@pytest.mark.parametrize('problem',['privacy','amount','confidence','evidence','score'])
def test_pending_label_resolves_only_a_proven_status_discrepancy(problem):
    m=deepcopy(analyze('Titular: Ya pagué 1500 pesos. Gestor: Envíe el comprobante por WhatsApp.',
        estatus_grabacion='NO DEFINE FECHA DE PAGO',nombre_final='sin_bloque.ogg').metadata)
    if problem=='privacy':m['privacy_validation']['review_required']=True
    elif problem=='amount':m['negotiation_validation']['review_required']=True
    elif problem=='confidence':m['status_validation']['detection_confidence']='MEDIA'
    elif problem=='evidence':m['status_validation']['evidence']=''
    d=A.shared_quality_decision(m,70 if problem=='score' else 100,80,95)
    assert not d['calidad_aprobada']


def test_new_batch_minor_failure_copy_report_and_consolidation(tmp_path,monkeypatch):
    from app.services.batch_service import BatchService
    from app.services.whisper_service import whisper_service
    from app.services.consolidated_report_service import _record
    original=tmp_path/'original.wav';original.write_bytes(b'synthetic audio; ASR stub')
    source=original.read_bytes();excel=tmp_path/'accounts.xlsx';w=Workbook();s=w.active;s.title='Relacion_Audios'
    headers=['archivo_original','gestor',*CONTEXT];s.append(headers);s.append([original.name,'Gestor sintético',*CONTEXT.values()]);w.save(excel);w.close()
    excel_bytes=excel.read_bytes()
    def transcribe(audio_path,output_directory):
        output=Path(output_directory)/'result.json';output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps({'archivo':original.name,'texto':'Gestor: Habla MRS. Titular: Soy yo. Ya pagué 500 pesos. Gestor: Envíe el comprobante por WhatsApp.','duracion_segundos':95,'segmentos':[]}),encoding='utf-8')
        return {'ruta_json':str(output)}
    monkeypatch.setattr(whisper_service,'transcribe_audio',transcribe)
    b=BatchService();b.set_files([str(original)]);b.set_relation_excel(excel)
    b.process_all(output_directory=tmp_path/'project/02_Audios/Transcripciones')
    item=b.items[0];decision=item['classification'];copy=Path(item['classified_audio_path'])
    assert decision['clasificacion']=='FALLA_MINIMA' and not decision['aprobado']
    assert copy.parent.name=='FALLA_MINIMA' and copy.read_bytes()==source
    assert original.read_bytes()==source and excel.read_bytes()==excel_bytes
    summary=b.get_classification_summary()
    assert summary['fallas_minimas']==1 and summary['aprobados']==summary['revisar']==summary['fallas_graves']==0
    w=load_workbook(b.last_report_path,data_only=True)
    try:
        assert w['FALLA_MINIMA'].max_row==2
        assert dict(w['RESUMEN'].values)['Fallas mínimas']==1
        rows=list(w['RESULTADOS'].values);row=dict(zip(rows[0],rows[1]))
        assert row['Resultado IA']=='FALLA_MINIMA'
        assert row['Resultado Final Operativo']=='NO APROBADO - FALLA MÍNIMA'
        assert row['Nivel de atención']=='MEDIA'
    finally:w.close()
    record=_record(item,{'name':'synthetic','sha256':'synthetic','updated':None})
    assert record['classification']=='FALLA_MINIMA' and not record['severe']
    assert any(e['code']=='CONFIRMED_MINOR_FAILURE'for e in record['errors'])
