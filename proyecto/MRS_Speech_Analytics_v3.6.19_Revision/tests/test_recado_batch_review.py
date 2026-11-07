"""Varias confirmaciones, una transacción y una sola evaluación del lote."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import time

from openpyxl import load_workbook
import pytest

from app.services.checkpoint_recado_batch_review import prepare_recado_selections, confirm_checkpoint_recados
from app.services.recado_acceptance_review import SCOPE, DELIVERY_SCOPE, make_recado_confirmation

TEXT = 'Habla MRS. Es mi hermana. Le dejo un mensaje. Que se comunique con nosotros.'
DESCRIPTION = 'Número para que la titular negocie el restante.'


def fixture(tmp_path, *, problem=''):
    items = []
    for n in range(1, 5):
        text = TEXT if n < 4 else 'Habla MRS. Es mi esposa. Ya hicimos un pago. Ingreso la información.'
        if n == 4:
            text += problem
        items.append({'file_name': f'sample_{n}.ogg', 'result': {'archivo': f'sample_{n}.ogg',
            'texto': text, 'segmentos': [], 'duracion_segundos': 120},
            'relation': {'numero_de_tarjeta': f'123456789012{n:04d}', 'asignacion': '1PV',
                         'estatus_grabacion': 'MENSAJE CON FAMILIAR', 'nombre_final': f'salida_{n}'},
            'classification': {'puntaje_minimo': 80}})
    i = items[3]; i['recado_acceptance_confirmation'] = make_recado_confirmation(i['result'], i['relation'], user_confirmed=True)
    source = tmp_path/'input.json'; payload = {'completed': True, 'items': items}
    source.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8-sig')
    return source, payload


def selections(items):
    return prepare_recado_selections(items, '1, 2, 3', '4 | '+DESCRIPTION,
        acceptances_confirmed=True, messages_confirmed=True, callbacks_confirmed=True)


def test_multiple_scopes_reanalyze_exactly_once_and_keep_the_source(tmp_path, monkeypatch):
    from app.services import checkpoint_reanalysis
    source, payload = fixture(tmp_path); raw = source.read_bytes(); calls = []
    real = checkpoint_reanalysis.reanalyze_checkpoint
    def counted(*args, **kwargs):
        calls.append(True); return real(*args, **kwargs)
    monkeypatch.setattr(checkpoint_reanalysis, 'reanalyze_checkpoint', counted)
    result = confirm_checkpoint_recados(source, selections(payload['items']), tmp_path/'out',
        expected_source_sha256=hashlib.sha256(raw).hexdigest())
    assert calls == [True] and result['confirmed_calls'] == 4 and result['outcomes'] == {'APROBADO': 4}
    assert source.read_bytes() == raw
    final = json.loads(Path(result['checkpoint']).read_text(encoding='utf-8'))
    assert final['completed'] and final['recado_review_stage'] == 'FINAL_REANALYZED'
    intermediate = json.loads((tmp_path/'out/auditoria/entrada.json').read_text(encoding='utf-8'))
    assert not intermediate['completed'] and intermediate['recado_review_stage'] == 'INTERMEDIATE_NOT_REANALYZED'
    assert not list((tmp_path/'out').glob('*.json'))
    for before, after in zip(payload['items'], final['items']):
        assert before['result'] == after['result'] and before['relation'] == after['relation']
    assert len(final['items'][3]['recado_acceptance_confirmation_history']) == 1
    assert final['items'][3]['recado_acceptance_confirmation']['scope'] == DELIVERY_SCOPE
    assert final['items'][0]['recado_acceptance_confirmation']['scope'] == SCOPE
    book = load_workbook(result['report'], read_only=True, data_only=True)
    assert book['RECADOS_CONFIRMADOS'].max_row == 5 and book['RESULTADOS'].max_row == 5
    book.close()


@pytest.mark.parametrize('accepted,delivered,flags', [
    ('1,2', '', (False, False, False)),
    ('', '4 | '+DESCRIPTION, (False, True, False)),
    ('', '4 | '+DESCRIPTION, (False, False, True)),
    ('1,1', '', (True, False, False)),
    ('1', '1 | '+DESCRIPTION, (True, True, True)),
    ('0', '', (True, False, False)), ('5', '', (True, False, False)),
    ('1-3', '', (True, False, False)), ('1,foo', '', (True, False, False)),
    ('', '4 sin separador', (False, True, True)),
    ('', '4 | abc', (False, True, True)), ('', '', (True, True, True)),
])
def test_invalid_or_unconfirmed_selection_is_rejected_before_writing(tmp_path, accepted, delivered, flags):
    _, payload = fixture(tmp_path)
    with pytest.raises(ValueError):
        prepare_recado_selections(payload['items'], accepted, delivered,
            acceptances_confirmed=flags[0], messages_confirmed=flags[1], callbacks_confirmed=flags[2])
    assert not (tmp_path/'out').exists()


def test_one_bad_fact_in_a_batch_creates_no_partial_output(tmp_path):
    source, payload = fixture(tmp_path); chosen = selections(payload['items'])
    chosen['sample_4.ogg']['callback_confirmed'] = False
    with pytest.raises(ValueError):
        confirm_checkpoint_recados(source, chosen, tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_source_changed_after_preview_cannot_be_used(tmp_path):
    source, payload = fixture(tmp_path); sha = hashlib.sha256(source.read_bytes()).hexdigest()
    source.write_bytes(source.read_bytes()+b' ')
    with pytest.raises(ValueError, match='cambió'):
        confirm_checkpoint_recados(source, selections(payload['items']), tmp_path/'out', expected_source_sha256=sha)
    assert not (tmp_path/'out').exists()


def test_unselected_existing_proofs_and_history_survive_and_repeating_is_idempotent(tmp_path):
    source, payload = fixture(tmp_path); chosen = selections(payload['items'])
    first = confirm_checkpoint_recados(source, chosen, tmp_path/'first')
    a = json.loads(Path(first['checkpoint']).read_text(encoding='utf-8'))
    second = confirm_checkpoint_recados(first['checkpoint'], chosen, tmp_path/'second')
    b = json.loads(Path(second['checkpoint']).read_text(encoding='utf-8'))
    for x, y in zip(a['items'], b['items']):
        assert x['classification'] == y['classification']
        assert x['recado_acceptance_confirmation'] == y['recado_acceptance_confirmation']
        assert x.get('recado_acceptance_confirmation_history') == y.get('recado_acceptance_confirmation_history')
    assert len(b['recado_batch_confirmation_import_history']) == 1
    one = {'sample_1.ogg': chosen['sample_1.ogg']}
    third = confirm_checkpoint_recados(first['checkpoint'], one, tmp_path/'third')
    c = json.loads(Path(third['checkpoint']).read_text(encoding='utf-8'))
    for index in (1, 2, 3):
        assert a['items'][index]['recado_acceptance_confirmation'] == c['items'][index]['recado_acceptance_confirmation']


@pytest.mark.parametrize('problem', [' Gestor: Tiene una deuda de 500 pesos.',
    ' Me trataron mal.', ' No le voy a pasar el recado.', ' La tarjeta termina en 9999.'])
def test_batch_does_not_force_approval_or_waive_other_controls(tmp_path, problem):
    source, payload = fixture(tmp_path, problem=problem)
    result = confirm_checkpoint_recados(source, selections(payload['items']), tmp_path/'out')
    data = json.loads(Path(result['checkpoint']).read_text(encoding='utf-8'))
    assert not data['items'][3]['classification']['aprobado']
    assert all(i['classification']['aprobado'] for i in data['items'][:3])


def test_cli_multiple_calls_creates_one_final_pair(tmp_path, monkeypatch):
    import sys
    from tools import confirm_recados_batch as cli
    source, _ = fixture(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['batch', '--checkpoint', str(source), '--accepted-calls', '1,2,3',
        '--delivered-call', '4 | '+DESCRIPTION, '--confirm-acceptances', '--confirm-messages',
        '--confirm-callbacks', '--output-dir', str(tmp_path/'out')])
    assert cli.main() == 0
    assert (tmp_path/'out/resultados/checkpoint_reanalizado.json').is_file()
    assert (tmp_path/'out/resultados/04_Reportes/Reporte_Reanalisis_Reglas.xlsx').is_file()


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Requiere pantalla Tk de pruebas.')
def test_real_gui_has_blank_defaults_previews_multiple_files_and_saves_without_blocking(tmp_path):
    import tkinter as tk
    from tools.confirm_recados_batch import RecadoBatchWindow
    source, payload = fixture(tmp_path); root = tk.Tk(); root.withdraw()
    window = RecadoBatchWindow(root, source, payload, hashlib.sha256(source.read_bytes()).hexdigest(), tmp_path/'out')
    try:
        root.update()
        assert root.winfo_viewable() and not window.accepted.get()
        assert not window.accepted_ok.get() and not window.message_ok.get() and not window.callback_ok.get()
        window.accepted.set('1,2,3'); window.delivered.insert('1.0', '4 | '+DESCRIPTION)
        window.preview()
        assert window.prepared is None and not (tmp_path/'out').exists()
        window.accepted_ok.set(True); window.message_ok.set(True); window.callback_ok.set(True)
        window.preview(); root.update()
        assert len(window.tree.get_children()) == 4 and len(window.prepared) == 4
        assert window.save_button.winfo_rooty()+window.save_button.winfo_height() <= root.winfo_rooty()+root.winfo_height()
        window.save(); assert window.busy
        deadline = time.monotonic()+30
        while window.busy and time.monotonic() < deadline:
            root.update(); time.sleep(.01)
        assert not window.busy and window.result['outcomes'] == {'APROBADO': 4}
        assert 'checkpoint_reanalizado.json' in window.status.get()
        assert Path(window.result['report']).is_file()
    finally:
        if getattr(window, 'worker', None):
            window.worker.join(timeout=30)
        root.destroy()


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Requiere pantalla Tk de pruebas.')
def test_real_gui_requires_a_new_preview_after_edits_and_cancel_writes_nothing(tmp_path):
    import tkinter as tk
    from tools.confirm_recados_batch import RecadoBatchWindow
    source, payload = fixture(tmp_path); root = tk.Tk()
    window = RecadoBatchWindow(root, source, payload, hashlib.sha256(source.read_bytes()).hexdigest(), tmp_path/'out')
    window.accepted.set('1'); window.accepted_ok.set(True); window.preview()
    window.accepted.set('2'); window.save()
    assert not window.busy and not (tmp_path/'out').exists()
    window.close()
