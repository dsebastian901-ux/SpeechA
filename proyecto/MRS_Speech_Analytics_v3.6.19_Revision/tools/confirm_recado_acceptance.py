"""Guardar aceptación de recado ya confirmada y reanalizar sin Whisper."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.recado_acceptance_review import confirm_checkpoint_recado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--call', dest='call_number', type=int)
    parser.add_argument('--confirm-acceptance', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    root = None
    try:
        if args.checkpoint is None or args.call_number is None or not args.confirm_acceptance:
            from tkinter import Tk, filedialog, simpledialog, messagebox
            root = Tk()
            root.withdraw()
        if args.checkpoint is None:
            name = filedialog.askopenfilename(parent=root, title='Seleccionar checkpoint completo ACTUAL',
                                             filetypes=[('JSON', '*.json')])
            if not name:
                print('Cancelado.'); return 0
            args.checkpoint = Path(name)
        data = json.loads(args.checkpoint.read_text(encoding='utf-8-sig'))
        items = data.get('items') or []
        if not items or not all(isinstance(i.get('result'), dict) for i in items):
            raise ValueError('Seleccione el checkpoint completo, no una lectura ASR.')
        if args.call_number is None:
            args.call_number = simpledialog.askinteger('Recado confirmado',
                'Número de llamada en este checkpoint:', minvalue=1, maxvalue=len(items), parent=root)
            if args.call_number is None:
                print('Cancelado.'); return 0
        if not 1 <= args.call_number <= len(items):
            raise ValueError('Número de llamada fuera del lote seleccionado.')
        item = items[args.call_number-1]
        if not args.confirm_acceptance:
            confirmed = messagebox.askyesno('Aceptación del recado',
                f"Llamada {args.call_number}: {item['file_name']}\n\n"
                '¿Ya comprobó que el interlocutor acepta transmitir el recado?\n'
                'Solo se registrará este hecho; se mantienen las demás validaciones.',
                parent=root, default=messagebox.NO)
            if not confirmed:
                print('Cancelado; no se registró una confirmación.'); return 0
        print('Generando checkpoint y reporte; espere a que termine...', flush=True)
        result = confirm_checkpoint_recado(args.checkpoint, item['file_name'], args.output_dir,
                                           user_confirmed=True)
    except Exception as error:
        print('No se registró la confirmación:', error)
        return 1
    finally:
        if root is not None:
            root.destroy()
    for label, key in [('Revisión del motor', 'engine_revision'), ('Resultados', 'outcomes'),
                       ('Checkpoint nuevo', 'checkpoint'), ('Reporte nuevo', 'report')]:
        print(label+':', result[key])
    print('No se ejecutó Whisper ni se modificaron los archivos originales.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
