"""Una aceptación humana resuelve solo ese hecho, sin eximir otras reglas."""
from copy import deepcopy
import json

import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.recado_acceptance_review import (
    make_recado_confirmation, validate_recado_confirmation, confirm_checkpoint_recado)

TEXT = ('Habla MRS. Es mi hermana. Le dejo un mensaje. '
        'Que se comunique con nosotros al número de contacto 5551234567.')


def fixture(text=TEXT):
    return ({'archivo': 'sample.ogg', 'texto': text, 'segmentos': [], 'duracion_segundos': 120},
            {'estatus_grabacion': 'MENSAJE CON FAMILIAR', 'numero_de_tarjeta': '1234567890123456',
             'asignacion': '1PV', 'nombre_final': 'salida'})


def analyze(data, relation, record=None):
    t = TranscriptionModel.from_dict(data)
    t.metadata['recado_acceptance_confirmation'] = record
    return A.analyze_transcription(t, relation)


def test_confirmation_is_scoped_separate_from_asr_and_resolves_acceptance():
    data, relation = fixture(); original = deepcopy(data)
    assert analyze(data, relation).metadata['final_result'] == 'REVISAR'
    record = make_recado_confirmation(data, relation, user_confirmed=True)
    result = analyze(data, relation, record)
    assert result.metadata['final_result'] == 'APROBADO'
    assert result.metadata['recado_acceptance_validation']['valid']
    assert data == original and not record.get('audio_verified')
    assert not record.get('speaker_roles_confirmed')
    assert result.metadata['status_validation']['recado_evidence']['confirmed_recado']


@pytest.mark.parametrize('confirmed', [False, None, 1, 'yes'])
def test_explicit_confirmation_is_required(confirmed):
    data, relation = fixture()
    with pytest.raises(ValueError, match='explícita'):
        make_recado_confirmation(data, relation, user_confirmed=confirmed)


@pytest.mark.parametrize('field,value', [
    ('archivo', 'other.ogg'), ('texto', TEXT+' Algo más.'), ('duracion_segundos', 121),
    ('segmentos', [{'text': TEXT, 'start': 0, 'end': 120}])])
def test_changed_source_cannot_reuse_confirmation(field, value):
    data, relation = fixture(); record = make_recado_confirmation(data, relation, user_confirmed=True)
    data[field] = value
    assert not validate_recado_confirmation(data, relation, record)['valid']
    assert not analyze(data, relation, record).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('field,value', [('numero_de_tarjeta', '1234567890123999'), ('asignacion', '2PV')])
def test_other_account_cannot_reuse_confirmation(field, value):
    data, relation = fixture(); record = make_recado_confirmation(data, relation, user_confirmed=True)
    relation[field] = value
    assert not validate_recado_confirmation(data, relation, record)['valid']


def test_output_name_correction_keeps_binding_valid():
    data, relation = fixture(); record = make_recado_confirmation(data, relation, user_confirmed=True)
    relation['nombre_final'] = 'corrected'
    assert validate_recado_confirmation(data, relation, record)['valid']


@pytest.mark.parametrize('field,value', [('active', False), ('scope', 'APPROVE_ALL'),
    ('user_confirmed', False), ('record_sha256', 'x'), ('source_binding', 'x')])
def test_tampered_or_revoked_fact_is_not_ignored_even_with_clear_asr(field, value):
    data, relation = fixture(TEXT+' Le paso el recado.')
    assert analyze(data, relation).metadata['final_result'] == 'APROBADO'
    record = make_recado_confirmation(data, relation, user_confirmed=True); record[field] = value
    assert analyze(data, relation, record).metadata['final_result'] == 'REVISAR'


@pytest.mark.parametrize('problem', [
    'No le voy a pasar el recado.', 'No lo conozco.', 'Me trataron mal.',
    'Tiene una deuda de 500 pesos.', 'Gestor: Tiene una deuda de 500 pesos.',
    'La tarjeta termina en 9999.', 'Gestor: Vamos a realizar una visita a su domicilio.',
    'Gestor: Qué poca madre.',
])
def test_acceptance_does_not_waive_refusal_privacy_mistreatment_card_or_threats(problem):
    data, relation = fixture(TEXT+' '+problem)
    record = make_recado_confirmation(data, relation, user_confirmed=True)
    assert not analyze(data, relation, record).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('text', [
    'Habla MRS. Es mi hermana.',
    'Habla MRS. Le dejo un mensaje. Que se comunique al número de contacto 5551234567.',
    'Habla MRS. Es mi hermana. ¿Le puedo dejar un recado?',
])
def test_acceptance_alone_cannot_invent_message_contact_or_family(text):
    data, relation = fixture(text)
    record = make_recado_confirmation(data, relation, user_confirmed=True)
    assert not analyze(data, relation, record).metadata['shared_classification']['aprobado']


def test_copy_reanalysis_preserves_fact_and_original_and_is_repeatable(tmp_path):
    data, relation = fixture()
    original = {'completed': True, 'items': [{'file_name': 'sample.ogg', 'result': data,
        'relation': relation, 'classification': {'puntaje_minimo': 80}}]}
    source = tmp_path/'original.json'; source.write_text(json.dumps(original), encoding='utf-8')
    raw = source.read_bytes()
    result = confirm_checkpoint_recado(source, 'sample.ogg', tmp_path/'first', user_confirmed=True)
    final = json.loads(open(result['checkpoint'], encoding='utf-8').read())
    assert source.read_bytes() == raw
    assert final['items'][0]['result'] == data
    assert final['items'][0]['classification']['clasificacion'] == 'APROBADO'
    assert final['items'][0].get('audio_block_evidence') is None
    assert not final['recado_confirmation_import']['whisper_executed']
    again = reanalyze_checkpoint(result['checkpoint'], tmp_path/'again')
    repeated = json.loads(open(again['checkpoint'], encoding='utf-8').read())
    assert repeated['items'][0]['classification']['clasificacion'] == 'APROBADO'
    assert final['items'][0]['recado_acceptance_confirmation'] == repeated['items'][0]['recado_acceptance_confirmation']


def test_wrong_file_or_missing_confirmation_cannot_write_outputs(tmp_path):
    data, relation = fixture(); source = tmp_path/'original.json'
    source.write_text(json.dumps({'items': [{'file_name': 'sample.ogg', 'result': data, 'relation': relation}]}))
    for name, flag in [('other.ogg', True), ('sample.ogg', False)]:
        with pytest.raises(ValueError):
            confirm_checkpoint_recado(source, name, tmp_path/'output', user_confirmed=flag)
    assert not (tmp_path/'output').exists()


def test_cli_explicit_confirmation_produces_a_new_final_checkpoint(tmp_path, monkeypatch):
    from tools import confirm_recado_acceptance as cli
    import sys
    data, relation = fixture(); source = tmp_path/'original.json'
    source.write_text(json.dumps({'items': [{'file_name': 'sample.ogg', 'result': data, 'relation': relation}]}))
    monkeypatch.setattr(sys, 'argv', ['confirm', '--checkpoint', str(source), '--call', '1',
                                    '--confirm-acceptance', '--output-dir', str(tmp_path/'out')])
    assert cli.main() == 0
    assert (tmp_path/'out/resultados/checkpoint_reanalizado.json').is_file()


def test_cli_cancel_never_registers_a_fact(tmp_path, monkeypatch):
    from tools import confirm_recado_acceptance as cli
    from types import SimpleNamespace
    import sys
    data, relation = fixture(); source = tmp_path/'original.json'
    source.write_text(json.dumps({'items': [{'file_name': 'sample.ogg', 'result': data, 'relation': relation}]}))
    destroyed = []
    class Root:
        def withdraw(self): pass
        def destroy(self): destroyed.append(True)
    monkeypatch.setitem(sys.modules, 'tkinter', SimpleNamespace(
        Tk=Root, filedialog=None, simpledialog=None,
        messagebox=SimpleNamespace(NO='no', askyesno=lambda *a, **k: False)))
    monkeypatch.setattr(sys, 'argv', ['confirm', '--checkpoint', str(source), '--call', '1',
                                    '--output-dir', str(tmp_path/'out')])
    assert cli.main() == 0 and destroyed == [True]
    assert not (tmp_path/'out').exists()
