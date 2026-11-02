"""Registrar una divulgación que el usuario ya confirmó, sin volver a ejecutar Whisper."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.checkpoint_privacy_review import confirm_checkpoint_disclosure
from app.services.privacy_disclosure_review import disclosure_candidates


def choose_confirmation(root, candidates, call_label,*,home_warning=False):
    from tkinter import BooleanVar, StringVar, Toplevel, Listbox, END
    from tkinter import ttk
    dialog = Toplevel(root)
    dialog.title('Advertencia en domicilio confirmada' if home_warning else 'Divulgación ya confirmada por el usuario')
    dialog.geometry('900x540')
    ttk.Label(dialog, text=call_label, wraplength=850).pack(padx=15, pady=5)
    ttk.Label(dialog, text='Seleccione el fragmento que escuchó y confirme ambos hechos.\n'
              'Las lecturas ASR no identifican por sí mismas al hablante.', wraplength=850).pack(padx=15, pady=12)
    listing = Listbox(dialog, height=9, exportselection=False)
    listing.pack(fill='both', expand=True, padx=15)
    for index, candidate in enumerate(candidates, 1):
        timing = (f"{candidate['start']:.2f}–{candidate['end']:.2f} s"
                  if all(isinstance(candidate[k], (int, float)) for k in ('start', 'end')) else 'sin tiempo')
        listing.insert(END, f"{index}. {candidate['source']} · {timing} · {candidate['text']}")
    detail = StringVar(master=dialog)
    ttk.Label(dialog, textvariable=detail, wraplength=850).pack(padx=15, pady=8)
    listing.bind('<<ListboxSelect>>', lambda event: detail.set(
        ((('Contexto: '+candidates[listing.curselection()[0]]['question_text']+'\nFragmento: ')
          if candidates[listing.curselection()[0]].get('question_text') else '')
         +candidates[listing.curselection()[0]]['text']) if listing.curselection() else ''))
    actor, recipient = BooleanVar(master=dialog, value=False), BooleanVar(master=dialog, value=False)
    ttk.Checkbutton(dialog, text='Confirmé que el gestor dice el fragmento seleccionado.', variable=actor).pack(anchor='w', padx=15, pady=7)
    ttk.Checkbutton(dialog, text=('Confirmé en el audio esta advertencia de recuperación en domicilio.' if home_warning
                                else 'Confirmé que la recibe un tercero, no el titular.'), variable=recipient).pack(anchor='w', padx=15)
    message = StringVar(master=dialog)
    ttk.Label(dialog, textvariable=message).pack(pady=5)
    selected = []
    def save():
        if not listing.curselection() or not actor.get() or not recipient.get():
            message.set('Seleccione un fragmento y marque los dos hechos ya confirmados.'); return
        selected.append(listing.curselection()[0])
        dialog.destroy()
    ttk.Button(dialog, text='Registrar confirmación y generar reporte', command=save).pack(pady=10)
    dialog.protocol('WM_DELETE_WINDOW', dialog.destroy)
    # Tk oculta las ventanas transitorias si su ventana propietaria está
    # retirada. El selector anterior usa precisamente una raíz withdraw().
    # No capturar la entrada hasta que el usuario pueda ver la confirmación.
    if root.winfo_viewable():
        dialog.transient(root)
    dialog.deiconify()
    dialog.lift()
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_force()
    root.wait_window(dialog)
    return selected[0] if selected else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--call', type=int, dest='call_number')
    parser.add_argument('--candidate', type=int, help='Fragmento de la lista, empezando en 1.')
    parser.add_argument('--confirm-gestor', action='store_true')
    parser.add_argument('--confirm-tercero', action='store_true')
    parser.add_argument('--home-warning',action='store_true')
    parser.add_argument('--confirm-warning',action='store_true')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    root = None
    try:
        if args.checkpoint is None or args.call_number is None or args.candidate is None:
            from tkinter import Tk, filedialog, simpledialog
            root = Tk(); root.withdraw()
            if args.checkpoint is None:
                name = filedialog.askopenfilename(title='Seleccionar checkpoint completo ACTUAL', filetypes=[('JSON', '*.json')])
                if not name: print('Cancelado.'); return 0
                args.checkpoint = Path(name)
        data = json.loads(args.checkpoint.read_text(encoding='utf-8-sig'))
        items = data.get('items') or []
        if not items or not all(isinstance(i.get('result'), dict) for i in items):
            raise ValueError('Seleccione el checkpoint completo, no una lectura ASR.')
        if args.call_number is None:
            args.call_number = simpledialog.askinteger('Llamada confirmada', 'Número de llamada en este checkpoint:',
                minvalue=1, maxvalue=len(items), parent=root)
            if args.call_number is None: print('Cancelado.'); return 0
        if not 1 <= args.call_number <= len(items):
            raise ValueError('Número de llamada fuera del lote seleccionado.')
        item = items[args.call_number-1]
        print('Buscando fragmentos de la llamada seleccionada...', flush=True)
        if args.home_warning:
            from app.services.home_warning_review import warning_candidates
            candidates=warning_candidates(item['result'],item.get('relation') or {},item.get('audio_block_evidence'))
        else:candidates = disclosure_candidates(item['result'], item.get('relation') or {}, item.get('audio_block_evidence'))
        if not candidates:
            raise ValueError('No hay un fragmento financiero declarativo válido para vincular; conserve la revisión.')
        if args.candidate is None:
            # Mostrar la identidad exacta antes de registrar; no hay llamada ni fragmento preseleccionado.
            print('Abriendo la ventana de fragmentos y confirmación...', flush=True)
            label=f"Llamada {args.call_number}: {item['file_name']}"
            selection=(choose_confirmation(root,candidates,label,home_warning=True) if args.home_warning
                       else choose_confirmation(root, candidates,label))
            if selection is None: print('Cancelado.'); return 0
            args.candidate = selection+1
            args.confirm_gestor = True
            if args.home_warning:args.confirm_warning=True
            else:args.confirm_tercero=True
        if not 1 <= args.candidate <= len(candidates):
            raise ValueError('Fragmento fuera de la lista de evidencias.')
        print('Generando el checkpoint y el reporte. Espere a que termine...', flush=True)
        result = confirm_checkpoint_disclosure(args.checkpoint, item['file_name'], candidates[args.candidate-1],
            args.output_dir, actor_confirmed=args.confirm_gestor, third_party_confirmed=args.confirm_tercero,
            home_warning=args.home_warning,warning_confirmed=args.confirm_warning)
    except Exception as error:
        print('No se registró la confirmación:', error); return 1
    finally:
        if root is not None: root.destroy()
    print('Revisión del motor:', result['engine_revision'])
    print('Evaluaciones:', result['evaluations'])
    print('Resultados:', result['outcomes'])
    print('Checkpoint nuevo:', result['checkpoint'])
    print('Reporte nuevo:', result['report'])
    print('No se ejecutó Whisper ni se modificaron los archivos originales.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
