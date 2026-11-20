"""Casos sintéticos: sin datos de cuentas ni grabaciones reales."""
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.services.analytics_service import AnalyticsService as A
from app.services.payment_intent_frames import payment_frames
from app.services.consolidated_report_service import ConsolidatedReportService as C
from app.services.access_service import AccessStore


@pytest.mark.parametrize('answer', ['No, no.', 'No, señorita, no.', 'No, gracias.'])
def test_negative_question_without_explanation_does_not_create_payment_decision(answer):
    frames = payment_frames('¿No aplica el pago aún? ' + answer)
    assert not any(f['declined'] or f['accepted'] for f in frames)


def test_copy_failure_keeps_critical_quality_and_is_retriable(tmp_path, monkeypatch):
    from test_batch_runtime_refresh import saved_call, no_asr
    batch, audio, output, sidecar, data = saved_call(tmp_path,
        'Familiar: Soy su madre.\nGestor: Tiene una deuda de 1500 pesos.')
    no_asr(monkeypatch)
    original = batch._copy_classified_audio
    monkeypatch.setattr(batch, '_copy_classified_audio',
                        lambda **kw: (_ for _ in ()).throw(OSError('disco simulado')))
    batch.process_all(output)
    item = batch.items[0]
    assert item['classification']['clasificacion'] == 'FALLA_GRAVE'
    assert item['status'] == 'error'
    assert item['copy_status'] == 'error'
    assert item['copy_error']
    assert batch.get_classification_summary()['revisar'] == 0
    assert batch.get_classification_summary()['errores_copia'] == 1
    from app.services.batch_report_service import BatchReportService
    row = BatchReportService._row_from_item(item)
    assert row['Clasificación física'] == 'FALLA_GRAVE'
    assert row['Estado de copia'] == 'error' and row['Error de copia']
    assert not json.loads(Path(batch.checkpoint_path).read_text())['completed']
    monkeypatch.setattr(batch, '_copy_classified_audio', original)
    assert len(batch.process_all(output)) == 1
    assert item['status'] == 'completado' and not item.get('copy_error')
    assert Path(item['classified_audio_path']).read_bytes() == audio.read_bytes()
    assert json.loads(sidecar.read_text()) == data


def test_partial_copy_is_never_left_in_approved_folder(tmp_path, monkeypatch):
    from app.services.batch_service import BatchService
    import app.services.batch_service as module
    source = tmp_path / 'original.wav'; source.write_bytes(b'contenido completo sintetico')
    output = tmp_path / 'project' / 'Transcripciones'; output.mkdir(parents=True)
    def broken_copy(source, destination):
        Path(destination).write_bytes(b'incompleto')
        raise OSError('disco simulado')
    monkeypatch.setattr(module.shutil, 'copy2', broken_copy)
    item = {'path':str(source)}
    with pytest.raises(OSError):
        BatchService()._copy_classified_audio(item, None,
            {'clasificacion':'APROBADO','aprobado':True}, output)
    assert not any(p.is_file() for p in (output.parent/'Audios Clasificados').rglob('*'))
    assert source.read_bytes() == b'contenido completo sintetico'


def test_consolidated_pending_privacy_or_profanity_is_not_a_confirmed_error(tmp_path):
    from test_consolidated_reports import call, checkpoint
    item = call(1)
    item['analytics_metadata']['penalties'] = [
        {'id':'PEN_GROSERIA_SIN_ATRIBUCION','reason':'Voz por confirmar','points':0,'invalidates':False}]
    item['classification'].update(decision_findings=[
        {'code':'OFFENSIVE_LANGUAGE','source_field':'treatment_validation','rule_group':9,
         'severity':'REVIEW','reasons':['Voz por confirmar']}])
    data = C.load([checkpoint(tmp_path,'uno',[item])])
    assert not data['calls'][0]['errors']
    assert data['calls'][0]['pending_observations']
    result = C.generate(data,tmp_path/'out',level='DETALLADO')
    book=load_workbook(result['files']['xlsx'])
    try:
        assert book['ERRORES_COMUNES'].max_row == 1
        assert book['ALERTAS_PENDIENTES'].max_row > 1
    finally: book.close()


def test_failed_login_revokes_previous_session_and_authority(tmp_path):
    password='Clave sintetica de auditoria 123'
    store=AccessStore(tmp_path/'accounts');store.initialize(password)
    with pytest.raises(PermissionError): store.login('DANIELA SEBASTIAN','equivocada')
    assert not store.allowed('users')
    assert store.authority is None


def test_reported_instruction_does_not_hide_new_bank_destination():
    from app.services.payment_instruction_validation import wrong_bank_instructions
    banks={'SANTANDER':['santander']}; codes={'SANTANDER':'1234567'}
    new = 'Gestor: Me dijeron que pagara en tienda, pero ahora deposite a la cuenta Santander 7654321.'
    assert wrong_bank_instructions(new,[],banks,codes,'123456789012345678')
    old = 'Titular: Me dijeron que deposite a la cuenta Santander 7654321.'
    assert not wrong_bank_instructions(old,[],banks,codes,'123456789012345678')

@pytest.mark.parametrize('module,class_name,method', [
    ('settings_view','SettingsView','save_settings'),
    ('settings_view','SettingsView','reset_settings'),
    ('batch_view','BatchView','start_processing'),
    ('transcription_view','TranscriptionView','save_current_transcription'),
    ('analytics_view','AnalyticsView','analyze_selected'),
    ('consolidated_reports_dialog','ConsolidatedReportsDialog','_generate'),
])
def test_open_views_cannot_start_actions_after_session_expires(tmp_path,monkeypatch,module,class_name,method):
    import importlib
    from types import SimpleNamespace
    from app.services.access_service import activate
    import tkinter.messagebox
    store=AccessStore(tmp_path/'accounts');store.initialize('Clave sintetica de auditoria 123')
    activate(store)
    store.registry._clock=lambda:float('inf')
    errors=[]
    monkeypatch.setattr(tkinter.messagebox,'showerror',lambda *a,**kw:errors.append(a))
    try:
        cls=getattr(importlib.import_module('app.ui.views.'+module),class_name)
        getattr(cls,method)(SimpleNamespace())
        assert errors, 'La acción debe pedir reiniciar sesión antes de leer o cambiar datos'
    finally:activate(None)


def test_unevaluated_metadata_cannot_be_an_approval():
    result=A.shared_quality_decision({},100,duration_seconds=90)
    assert result['clasificacion']=='REVISAR'
    assert not result['calidad_aprobada']
    assert any(f['code']=='QUALITY_EVIDENCE_MISSING' for f in result['decision_findings'])


@pytest.mark.parametrize('duration',[float('nan'),float('inf'),-float('inf')])
def test_nonfinite_audio_duration_cannot_approve(duration):
    m={'quality_contact_type':'TITULAR','status_validation':{'valid':True}}
    result=A.shared_quality_decision(m,100,duration_seconds=duration)
    assert result['clasificacion']=='REVISAR'


@pytest.mark.parametrize('score',[float('nan'),float('inf'),-1,101])
def test_invalid_numeric_score_is_a_technical_input_error(score):
    with pytest.raises(ValueError):
        A.shared_quality_decision({'quality_contact_type':'TITULAR'},score,duration_seconds=90)


@pytest.mark.parametrize('answer',['No, no tengo dinero.','No, no puedo pagar.'])
def test_explanatory_negative_response_is_still_a_payment_response(answer):
    assert any(f['declined'] for f in payment_frames('¿No puede realizar el pago? '+answer))


def test_copy_verification_rejects_silent_truncation(tmp_path,monkeypatch):
    import app.services.batch_service as module
    from app.services.batch_service import BatchService
    source=tmp_path/'original.wav';source.write_bytes(b'original completo')
    output=tmp_path/'project'/'Transcripciones';output.mkdir(parents=True)
    monkeypatch.setattr(module.shutil,'copy2',lambda a,b:Path(b).write_bytes(b'parcial'))
    with pytest.raises(OSError):
        BatchService()._copy_classified_audio({'path':str(source)},None,
            {'clasificacion':'APROBADO','aprobado':True},output)
    assert not any(p.is_file() for p in (output.parent/'Audios Clasificados').rglob('*'))


def test_consolidated_approved_counter_agrees_with_batch_categories(tmp_path):
    from test_consolidated_reports import call,checkpoint
    from app.services.batch_service import BatchService
    from app.services.classification_policy import APPROVED_RESULTS
    from app.services.consolidated_report_service import _summary
    categories=['APROBADO','APROBADO_ETIQUETA_CORREGIDA','APROBADO_DURACION_MENOR',
        'APROBADO_SIN_ETIQUETAR','APROBADO_CON_EXCEPCION','REVISAR','FALLA_GRAVE','ERROR']
    items=[]
    for n,category in enumerate(categories):
        i=call(n);i['analytics_metadata']={}
        i['classification']={'clasificacion':category,'aprobado':category in APPROVED_RESULTS}
        items.append(i)
    batch=BatchService();batch.items=items
    dataset=C.load([checkpoint(tmp_path,'one',items)])
    assert _summary(dataset['calls'],())[0][1]==batch.get_classification_summary()['aprobados']==3


def test_critical_reported_failure_is_not_downgraded_by_pending_observation(tmp_path):
    from test_consolidated_reports import call,checkpoint
    i=call(1,grave=True)
    i['classification']['decision_findings']=[{'code':'UNCERTAIN_DISCLOSURE',
        'severity':'PENDING_ALERT','rule_group':3,'reasons':['Otro fragmento pendiente']}]
    r=C.load([checkpoint(tmp_path,'one',[i])])['calls'][0]
    assert r['severe'] and any(e['grave'] for e in r['errors'])
    assert r['pending_observations']
