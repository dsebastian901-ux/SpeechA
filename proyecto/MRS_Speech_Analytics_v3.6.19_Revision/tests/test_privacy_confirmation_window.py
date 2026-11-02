"""Interacción real de Tk: el diálogo debe verse aunque su raíz esté oculta."""
import os
import json
import sys

import pytest

from tools.confirm_privacy_disclosure import choose_confirmation

pytestmark = pytest.mark.skipif(
    sys.platform != 'win32' and not os.environ.get('DISPLAY'),
    reason='Necesita una pantalla Tk real (DISPLAY o Windows).',
)


def widgets(widget):
    for child in widget.winfo_children():
        yield child
        yield from widgets(child)


@pytest.mark.parametrize('visible_parent', [False, True])
def test_visible_window_requires_explicit_fragment_and_two_facts(visible_parent):
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    if not visible_parent:
        root.withdraw()
    else:
        root.update()
    checks, problems = [], []
    def interact():
        dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
        try:
            assert dialog.winfo_viewable(), 'La confirmación quedó oculta.'
            assert root.grab_current() == dialog
            assert bool(root.winfo_viewable()) is visible_parent
            all_widgets = list(widgets(dialog))
            listing = next(w for w in all_widgets if isinstance(w, tk.Listbox))
            toggles = [w for w in all_widgets if isinstance(w, ttk.Checkbutton)]
            submit = next(w for w in all_widgets if isinstance(w, ttk.Button))
            assert not listing.curselection()
            assert all(not w.instate(['selected']) for w in toggles)
            submit.invoke()
            assert dialog.winfo_exists(), 'No debe guardar sin seleccionar ni confirmar.'
            listing.selection_set(0)
            toggles[0].invoke()
            submit.invoke()
            assert dialog.winfo_exists(), 'No debe guardar con un solo hecho confirmado.'
            toggles[1].invoke()
            checks.append(True)
            submit.invoke()
        except Exception as error:
            problems.append(error)
            dialog.destroy()
    # Un timeout local cierra incluso el diálogo defectuoso, evitando bloquear pytest.
    root.after(350, interact)
    try:
        result = choose_confirmation(root, [{'source': 'ORIGINAL', 'start': 10, 'end': 12,
            'text': 'Tiene un saldo vencido de 500 pesos.'}], 'Llamada de prueba: sample.ogg')
        assert not problems, problems
        assert checks == [True] and result == 0
        assert root.grab_current() is None
    finally:
        root.destroy()


def test_closing_visible_confirmation_cancels_without_selecting_a_fact():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    visible = []
    def close():
        dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
        visible.append(bool(dialog.winfo_viewable()))
        root.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
    root.after(350, close)
    try:
        result = choose_confirmation(root, [{'source': 'ORIGINAL', 'start': 10, 'end': 12,
            'text': 'Tiene un saldo vencido de 500 pesos.'}], 'Cancelar prueba')
        assert visible == [True] and result is None
        assert root.grab_current() is None
    finally:
        root.destroy()


def test_number_entry_then_real_confirmation_generates_checkpoint_and_excel(tmp_path, monkeypatch):
    import tkinter as tk
    from tkinter import filedialog, simpledialog, ttk
    from tools import confirm_privacy_disclosure as cli
    from openpyxl import load_workbook
    source = tmp_path/'source.json'
    source.write_text(json.dumps({'items': [{'file_name': 'sample.ogg',
        'result': {'archivo': 'sample.ogg', 'texto': 'Soy su madre. Tiene un saldo vencido de 500 pesos.',
                   'duracion_segundos': 120, 'segmentos': []},
        'relation': {'numero_de_tarjeta': '1234567890123456', 'estatus_grabacion': 'MENSAJE CON FAMILIAR'}}]}))
    original = source.read_bytes()
    create_root = tk.Tk
    states, problems = [], []
    def root_factory():
        root = create_root()
        def interact():
            dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            try:
                assert dialog.winfo_viewable()
                assert root.grab_current() == dialog
                states.append('visible after entering number')
                children = list(widgets(dialog))
                next(w for w in children if isinstance(w, tk.Listbox)).selection_set(0)
                for control in children:
                    if isinstance(control, ttk.Checkbutton): control.invoke()
                next(w for w in children if isinstance(w, ttk.Button)).invoke()
            except Exception as error:
                problems.append(error); dialog.destroy()
        root.after(350, interact)
        return root
    monkeypatch.setattr(tk, 'Tk', root_factory)
    monkeypatch.setattr(filedialog, 'askopenfilename', lambda **kwargs: str(source))
    def number(*args, **kwargs):
        assert not kwargs['parent'].winfo_viewable()
        states.append('entered number')
        return 1
    monkeypatch.setattr(simpledialog, 'askinteger', number)
    monkeypatch.setattr(sys, 'argv', ['confirm', '--output-dir', str(tmp_path/'out')])
    assert cli.main() == 0
    assert not problems, problems
    assert states == ['entered number', 'visible after entering number']
    assert source.read_bytes() == original
    final = json.loads((tmp_path/'out/resultados/checkpoint_reanalizado.json').read_text())
    assert final['items'][0]['classification']['clasificacion'] == 'FALLA_GRAVE'
    assert final['items'][0]['privacy_disclosure_confirmation']['actor_confirmed']
    book = load_workbook(final['last_report_path'], read_only=True, data_only=True)
    assert 'PEN003' in str(list(book['RESULTADOS'].values)[1])
    book.close()
