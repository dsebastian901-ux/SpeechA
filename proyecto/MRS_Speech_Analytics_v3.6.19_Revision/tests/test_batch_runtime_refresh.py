"""El procesamiento habitual debe actualizar dictámenes, no solo la cabecera."""
import json
from pathlib import Path

import pytest

from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service


TEXT = ('Habla MRS. Soy su madre. Dígale que se comunique al número de contacto '
        '5512345678. Le paso el recado.')


def saved_call(tmp_path, text=TEXT, **extra):
    audio = tmp_path / 'originales' / 'ejemplo.wav'
    audio.parent.mkdir()
    audio.write_bytes(b'audio de prueba: no ejecutar ASR')
    output = tmp_path / 'proyecto' / '02_Audios' / 'Transcripciones'
    output.mkdir(parents=True)
    data = dict(archivo=audio.name, ruta_audio=str(audio), texto=text,
                duracion_segundos=90, segmentos=[], **extra)
    sidecar = output / 'ejemplo.json'
    sidecar.write_text(json.dumps(data), encoding='utf-8')
    batch = BatchService()
    batch.set_files([audio])
    return batch, audio, output, sidecar, data


def no_asr(monkeypatch):
    def fail(**kwargs):
        pytest.fail('Actualizar reglas no debe ejecutar Whisper otra vez')
    monkeypatch.setattr(whisper_service, 'transcribe_audio', fail)


def test_normal_batch_refreshes_legacy_result_and_removes_stale_approved_copy(tmp_path, monkeypatch):
    batch, audio, output, sidecar, data = saved_call(
        tmp_path, 'Familiar: Soy su madre.\nGestor: Tiene una deuda de 1500 pesos.')
    old_copy = output.parent / 'Audios Clasificados' / 'APROBADOS' / audio.name
    old_copy.parent.mkdir(parents=True)
    old_copy.write_bytes(audio.read_bytes())
    batch.items[0].update(status='completado', result=data,
        classification={'clasificacion': 'APROBADO', 'aprobado': True},
        classified_audio_path=str(old_copy))
    batch._save_checkpoint(output, completed=True)
    old_checkpoint = Path(batch.checkpoint_path).read_bytes()
    no_asr(monkeypatch)
    assert len(batch.process_all(output)) == 1
    item = batch.items[0]
    assert item['classification']['clasificacion'] == 'FALLA_GRAVE'
    assert item['transcription_recovered']
    assert not old_copy.exists()
    assert audio.read_bytes() == Path(item['classified_audio_path']).read_bytes()
    assert any(p.read_bytes() == old_checkpoint for p in
               Path(batch.checkpoint_path).parent.rglob('checkpoint_*.json'))
    assert json.loads(sidecar.read_text()) == data
    assert batch.process_all(output) == [], 'El resultado actualizado sí es idempotente'


def test_finished_legacy_checkpoint_is_offered_for_normal_resume(tmp_path):
    batch, _, output, _, data = saved_call(tmp_path)
    batch.items[0].update(status='completado', result=data)
    batch._save_checkpoint(output, completed=True)
    info = BatchService().find_checkpoint(output)
    assert info and info['outdated'] == 1
    resumed = BatchService()
    resumed.resume_from_checkpoint(output)
    assert resumed.items[0]['result'] == data


def test_resume_keeps_embedded_excel_instead_of_changing_to_audio_only(tmp_path):
    batch, audio, output, _, data = saved_call(tmp_path)
    relation = dict(archivo_original=audio.name, gestor='Gestora ejemplo',
                    estatus_grabacion='CONVENIO', nombre_final='salida.wav',
                    numero_de_tarjeta='0123456789012345', pago_minimo='1800')
    batch.items[0].update(status='completado', result=data, relation=relation)
    batch.relation_enabled = True
    batch.relation_excel = str(tmp_path / 'otro_equipo' / 'cuentas.xlsx')
    batch._save_checkpoint(output)
    resumed = BatchService()
    resumed.resume_from_checkpoint(output)
    assert resumed.has_relation_excel()
    assert resumed.items[0]['relation']['pago_minimo'] == '1800'
    assert resumed.relation_service.find_record(audio).numero_de_tarjeta == relation['numero_de_tarjeta']


def test_selected_model_change_does_not_silently_reuse_small(tmp_path, monkeypatch):
    batch, audio, output, sidecar, _ = saved_call(tmp_path, modelo='small')
    monkeypatch.setattr(whisper_service, 'get_runtime_configuration', lambda: {'model': 'medium'})
    calls = []
    def asr(**kwargs):
        calls.append(kwargs['audio_path'])
        data = json.loads(sidecar.read_text())
        data['modelo'] = 'medium'
        sidecar.write_text(json.dumps(data))
        return {'ruta_json': str(sidecar)}
    monkeypatch.setattr(whisper_service, 'transcribe_audio', asr)
    batch.process_all(output)
    assert calls == [str(audio)]
    assert batch.items[0]['result']['modelo'] == 'medium'


def test_rule_change_updates_finished_call_through_normal_resume(tmp_path, monkeypatch):
    from app.services import batch_runtime_state as state
    batch, _, output, _, _ = saved_call(tmp_path)
    no_asr(monkeypatch)
    assert len(batch.process_all(output)) == 1
    assert BatchService().find_checkpoint(output) is None
    monkeypatch.setattr(state, 'engine_fingerprint', lambda: 'reglas_actualizadas')
    recovered = BatchService()
    assert recovered.find_checkpoint(output)['outdated'] == 1
    recovered.resume_from_checkpoint(output)
    assert len(recovered.process_all(output)) == 1
    assert recovered.items[0]['evaluation_stamp']['engine_fingerprint'] == 'reglas_actualizadas'
    assert recovered.items[0]['transcription_recovered']
    assert recovered.find_checkpoint(output) is None
    assert recovered.process_all(output) == []


def test_refresh_recovers_checkpoint_transcript_when_sidecar_is_missing(tmp_path, monkeypatch):
    batch, _, output, sidecar, data = saved_call(tmp_path)
    sidecar.unlink()
    batch.items[0].update(status='completado', result=data)
    no_asr(monkeypatch)
    assert len(batch.process_all(output)) == 1
    assert batch.items[0]['status'] == 'completado'
    assert batch.items[0]['transcription_recovered']
    assert batch.items[0]['result'] == data


def test_bom_sidecar_is_recovered_without_transcribing(tmp_path, monkeypatch):
    batch, _, output, sidecar, data = saved_call(tmp_path)
    sidecar.write_text(json.dumps(data), encoding='utf-8-sig')
    no_asr(monkeypatch)
    assert len(batch.process_all(output)) == 1
    assert batch.items[0]['status'] == 'completado'
    assert batch.items[0]['transcription_recovered']


@pytest.mark.parametrize('changes', [
    {'archivo': 'ejemplo.ogg'},
    {'ruta_audio': '/otra_carpeta/ejemplo.wav'},
    {'modelo': 'small'},
    {'idioma_solicitado': 'en'},
    {'beam_size': 1},
    {'vad_filter': False},
    {'word_timestamps': False},
])
def test_known_mismatch_never_falls_back_to_old_asr_if_model_fails(tmp_path, monkeypatch, changes):
    batch, _, output, sidecar, data = saved_call(tmp_path)
    data.update(changes)
    sidecar.write_text(json.dumps(data))
    monkeypatch.setattr(whisper_service, 'get_runtime_configuration', lambda: {
        'model': 'medium', 'language': 'es', 'beam_size': 5,
        'vad_filter': True, 'word_timestamps': True})
    calls = []
    def unavailable(**kwargs):
        calls.append(kwargs)
        raise RuntimeError('El modelo seleccionado no está instalado')
    monkeypatch.setattr(whisper_service, 'transcribe_audio', unavailable)
    assert batch.process_all(output) == []
    assert len(calls) == 1
    assert batch.items[0]['classification']['clasificacion'] == 'ERROR'
    assert not batch.items[0]['classification']['aprobado']
    assert json.loads(sidecar.read_text()) == data


def test_audio_replacement_requires_asr_even_with_same_filename(tmp_path, monkeypatch):
    batch, audio, output, _, _ = saved_call(tmp_path)
    no_asr(monkeypatch)
    batch.process_all(output)
    audio.write_bytes(b'este es un audio distinto, conservando el nombre')
    calls = []
    def unavailable(**kwargs):
        calls.append(kwargs)
        raise RuntimeError('ASR de prueba no disponible')
    monkeypatch.setattr(whisper_service, 'transcribe_audio', unavailable)
    batch.process_all(output)
    assert len(calls) == 1
    assert batch.items[0]['status'] == 'error'
    assert batch.items[0]['classification']['clasificacion'] == 'ERROR'


def test_manual_sidecar_correction_is_used_on_next_normal_run(tmp_path, monkeypatch):
    batch, _, output, sidecar, data = saved_call(tmp_path)
    no_asr(monkeypatch)
    batch.process_all(output)
    assert batch.items[0]['classification']['clasificacion'] == 'APROBADO'
    data['texto'] = 'Familiar: Soy su madre.\nGestor: Tiene una deuda de 1500 pesos.'
    sidecar.write_text(json.dumps(data))
    assert len(batch.process_all(output)) == 1
    assert batch.items[0]['classification']['clasificacion'] == 'FALLA_GRAVE'
    assert batch.items[0]['result']['texto'] == data['texto']


def test_only_managed_copy_can_be_retired(tmp_path):
    batch, audio, output, _, _ = saved_call(tmp_path)
    batch.items[0]['classified_audio_path'] = str(audio)
    batch._retire_classified_copy(batch.items[0], output)
    assert audio.exists()
    external = tmp_path / 'otra_copia.wav'
    external.write_bytes(b'archivo ajeno')
    batch.items[0]['classified_audio_path'] = str(external)
    batch._retire_classified_copy(batch.items[0], output)
    assert external.exists()


def test_no_excel_match_remains_missing_in_mode_a_after_resume(tmp_path, monkeypatch):
    batch, _, output, _, data = saved_call(tmp_path)
    batch.items[0].update(result=data, status='completado')
    batch.relation_enabled = True
    batch.relation_excel = str(tmp_path / 'cuentas_ausentes.xlsx')
    batch._save_checkpoint(output)
    resumed = BatchService()
    resumed.resume_from_checkpoint(output)
    no_asr(monkeypatch)
    resumed.process_all(output)
    assert resumed.has_relation_excel()
    assert resumed.items[0]['classification']['clasificacion'] == 'SIN_RELACION_EXCEL'
    assert not resumed.items[0]['classification']['aprobado']


@pytest.mark.parametrize('change_source', [False, True])
def test_normal_refresh_preserves_human_fact_but_revalidates_its_scope(tmp_path, monkeypatch, change_source):
    from app.services.recado_acceptance_review import make_recado_confirmation
    batch, audio, output, sidecar, data = saved_call(tmp_path,
        'Habla MRS. Es mi hermana. Le dejo un mensaje. '
        'Que se comunique con nosotros al número de contacto 5551234567.')
    relation = dict(archivo_original=audio.name, gestor='Gestora',
        estatus_grabacion='MENSAJE CON FAMILIAR', numero_de_tarjeta='1234567890123456',
        asignacion='1PV', nombre_final='1234567890123456_1PV_352_3EROS_GESTORA_MRS_20261117.wav')
    proof = make_recado_confirmation(data, relation, user_confirmed=True)
    if change_source:
        data = dict(data, texto=data['texto'] + ' Algo más.')
        sidecar.write_text(json.dumps(data))
    batch.items[0].update(status='completado', result=data, relation=relation,
                        recado_acceptance_confirmation=proof)
    batch.relation_enabled = True
    batch.relation_excel = str(tmp_path / 'cuentas_ausentes.xlsx')
    batch.relation_service.authorized_statuses = ['MENSAJE CON FAMILIAR']
    batch._save_checkpoint(output)
    resumed = BatchService()
    resumed.resume_from_checkpoint(output)
    no_asr(monkeypatch)
    resumed.process_all(output)
    item = resumed.items[0]
    assert item['recado_acceptance_confirmation'] == proof
    assert item['analytics_metadata']['recado_acceptance_validation']['valid'] is (not change_source)
    assert item['classification']['aprobado'] is (not change_source), item['classification']


def test_marking_old_results_outdated_never_fabricates_pending_transcriptions(tmp_path):
    from copy import deepcopy
    batch, _, output, _, data = saved_call(tmp_path)
    batch.items[0].update(status='completado', result=data)
    next_audio = tmp_path / 'originales' / 'pendiente.wav'
    next_audio.write_bytes(b'aun no procesado')
    batch.set_files([next_audio])
    pending = deepcopy(batch.items[1])
    batch._prepare_runtime_refresh(output, batch._runtime_context())
    assert batch.items[1] == pending
    assert batch.items[0]['status'] == 'pendiente'
    assert batch.items[0]['classification'] is None
    assert batch.get_classification_summary()['analizados'] == 0


def test_catalog_is_preserved_even_when_all_statuses_are_explicitly_disabled(tmp_path):
    payload = {'authorized_statuses': [], 'items': [{'relation': {'estatus_grabacion': 'CONVENIO'},
                'classification': {'estatus_autorizado': True}}]}
    assert BatchService._saved_authorized_statuses(payload) == []
    del payload['authorized_statuses']
    assert BatchService._saved_authorized_statuses(payload) == ['CONVENIO']
    payload['items'][0]['classification']['estatus_autorizado'] = False
    assert BatchService._saved_authorized_statuses(payload) == []


def test_bom_checkpoint_can_be_resumed_and_retried_errors_are_not_skipped(tmp_path):
    batch, _, output, _, _ = saved_call(tmp_path)
    batch.items[0].update(status='error', message='Interrupción de la carga del modelo')
    batch._save_checkpoint(output)
    path = Path(batch.checkpoint_path)
    payload = json.loads(path.read_text())
    path.write_text(json.dumps(payload), encoding='utf-8-sig')
    resumed = BatchService()
    assert resumed.find_checkpoint(output)['errors'] == 1
    resumed.resume_from_checkpoint(output)
    assert resumed.items[0]['status'] == 'pendiente'
