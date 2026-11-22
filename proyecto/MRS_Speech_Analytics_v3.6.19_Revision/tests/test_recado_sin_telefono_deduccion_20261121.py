"""Regla de monitoreo confirmada: recado aceptado sin teléfono = -15.

Pruebas sintéticas, NO verifican audios reales. Mantener separadas calidad,
estatus de recado y duda acústica sobre contacto que sí fue ofrecido.
"""
from copy import deepcopy

from app.services.quality_decision import evaluate_quality
from app.services.analytics_service import AnalyticsService
from app.models.transcriptions import TranscriptionModel


def _metadata():
    return {
        'quality_contact_type':'TERCERO / FAMILIAR',
        'status_validation':{
            'excel_status':'MENSAJE CON FAMILIAR',
            'detected_status':'MENSAJE CON FAMILIAR',
            'matches':True,'valid':True,'review_required':False,
            'evidence_method':'RECADO_ACEPTADO_SIN_CONTACTO_PENALIZADO',
            'evidence':'Tercero: Sí, dígame. Gestor: Por favor dígale que se comunique con nosotros.',
        },
        'message_workflow_validation':{
            'recipient_accepted':True,'directed_body':True,
            'callback_available':False,'final_refusal':False,
            'recado_sin_contacto_confirmado':True,
        },
        'message_delivery_validation':{
            'review_required':False,
            'deduction_code':'PEN_RECADO_SIN_CONTACTO_RETORNO',
        },
        'penalties':[{
            'id':'PEN_RECADO_SIN_CONTACTO_RETORNO',
            'category':'Recado','points':15,'invalidates':False,
            'reason':'Se omitió el teléfono de retorno.'
        }],
        'critical_failures':[],
    }


def test_85_points_and_only_15_point_recado_omission_is_approved():
    result=evaluate_quality(_metadata(),85,duration_seconds=90)
    assert result['clasificacion']=='APROBADO'
    assert result['aprobado'] is True
    assert result['score']==85
    assert not result['requires_alert_review']
    assert not any(f['severity'] in ('REVIEW','CRITICAL')
                   for f in result['decision_findings'])


def test_80_points_with_other_independent_five_point_deduction_is_approved():
    meta=_metadata()
    meta['penalties'].append({
        'id':'PEN_OTRO_5','category':'Trato','points':5,
        'invalidates':False,'reason':'Otro descuento confirmado e independiente'})
    result=evaluate_quality(meta,80,duration_seconds=90)
    assert result['clasificacion']=='APROBADO'
    assert result['aprobado'] is True
    assert result['score']==80


def test_below_80_remains_rejected_even_for_accepted_recado():
    result=evaluate_quality(_metadata(),79,duration_seconds=90)
    assert result['clasificacion']=='NO_APROBADO_MENOR_80'
    assert not result['aprobado']


def test_independent_privacy_issue_blocks_approval():
    meta=_metadata()
    meta['privacy_validation']={
        'confirmed_disclosure':True,'reason':'Divulgación de saldo a tercero corroborada'}
    result=evaluate_quality(meta,85,duration_seconds=90)
    assert result['clasificacion']=='FALLA_GRAVE'
    assert not result['aprobado']


def test_attempted_but_unverifiable_callback_still_requires_audio_review():
    meta=_metadata()
    meta['message_delivery_validation']={
        'review_required':True,
        'reason':'Se ofreció dictado, pero falta corroborar lo que escuchó ASR.'}
    meta['message_workflow_validation']['recado_sin_contacto_confirmado']=False
    meta['penalties']=[]
    result=evaluate_quality(meta,100,duration_seconds=90)
    assert result['clasificacion']=='REVISAR'
    assert not result['aprobado']


def test_realistic_recado_recibido_missing_callback_does_not_force_review():
    text=(
        'Gestor: Soy Carla de MRS Consultores en representación de Bradescard. '
        '¿Puedo dejar un recado para el señor Juan? '
        'Tercero: Soy su hermana. Sí, dígame por favor. '
        'Gestor: Dígale por favor que se comunique con MRS Consultores. '
        'Tercero: De acuerdo, le aviso.'
    )
    analysis=AnalyticsService.analyze_transcription(
        TranscriptionModel.from_dict({
            'archivo':'synthetic_recado_sin_telefono.ogg',
            'texto':text,'duracion_segundos':92,
        }),
        {
            'numero_de_tarjeta':'1234567890123456',
            'nombre_final':'1234567890123456_1PV_352_3EROS_PERSONA_MRS_20261121',
            'estatus_grabacion':'MENSAJE CON FAMILIAR',
            'fecha':'2026-11-21','vencimiento':'2026-11-30',
            'asignacion':'1PV','pago_minimo':'1000','saldo_total':'3000','corte':'23'
        })
    meta=analysis.metadata
    assert meta['message_workflow_validation']['recado_sin_contacto_confirmado']
    assert not meta['message_delivery_validation']['review_required']
    assert meta['status_validation']['detected_status']=='MENSAJE CON FAMILIAR'
    assert meta['status_validation']['valid']
    omission=[p for p in meta['penalties']
              if p['id']=='PEN_RECADO_SIN_CONTACTO_RETORNO']
    assert len(omission)==1 and omission[0]['points']==15
    assert not any(f['code']=='CALLBACK_NOT_DELIVERED'
                   for f in meta['shared_classification']['decision_findings'])
