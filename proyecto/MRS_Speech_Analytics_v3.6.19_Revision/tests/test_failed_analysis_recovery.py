"""Una caída de reglas no elimina Whisper ni reutiliza un audio ajeno."""
import json
from pathlib import Path

import pytest

from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.analytics_service import AnalyticsService
from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service


def source_checkpoint(tmp_path, *, name='same.wav', embedded=None):
    text = {'archivo': name, 'texto': 'Habla MRS. Soy su madre. Dígale que se comunique. Le paso el recado.',
            'duracion_segundos': 90, 'segmentos': []}
    folder = tmp_path/'transcripts'; folder.mkdir()
    (folder/'same.json').write_text(json.dumps(text), encoding='utf-8-sig')
    source = tmp_path/'batch.json'
    source.write_text(json.dumps({'output_directory': str(folder), 'items': [
        {'file_name': 'same.wav', 'result': embedded, 'status': 'error',
         'message': "name 'payment_date_confirmed' is not defined"}]}), encoding='utf-8')
    return source, text


def test_failed_analysis_recovers_saved_json_without_whisper(tmp_path, monkeypatch):
    source, text = source_checkpoint(tmp_path)
    raw = source.read_bytes()
    monkeypatch.setattr(whisper_service, 'transcribe_audio', lambda **kw: pytest.fail('No Whisper'))
    result = reanalyze_checkpoint(source, tmp_path/'new')
    saved = json.loads(Path(result['checkpoint']).read_text(encoding='utf-8'))
    assert result['outcomes'] == {'APROBADO': 1}
    assert saved['items'][0]['result'] == text
    assert len(saved['items'][0]['transcription_recovery']['sha256']) == 64
    assert source.read_bytes() == raw


@pytest.mark.parametrize('name', ['other.wav', 'same.ogg'])
def test_same_stem_or_wrong_audio_is_never_recovered(tmp_path, name):
    source, _ = source_checkpoint(tmp_path, name=name)
    result = reanalyze_checkpoint(source, tmp_path/'new')
    assert result['outcomes'] == {'ERROR': 1}


def test_embedded_transcript_wins_over_external_json(tmp_path):
    embedded = {'archivo': 'same.wav', 'texto': 'Familiar: Soy su madre.\nGestor: Debe 1500 pesos.',
                'duracion_segundos': 90, 'segmentos': []}
    source, _ = source_checkpoint(tmp_path, embedded=embedded)
    result = reanalyze_checkpoint(source, tmp_path/'new')
    saved = json.loads(Path(result['checkpoint']).read_text(encoding='utf-8'))
    assert result['outcomes'] == {'FALLA_GRAVE': 1}
    assert saved['items'][0]['result'] == embedded
    assert 'transcription_recovery' not in saved['items'][0]


def test_recovery_rejects_same_name_from_another_audio_directory(tmp_path):
    source, text = source_checkpoint(tmp_path)
    text['ruta_audio'] = str(tmp_path/'other/same.wav')
    (tmp_path/'transcripts/same.json').write_text(json.dumps(text), encoding='utf-8')
    payload = json.loads(source.read_text(encoding='utf-8'))
    payload['items'][0]['path'] = str(tmp_path/'original/same.wav')
    source.write_text(json.dumps(payload), encoding='utf-8')
    result = reanalyze_checkpoint(source, tmp_path/'new')
    assert result['outcomes'] == {'ERROR': 1}


def test_missing_json_stays_error_without_retranscribing(tmp_path, monkeypatch):
    source, _ = source_checkpoint(tmp_path)
    (tmp_path/'transcripts/same.json').unlink()
    monkeypatch.setattr(whisper_service, 'transcribe_audio', lambda **kw: pytest.fail('No Whisper'))
    result = reanalyze_checkpoint(source, tmp_path/'new')
    assert result['outcomes'] == {'ERROR': 1}


def test_batch_analysis_failure_preserves_transcript_and_clears_score(tmp_path, monkeypatch):
    source = tmp_path/'same.wav'; source.write_bytes(b'synthetic')
    output = tmp_path/'project/02_Audios/Transcripciones'; output.mkdir(parents=True)
    text = {'archivo': 'same.wav', 'texto': 'Habla MRS.', 'duracion_segundos': 90, 'segmentos': []}
    (output/'same.json').write_text(json.dumps(text), encoding='utf-8')
    batch = BatchService(); batch.set_files([str(source)])
    batch.items[0]['classification'] = {'clasificacion': 'APROBADO', 'aprobado': True}
    batch.items[0]['compliance_score'] = 100
    batch.items[0]['classified_audio_path'] = 'old-approved.wav'
    monkeypatch.setattr(whisper_service, 'transcribe_audio', lambda **kw: pytest.fail('No Whisper'))
    def fail(*a, **kw):
        raise NameError("name 'payment_date_confirmed' is not defined")
    monkeypatch.setattr(AnalyticsService, 'analyze_transcription', fail)
    batch.process_all(str(output))
    item = batch.items[0]
    assert item['status'] == 'error' and item['result'] == text
    assert item['classification']['clasificacion'] == 'ERROR'
    assert not item['classification']['aprobado'] and item['compliance_score'] is None
    assert item['classified_audio_path'] is None
    saved = json.loads(Path(batch.checkpoint_path).read_text(encoding='utf-8'))
    assert saved['items'][0]['result'] == text
