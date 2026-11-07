"""Entrega humana de recado y contacto: dos hechos ligados al contexto original."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.recado_acceptance_review import (
    make_recado_confirmation, make_recado_delivery_confirmation,
    validate_recado_confirmation, confirm_checkpoint_recado, DELIVERY_SCOPE)

TEXT = ('Habla MRS. No se encuentra. Es mi esposa. '
        'Estamos tratando de contactarla para llegar a una negociación. '
        'Ya hicimos un pago. Ingreso la información, buen día.')
DESCRIPTION = 'Número para que la titular negocie el restante.'


def fixture(text=TEXT):
    return ({'archivo': 'sample.ogg', 'texto': text, 'segmentos': [], 'duracion_segundos': 120},
            {'estatus_grabacion': 'MENSAJE CON FAMILIAR', 'numero_de_tarjeta': '1234567890123456',
             'asignacion': '1PV', 'nombre_final': 'salida'})


def proof(data, relation):
    return make_recado_delivery_confirmation(data, relation, DESCRIPTION,
        message_confirmed=True, callback_confirmed=True)


def analyze(data, relation, record=None):
    t = TranscriptionModel.from_dict(data)
    t.metadata['recado_acceptance_confirmation'] = record
    return A.analyze_transcription(t, relation)


def test_delivery_is_a_separate_user_fact_not_an_asr_or_acceptance_rewrite():
    data, relation = fixture(); raw = deepcopy(data)
    assert analyze(data, relation).metadata['final_result'] == 'REVISAR'
    record = proof(data, relation); result = analyze(data, relation, record)
    assert result.metadata['final_result'] == 'APROBADO' and result.compliance_score == 100
    status = result.metadata['recado_acceptance_validation']
    assert status['valid'] and status['message_delivered'] and status['callback_delivered']
    assert not status['recipient_accepted']
    assert not record.get('audio_verified') and not record.get('speaker_roles_confirmed')
    assert data == raw and not result.metadata['privacy_validation']['confirmed_disclosure']
    evidence = result.metadata['status_validation']['recado_evidence']
    assert evidence['confirmed_recado'] and evidence['callback_information']
    assert evidence['evidence']['message'][0]['text'] == DESCRIPTION


@pytest.mark.parametrize('message,callback', [(False, True), (True, False), (False, False),
    (1, True), (True, 1), (None, True)])
def test_both_explicit_facts_are_required(message, callback):
    data, relation = fixture()
    with pytest.raises(ValueError, match='separado'):
        make_recado_delivery_confirmation(data, relation, DESCRIPTION,
            message_confirmed=message, callback_confirmed=callback)


@pytest.mark.parametrize('description', [None, '', 'abc', 'x'*501, 123])
def test_a_description_is_required_without_inventing_one(description):
    data, relation = fixture()
    with pytest.raises(ValueError, match='Describa'):
        make_recado_delivery_confirmation(data, relation, description,
            message_confirmed=True, callback_confirmed=True)


@pytest.mark.parametrize('field,value', [('archivo', 'other.ogg'), ('texto', TEXT+' Otra frase.'),
    ('duracion_segundos', 121), ('segmentos', [{'text': TEXT}])])
def test_changed_source_cannot_reuse_delivery(field, value):
    data, relation = fixture(); record = proof(data, relation); data[field] = value
    assert not validate_recado_confirmation(data, relation, record)['valid']
    assert not analyze(data, relation, record).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('field,value', [('numero_de_tarjeta', '1234567890123999'), ('asignacion', '2PV')])
def test_changed_account_cannot_reuse_delivery(field, value):
    data, relation = fixture(); record = proof(data, relation); relation[field] = value
    assert not validate_recado_confirmation(data, relation, record)['valid']


@pytest.mark.parametrize('field,value', [('active', False), ('scope', 'APPROVE_ALL'),
    ('message_description', 'Otro recado.'), ('message_confirmed', False),
    ('callback_confirmed', False), ('user_confirmed', False), ('record_sha256', 'x')])
def test_tampered_or_revoked_record_blocks_approval(field, value):
    data, relation = fixture(); record = proof(data, relation); record[field] = value
    assert analyze(data, relation, record).metadata['final_result'] == 'REVISAR'


@pytest.mark.parametrize('problem', [
    'No le voy a pasar el recado.', 'No lo conozco.', 'Me trataron mal.',
    'Tiene una deuda de 500 pesos.', 'Gestor: Tiene una deuda de 500 pesos.',
    'La tarjeta termina en 9999.', 'Gestor: Vamos a realizar una visita a su domicilio.',
    'Gestor: Qué poca madre.',
])
def test_delivered_recado_does_not_waive_other_quality_rules(problem):
    data, relation = fixture(TEXT+' '+problem)
    assert not analyze(data, relation, proof(data, relation)).metadata['shared_classification']['aprobado']


def test_delivered_recado_does_not_invent_family_from_excel():
    data, relation = fixture(TEXT.replace('Es mi esposa. ', ''))
    assert not analyze(data, relation, proof(data, relation)).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('description', ['Su saldo es 500 pesos.', 'Debe 500 pesos.',
    'Su tarjeta 1234567890123456.', 'Tiene tres mensualidades vencidas.'])
def test_financial_information_in_the_human_description_cannot_be_approved_as_a_generic_message(description):
    data, relation = fixture()
    record = make_recado_delivery_confirmation(data, relation, description,
        message_confirmed=True, callback_confirmed=True)
    result = analyze(data, relation, record)
    assert result.metadata['recado_acceptance_validation']['review_required']
    assert result.metadata['final_result'] == 'REVISAR'
    assert not result.metadata['privacy_validation']['confirmed_disclosure']
    assert not any(p['id'] == 'PEN003' for p in result.metadata['penalties'])


def test_generic_balance_without_amount_in_description_keeps_the_users_allowed_policy():
    data, relation = fixture()
    record = make_recado_delivery_confirmation(data, relation,
        'Número para comunicarse por un saldo pendiente.', message_confirmed=True, callback_confirmed=True)
    assert analyze(data, relation, record).metadata['final_result'] == 'APROBADO'


def test_acceptance_only_still_cannot_invent_missing_callback():
    data, relation = fixture()
    record = make_recado_confirmation(data, relation, user_confirmed=True)
    assert not analyze(data, relation, record).metadata['shared_classification']['aprobado']


def test_name_change_preserves_identity_and_old_acceptance_proofs_still_work():
    data, relation = fixture(); delivery = proof(data, relation)
    acceptance = make_recado_confirmation(data, relation, user_confirmed=True)
    relation['nombre_final'] = 'nombre corregido'
    assert validate_recado_confirmation(data, relation, delivery)['valid']
    assert validate_recado_confirmation(data, relation, acceptance)['valid']


def write_master(tmp_path):
    data, relation = fixture(); source = tmp_path/'original.json'
    source.write_text(json.dumps({'items': [{'file_name': 'sample.ogg', 'result': data,
        'relation': relation, 'classification': {'puntaje_minimo': 80}}]}), encoding='utf-8')
    return source


def test_checkpoint_roundtrip_preserves_full_fact_and_does_not_touch_the_input(tmp_path):
    source = write_master(tmp_path); raw = source.read_bytes()
    first = confirm_checkpoint_recado(source, 'sample.ogg', tmp_path/'first',
        message_description=DESCRIPTION, message_confirmed=True, callback_confirmed=True)
    payload = json.loads(Path(first['checkpoint']).read_text(encoding='utf-8'))
    assert source.read_bytes() == raw and payload['items'][0]['classification']['aprobado']
    assert payload['recado_confirmation_import']['scope'] == DELIVERY_SCOPE
    again = reanalyze_checkpoint(first['checkpoint'], tmp_path/'again')
    repeated = json.loads(Path(again['checkpoint']).read_text(encoding='utf-8'))
    assert repeated['items'][0]['classification']['aprobado']
    assert payload['items'][0]['recado_acceptance_confirmation'] == repeated['items'][0]['recado_acceptance_confirmation']


def test_upgrading_an_acceptance_preserves_history_and_repeating_delivery_is_idempotent(tmp_path):
    source = write_master(tmp_path)
    acceptance = confirm_checkpoint_recado(source, 'sample.ogg', tmp_path/'acceptance', user_confirmed=True)
    first = confirm_checkpoint_recado(acceptance['checkpoint'], 'sample.ogg', tmp_path/'first',
        message_description=DESCRIPTION, message_confirmed=True, callback_confirmed=True)
    a = json.loads(Path(first['checkpoint']).read_text(encoding='utf-8'))
    assert len(a['items'][0]['recado_acceptance_confirmation_history']) == 1
    second = confirm_checkpoint_recado(first['checkpoint'], 'sample.ogg', tmp_path/'second',
        message_description=DESCRIPTION, message_confirmed=True, callback_confirmed=True)
    b = json.loads(Path(second['checkpoint']).read_text(encoding='utf-8'))
    assert a['items'][0]['recado_acceptance_confirmation'] == b['items'][0]['recado_acceptance_confirmation']
    assert a['items'][0]['recado_acceptance_confirmation_history'] == b['items'][0]['recado_acceptance_confirmation_history']


def test_cli_delivery_mode_is_explicit_and_noninteractive_with_complete_flags(tmp_path, monkeypatch):
    from tools import confirm_recado_acceptance as cli
    source = write_master(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['confirm', '--checkpoint', str(source), '--call', '1',
        '--delivered-recado', '--description', DESCRIPTION, '--confirm-message', '--confirm-callback',
        '--output-dir', str(tmp_path/'out')])
    assert cli.main() == 0
    payload = json.loads((tmp_path/'out/resultados/checkpoint_reanalizado.json').read_text(encoding='utf-8'))
    assert payload['items'][0]['classification']['aprobado']


@pytest.mark.parametrize('flags', [['--description', DESCRIPTION],
    ['--confirm-callback'], ['--delivered-recado', '--confirm-acceptance']])
def test_cli_does_not_mix_confirmation_scopes(monkeypatch, flags):
    from tools import confirm_recado_acceptance as cli
    monkeypatch.setattr(sys, 'argv', ['confirm']+flags)
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2


@pytest.mark.parametrize('cancel_at', ['message', 'callback', 'description'])
def test_gui_cancel_at_each_fact_or_description_creates_no_output(tmp_path, monkeypatch, cancel_at):
    from types import SimpleNamespace
    from tools import confirm_recado_acceptance as cli
    source = write_master(tmp_path); destroyed = []
    answers = iter([False] if cancel_at == 'message' else
                   [True, False] if cancel_at == 'callback' else [True, True])
    class Root:
        def withdraw(self): pass
        def destroy(self): destroyed.append(True)
    def ask(*args, **kwargs):
        assert kwargs['default'] == 'no'
        assert 'sample.ogg' in args[1]
        return next(answers)
    monkeypatch.setitem(sys.modules, 'tkinter', SimpleNamespace(Tk=Root, filedialog=None,
        simpledialog=SimpleNamespace(askstring=lambda *a, **k: None),
        messagebox=SimpleNamespace(NO='no', askyesno=ask)))
    monkeypatch.setattr(sys, 'argv', ['confirm', '--checkpoint', str(source), '--call', '1',
        '--delivered-recado', '--output-dir', str(tmp_path/'out')])
    assert cli.main() == 0 and destroyed == [True]
    assert not (tmp_path/'out').exists()
