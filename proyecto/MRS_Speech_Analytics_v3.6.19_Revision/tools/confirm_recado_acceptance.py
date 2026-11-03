"""Guardar aceptación o entrega de recado y contacto ya confirmadas, sin Whisper."""
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
    parser.add_argument('--delivered-recado', action='store_true')
    parser.add_argument('--description')
    parser.add_argument('--confirm-message', action='store_true')
    parser.add_argument('--confirm-callback', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    if not args.delivered_recado and (args.description is not None or args.confirm_message or args.confirm_callback):
        parser.error('Use --delivered-recado para confirmar la entrega del recado y del contacto.')
    if args.delivered_recado and args.confirm_acceptance:
        parser.error('Seleccione un solo alcance: aceptación o recado y contacto entregados.')
    root = None
    try:
        needs_confirmation = (not (args.confirm_message and args.confirm_callback and args.description is not None)
                              if args.delivered_recado else not args.confirm_acceptance)
        if args.checkpoint is None or args.call_number is None or needs_confirmation:
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
        if args.delivered_recado:
            label = f"Llamada {args.call_number}: {item['file_name']}\n\n"
            for field, prompt in [
                ('confirm_message', '¿Ya comprobó que el gestor entrega al interlocutor un recado para el titular?'),
                ('confirm_callback', '¿Ya comprobó que también entrega un contacto para que el titular se comunique?')]:
                if not getattr(args, field):
                    if not messagebox.askyesno('Recado y contacto entregados', label+prompt,
                                               parent=root, default=messagebox.NO):
                        print('Cancelado; no se registró la confirmación.'); return 0
                    setattr(args, field, True)
            if args.description is None:
                args.description = simpledialog.askstring('Contenido del recado',
                    label+'Describa brevemente el recado que comprobó en el audio.\n'
                    'No complete palabras o números que no haya confirmado.', parent=root)
                if args.description is None:
                    print('Cancelado; no se registró la confirmación.'); return 0
        elif not args.confirm_acceptance:
            confirmed = messagebox.askyesno('Aceptación del recado',
                f"Llamada {args.call_number}: {item['file_name']}\n\n"
                '¿Ya comprobó que el interlocutor acepta transmitir el recado?\n'
                'Solo se registrará este hecho; se mantienen las demás validaciones.',
                parent=root, default=messagebox.NO)
            if not confirmed:
                print('Cancelado; no se registró una confirmación.'); return 0
        print('Generando checkpoint y reporte; espere a que termine...', flush=True)
        result = confirm_checkpoint_recado(args.checkpoint, item['file_name'], args.output_dir,
            user_confirmed=not args.delivered_recado, message_description=args.description,
            message_confirmed=args.confirm_message, callback_confirmed=args.confirm_callback)
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
