"""Una confirmación concreta de divulgación activa PEN003 sin reescribir ASR."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.audio_block_evidence import binding, record_digest
from app.services.checkpoint_privacy_review import confirm_checkpoint_disclosure
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.family_contact_review import make_family_confirmation
from app.services.privacy_disclosure_review import (
    disclosure_candidates, make_disclosure_confirmation, validate_disclosure_confirmation,
)

BASE = 'Habla MRS. Soy su madre. Dígale que se comunique. Le paso el recado.'
FINANCE = 'Tiene un saldo vencido de 500 pesos.'


def fixture(additional=False):
    text = BASE if additional else BASE+' '+FINANCE
    data = {'archivo': 'sample.ogg', 'texto': text, 'segmentos': [], 'duracion_segundos': 120}
    relation = {'numero_de_tarjeta': '1234567890123456', 'estatus_grabacion': 'MENSAJE CON FAMILIAR', 'asignacion': '1PV'}
    reading = None
    if additional:
        reading = {'schema': 1, 'kind': 'AUTOMATED_ASR_ONLY', 'binding': binding(data, relation),
            'source_checkpoint_sha256': 'a'*64, 'receipt_sha256': 'b'*64, 'audio_sha256': 'c'*64,
            'model': 'small', 'human_verified': False, 'speaker_roles_confirmed': False,
            'text': FINANCE, 'segments': [{'text': FINANCE, 'start': 20, 'end': 25}],
            'tail_text': '', 'tail_segments': []}
        reading['record_sha256'] = record_digest(reading)
    return data, relation, reading


def record(data, relation, reading=None):
    candidate = disclosure_candidates(data, relation, reading)[0]
    return make_disclosure_confirmation(data, relation, candidate,
        actor_confirmed=True, third_party_confirmed=True, audio_evidence=reading)


def analyze(data, relation, confirmation=None, reading=None):
    t = TranscriptionModel.from_dict(data)
    t.metadata.update(privacy_disclosure_confirmation=confirmation, audio_block_evidence=reading)
    return A.analyze_transcription(t, relation)


@pytest.mark.parametrize('additional', [False, True])
def test_confirmed_gestor_to_third_party_is_critical_preserving_raw_asr(additional):
    data, relation, reading = fixture(additional)
    original, raw_reading = deepcopy(data), deepcopy(reading)
    before = analyze(data, relation, reading=reading)
    assert before.metadata['final_result'] == 'REVISAR'
    assert 'PEN003' not in {p['id'] for p in before.metadata['penalties']}
    confirmation = record(data, relation, reading)
    after = analyze(data, relation, confirmation, reading)
    assert after.metadata['final_result'] == 'FALLA_GRAVE'
    assert after.metadata['privacy_validation']['confirmed_disclosure']
    penalty = next(p for p in after.metadata['penalties'] if p['id'] == 'PEN003')
    assert penalty['points'] == 100 and penalty['invalidates']
    assert 'Confirmado por usuario' in penalty['reason']
    assert after.metadata['privacy_disclosure_validation']['valid']
    assert data == original and reading == raw_reading
    assert not confirmation.get('audio_verified')
    if reading:
        assert not reading['human_verified'] and not reading['speaker_roles_confirmed']
    assert len([e for e in after.metadata['privacy_validation']['evidence'] if e.get('attribution_source')]) == 1


@pytest.mark.parametrize('actor,third', [(False, True), (True, False), (False, False), (1, True), (True, 1)])
def test_both_confirmations_must_be_explicit(actor, third):
    data, relation, reading = fixture()
    with pytest.raises(ValueError, match='explícitamente'):
        make_disclosure_confirmation(data, relation, disclosure_candidates(data, relation)[0],
                                    actor_confirmed=actor, third_party_confirmed=third)


@pytest.mark.parametrize('field,value', [('archivo', 'other.ogg'), ('texto', BASE),
    ('duracion_segundos', 121), ('segmentos', [{'text': FINANCE}])])
def test_changed_call_invalidates_fact_and_does_not_create_critical_penalty(field, value):
    data, relation, reading = fixture()
    confirmation = record(data, relation)
    data[field] = value
    assert not validate_disclosure_confirmation(data, relation, confirmation)['valid']
    a = analyze(data, relation, confirmation)
    assert a.metadata['final_result'] == 'REVISAR'
    assert 'PEN003' not in {p['id'] for p in a.metadata['penalties']}


@pytest.mark.parametrize('field,value', [('numero_de_tarjeta', '1234567890123999'), ('asignacion', '2PV')])
def test_changed_account_cannot_reuse_fact(field, value):
    data, relation, _ = fixture(); confirmation = record(data, relation)
    relation[field] = value
    assert not validate_disclosure_confirmation(data, relation, confirmation)['valid']


def test_corrected_output_name_preserves_fact():
    data, relation, _ = fixture(); confirmation = record(data, relation)
    relation['nombre_final'] = 'corrected_output'
    assert validate_disclosure_confirmation(data, relation, confirmation)['valid']


@pytest.mark.parametrize('field,value', [('scope', 'ALL_QUALITY_RULES'), ('actor', 'TITULAR'),
    ('recipient', 'TITULAR'), ('actor_confirmed', False), ('third_party_confirmed', False),
    ('active', False), ('record_sha256', 'x'), ('source_binding', 'x'), ('source', 'AUTOMATED_ASR')])
def test_tampering_or_revocation_is_review_and_not_a_false_PEN003(field, value):
    data, relation, _ = fixture(); confirmation = record(data, relation)
    confirmation[field] = value
    a = analyze(data, relation, confirmation)
    assert a.metadata['privacy_disclosure_validation']['review_required']
    assert a.metadata['final_result'] == 'REVISAR'
    assert 'PEN003' not in {p['id'] for p in a.metadata['penalties']}


@pytest.mark.parametrize('text', [BASE, '¿Tiene un saldo vencido de 500 pesos?',
    'No tiene un saldo vencido de 500 pesos.', 'Si tuviera un saldo vencido de 500 pesos.',
    'Titular: '+FINANCE, 'Tercero: '+FINANCE])
def test_cannot_confirm_generic_words_questions_negations_or_other_known_speaker(text):
    data, relation, _ = fixture(); data['texto'] = text
    assert not disclosure_candidates(data, relation)


def test_fabricated_quote_or_time_cannot_be_registered():
    data, relation, _ = fixture()
    candidate = disclosure_candidates(data, relation)[0]
    for key, value in [('text', 'Tiene una deuda de 999 pesos.'), ('start', 123), ('source', 'OTHER')]:
        changed = dict(candidate, **{key: value})
        with pytest.raises(ValueError, match='fragmento financiero'):
            make_disclosure_confirmation(data, relation, changed, actor_confirmed=True, third_party_confirmed=True)


@pytest.mark.parametrize('change', ['remove', 'tamper', 'replace'])
def test_changed_additional_reading_invalidates_its_fact(change):
    data, relation, reading = fixture(True); confirmation = record(data, relation, reading)
    if change == 'remove': reading = None
    elif change == 'tamper': reading['text'] += ' Otro texto.'
    else:
        reading['audio_sha256'] = 'd'*64
        reading['record_sha256'] = record_digest(reading)
    assert not validate_disclosure_confirmation(data, relation, confirmation, reading)['valid']
    assert analyze(data, relation, confirmation, reading).metadata['final_result'] == 'REVISAR'


def test_confirmed_privacy_is_not_waived_by_hostility_exception():
    data, relation, _ = fixture(); t = TranscriptionModel.from_dict(data)
    t.metadata['privacy_disclosure_confirmation'] = record(data, relation)
    t.metadata['hostile_interlocutor_exception'] = dict.fromkeys(
        ['audio_verified', 'interlocutor_hostile_or_lascivious', 'prevented_script', 'agent_professional'], True)
    assert A.analyze_transcription(t, relation).metadata['final_result'] == 'FALLA_GRAVE'


@pytest.mark.parametrize('phrase', ['Tiene una deuda.'])
def test_other_financial_disclosure_without_amount_still_requires_confirmed_roles(phrase):
    data, relation, _ = fixture()
    data['texto'] = BASE+' '+phrase
    before = analyze(data, relation)
    assert before.metadata['privacy_validation']['review_required']
    assert 'PEN003' not in {p['id'] for p in before.metadata['penalties']}
    confirmed = record(data, relation)
    after = analyze(data, relation, confirmed)
    assert after.metadata['privacy_validation']['confirmed_disclosure']
    assert after.metadata['final_result'] == 'FALLA_GRAVE'


@pytest.mark.parametrize('phrase', ['Tiene un saldo pendiente.', 'Tiene un saldo vencido.', 'Es referente al saldo pendiente de su tarjeta.'])
def test_user_policy_allows_generic_pending_balance_without_amount(phrase):
    data, relation, _ = fixture()
    data['texto'] = BASE+' '+phrase
    before = analyze(data, relation)
    assert not before.metadata['privacy_validation']['review_required']
    assert not before.metadata['privacy_validation']['confirmed_disclosure']
    assert before.metadata['privacy_validation']['allowed_generic_balance_mentions']
    assert not disclosure_candidates(data, relation)


def test_checkpoint_roundtrip_idempotence_and_other_call_preservation(tmp_path):
    data, relation, reading = fixture(True)
    second = {'archivo': 'other.ogg', 'texto': BASE, 'duracion_segundos': 120, 'segmentos': []}
    family = make_family_confirmation(second, relation, 'MADRE', user_confirmed=True)
    payload = {'items': [
        {'file_name': 'sample.ogg', 'result': data, 'relation': relation, 'audio_block_evidence': reading},
        {'file_name': 'other.ogg', 'result': second, 'relation': relation, 'family_contact_confirmation': family,
         'output_name_review': {'retained': True}, 'mora_excel_import': {'retained': True}}]}
    source = tmp_path/'source.json'; source.write_text(json.dumps(payload), encoding='utf-8')
    raw = source.read_bytes(); evidence = disclosure_candidates(data, relation, reading)[0]
    result = confirm_checkpoint_disclosure(source, 'sample.ogg', evidence, tmp_path/'out',
        actor_confirmed=True, third_party_confirmed=True)
    final = json.loads(Path(result['checkpoint']).read_text())
    assert result['outcomes'] == {'FALLA_GRAVE': 1, 'APROBADO': 1}
    assert source.read_bytes() == raw
    for old, new in zip(payload['items'], final['items']):
        for key in old:
            assert old[key] == new[key]
    assert not final['reanalysis']['whisper_executed'] and not final['reanalysis']['audio_files_copied']
    again = reanalyze_checkpoint(result['checkpoint'], tmp_path/'again')
    updated = json.loads(Path(again['checkpoint']).read_text())
    assert updated['items'][0]['privacy_disclosure_confirmation'] == final['items'][0]['privacy_disclosure_confirmation']
    assert updated['items'][0]['classification']['clasificacion'] == 'FALLA_GRAVE'
    repeat = confirm_checkpoint_disclosure(result['checkpoint'], 'sample.ogg', evidence, tmp_path/'repeat',
        actor_confirmed=True, third_party_confirmed=True)
    repeated = json.loads(Path(repeat['checkpoint']).read_text())
    assert repeated['items'][0]['privacy_disclosure_confirmation'] == final['items'][0]['privacy_disclosure_confirmation']
    assert not repeated['items'][0].get('privacy_disclosure_history')
    book = load_workbook(result['report'], read_only=True, data_only=True)
    rows = list(book['RESULTADOS'].values)
    assert 'PEN003' in str(rows[1]) and 'Confirmado por usuario' in str(rows[1])
    book.close()


def test_invalid_confirmation_does_not_create_output(tmp_path):
    data, relation, _ = fixture()
    source = tmp_path/'source.json'
    source.write_text(json.dumps({'items': [{'file_name': 'sample.ogg', 'result': data, 'relation': relation}]}))
    with pytest.raises(ValueError, match='explícitamente'):
        confirm_checkpoint_disclosure(source, 'sample.ogg', disclosure_candidates(data, relation)[0], tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('number', [0, 2])
def test_cli_rejects_out_of_range_call_without_creating_outputs(tmp_path, monkeypatch, number):
    import sys
    from tools import confirm_privacy_disclosure as cli
    data, relation, _ = fixture()
    source = tmp_path/'source.json'
    source.write_text(json.dumps({'items': [{'file_name': 'sample.ogg', 'result': data, 'relation': relation}]}))
    monkeypatch.setattr(sys, 'argv', ['confirm', '--checkpoint', str(source), '--call', str(number),
        '--candidate', '1', '--confirm-gestor', '--confirm-tercero', '--output-dir', str(tmp_path/'out')])
    assert cli.main() == 1
    assert not (tmp_path/'out').exists()


def test_cli_file_selection_keeps_current_checkpoint_and_records_selected_fact(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from tools import confirm_privacy_disclosure as cli
    data, relation, _ = fixture()
    source = tmp_path/'source.json'
    source.write_text(json.dumps({'items': [{'file_name': 'sample.ogg', 'result': data, 'relation': relation}]}))
    destroyed, labels = [], []
    class Root:
        def withdraw(self): pass
        def destroy(self): destroyed.append(True)
    monkeypatch.setitem(sys.modules, 'tkinter', SimpleNamespace(Tk=Root,
        filedialog=SimpleNamespace(askopenfilename=lambda **kwargs: str(source)),
        simpledialog=SimpleNamespace(askinteger=lambda *args, **kwargs: 1)))
    def choose(root, candidates, call_label):
        labels.append(call_label)
        assert candidates[0]['text'] == FINANCE
        return 0
    monkeypatch.setattr(cli, 'choose_confirmation', choose)
    monkeypatch.setattr(sys, 'argv', ['confirm', '--output-dir', str(tmp_path/'out')])
    assert cli.main() == 0
    assert destroyed == [True] and labels == ['Llamada 1: sample.ogg']
    final = json.loads((tmp_path/'out/resultados/checkpoint_reanalizado.json').read_text())
    assert final['items'][0]['classification']['clasificacion'] == 'FALLA_GRAVE'


def test_cancelled_selection_does_not_record_a_fact(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from tools import confirm_privacy_disclosure as cli
    class Root:
        def withdraw(self): pass
        def destroy(self): pass
    monkeypatch.setitem(sys.modules, 'tkinter', SimpleNamespace(Tk=Root,
        filedialog=SimpleNamespace(askopenfilename=lambda **kwargs: ''), simpledialog=SimpleNamespace()))
    monkeypatch.setattr(sys, 'argv', ['confirm', '--output-dir', str(tmp_path/'out')])
    assert cli.main() == 0 and not (tmp_path/'out').exists()
