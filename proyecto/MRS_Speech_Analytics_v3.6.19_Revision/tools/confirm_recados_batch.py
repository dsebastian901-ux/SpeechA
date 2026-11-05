"""Registrar varias confirmaciones de recado y generar una sola salida final."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.checkpoint_recado_batch_review import prepare_recado_selections, confirm_checkpoint_recados
from app.services.recado_acceptance_review import DELIVERY_SCOPE


class RecadoBatchWindow:
    def __init__(self, root, checkpoint, payload, source_hash, output_directory=None):
        import tkinter as tk
        from tkinter import ttk
        self.root = root; self.checkpoint = Path(checkpoint); self.payload = payload
        self.source_hash = source_hash; self.output_directory = output_directory
        self.prepared = None; self.busy = False; self.result = None; self.messages = queue.Queue()
        root.title('Confirmar recados de varias llamadas'); root.geometry('1040x680')
        root.minsize(900, 620)
        frame = ttk.Frame(root, padding=12); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=f"Checkpoint: {self.checkpoint.name} · {len(payload['items'])} llamadas").pack(anchor='w')
        ttk.Label(frame, text='Registre únicamente los hechos que ya comprobó. Puede incluir varias llamadas.').pack(anchor='w', pady=(3, 12))
        self.accepted = tk.StringVar(root); self.accepted_ok = tk.BooleanVar(root, value=False)
        self.message_ok = tk.BooleanVar(root, value=False); self.callback_ok = tk.BooleanVar(root, value=False)
        groups = ttk.Frame(frame); groups.pack(fill='x')
        groups.columnconfigure(0, weight=1); groups.columnconfigure(1, weight=1)
        accepted_group = ttk.LabelFrame(groups, text='Aceptación del recado', padding=10)
        accepted_group.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        delivered_group = ttk.LabelFrame(groups, text='Recado y contacto entregados', padding=10)
        delivered_group.grid(row=0, column=1, sticky='nsew')
        ttk.Label(accepted_group, text='Números de llamada separados por comas').pack(anchor='w')
        ttk.Entry(accepted_group, textvariable=self.accepted).pack(fill='x', pady=4)
        ttk.Checkbutton(accepted_group, text='Confirmé la aceptación de esas llamadas.',
                        variable=self.accepted_ok).pack(anchor='w')
        ttk.Label(delivered_group, text='Una línea: número | descripción del mensaje').pack(anchor='w')
        self.delivered = tk.Text(delivered_group, height=3, width=48, wrap='word'); self.delivered.pack(fill='x', pady=4)
        ttk.Checkbutton(delivered_group, text='Confirmé la entrega de los recados indicados.',
                        variable=self.message_ok).pack(anchor='w', pady=(5, 0))
        ttk.Checkbutton(delivered_group, text='Confirmé también la entrega de sus contactos.',
                        variable=self.callback_ok).pack(anchor='w')
        ttk.Label(frame, text='Revise los archivos seleccionados antes de guardar. No se modifica el audio ni la transcripción.').pack(anchor='w', pady=(14, 5))
        self.preview_button = ttk.Button(frame, text='Revisar llamadas seleccionadas', command=self.preview)
        self.preview_button.pack(anchor='w')
        self.tree = ttk.Treeview(frame, columns=('call', 'file', 'scope'), show='headings', height=4)
        for key, label, width in [('call', 'Llamada', 70), ('file', 'Archivo', 620), ('scope', 'Hecho confirmado', 260)]:
            self.tree.heading(key, text=label); self.tree.column(key, width=width)
        self.tree.pack(fill='both', expand=True, pady=8)
        self.status = tk.StringVar(root, value='Indique las llamadas y los hechos ya comprobados.')
        ttk.Label(frame, textvariable=self.status, wraplength=980).pack(anchor='w', pady=5)
        self.progress = ttk.Progressbar(frame, mode='indeterminate'); self.progress.pack(fill='x', pady=5)
        buttons = ttk.Frame(frame); buttons.pack(fill='x')
        self.save_button = ttk.Button(buttons, text='Guardar todas y generar checkpoint y Excel', command=self.save, state='disabled')
        self.save_button.pack(side='left')
        self.open_button = ttk.Button(buttons, text='Abrir resultados', command=self.open_results, state='disabled')
        self.open_button.pack(side='left', padx=10)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.deiconify(); root.lift()

    def selection(self):
        return prepare_recado_selections(self.payload['items'], self.accepted.get(), self.delivered.get('1.0', 'end'),
            acceptances_confirmed=self.accepted_ok.get(), messages_confirmed=self.message_ok.get(),
            callbacks_confirmed=self.callback_ok.get())

    def preview(self):
        if self.busy:
            return
        try:
            self.prepared = self.selection()
        except Exception as error:
            self.prepared = None; self.save_button.configure(state='disabled'); self.status.set(str(error)); return
        self.tree.delete(*self.tree.get_children())
        for number, item in enumerate(self.payload['items'], 1):
            fact = self.prepared.get(item['file_name'])
            if fact:
                self.tree.insert('', 'end', values=(number, item['file_name'],
                    'Recado y contacto entregados' if fact['scope'] == DELIVERY_SCOPE else 'Aceptación de recado'))
        self.status.set(f'{len(self.prepared)} llamadas seleccionadas. Revise los archivos y guarde todas juntas.')
        self.save_button.configure(state='normal')

    def save(self):
        if self.busy:
            return
        try:
            if self.prepared is None or self.selection() != self.prepared:
                raise ValueError('Revise de nuevo las llamadas seleccionadas antes de guardar.')
        except Exception as error:
            self.save_button.configure(state='disabled'); self.status.set(str(error)); return
        self.busy = True
        self.save_button.configure(state='disabled'); self.preview_button.configure(state='disabled')
        self.open_button.configure(state='disabled'); self.progress.start(12)
        self.status.set('Registrando confirmaciones y generando un único checkpoint y Excel. Espere a que termine.')
        # Solo el hilo principal usa Tk. El trabajo de reglas/Excel no bloquea la ventana.
        selected = self.prepared.copy()
        def work():
            try:
                result = confirm_checkpoint_recados(self.checkpoint, selected, self.output_directory,
                                                    expected_source_sha256=self.source_hash)
                self.messages.put((True, result))
            except Exception as error:
                self.messages.put((False, str(error)))
        self.worker = threading.Thread(target=work, daemon=False); self.worker.start()
        self.root.after(100, self.poll)

    def poll(self):
        try:
            success, result = self.messages.get_nowait()
        except queue.Empty:
            self.root.after(100, self.poll); return
        self.busy = False; self.progress.stop()
        if success:
            self.result = result
            self.status.set(f"Terminado: {result['outcomes']}\nCheckpoint final: {result['checkpoint']}\nExcel: {result['report']}")
            self.open_button.configure(state='normal')
        else:
            self.status.set('No se completó la operación: '+result)
            self.preview_button.configure(state='normal')
        # Tras un resultado correcto, cerrar y volver a abrir evita reutilizar una base antigua.

    def open_results(self):
        if self.result:
            folder = str(Path(self.result['checkpoint']).parent)
            if os.name == 'nt':
                os.startfile(folder)
            else:
                self.status.set('Carpeta de resultados: '+folder)

    def close(self):
        if self.busy:
            self.status.set('La operación sigue en curso. Espere a que termine antes de cerrar.'); return
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--accepted-calls')
    parser.add_argument('--delivered-call', action='append', default=[])
    parser.add_argument('--confirm-acceptances', action='store_true')
    parser.add_argument('--confirm-messages', action='store_true')
    parser.add_argument('--confirm-callbacks', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(); root = None
    try:
        gui = args.accepted_calls is None and not args.delivered_call
        if gui or args.checkpoint is None:
            from tkinter import Tk, filedialog
            root = Tk(); root.withdraw()
        if args.checkpoint is None:
            name = filedialog.askopenfilename(parent=root, title='Seleccionar checkpoint completo actual',
                                             filetypes=[('JSON', '*.json')])
            if not name:
                print('Cancelado.'); return 0
            args.checkpoint = Path(name)
        raw = args.checkpoint.read_bytes(); payload = json.loads(raw.decode('utf-8-sig'))
        if not isinstance(payload, dict) or not isinstance(payload.get('items'), list) or not payload['items']:
            raise ValueError('Seleccione un checkpoint completo con llamadas.')
        source_hash = hashlib.sha256(raw).hexdigest()
        if gui:
            window = RecadoBatchWindow(root, args.checkpoint, payload, source_hash, args.output_dir)
            root.mainloop()
            result = window.result
            if result is None:
                print('No se generó una salida nueva.'); return 0
        else:
            selected = prepare_recado_selections(payload['items'], args.accepted_calls or '',
                '\n'.join(args.delivered_call), acceptances_confirmed=args.confirm_acceptances,
                messages_confirmed=args.confirm_messages, callbacks_confirmed=args.confirm_callbacks)
            print('Generando un único checkpoint y Excel para todas las confirmaciones...', flush=True)
            result = confirm_checkpoint_recados(args.checkpoint, selected, args.output_dir,
                                                expected_source_sha256=source_hash)
        print('Resultados:', result['outcomes'])
        print('Checkpoint final:', result['checkpoint'])
        print('Excel:', result['report'])
        print('No se ejecutó Whisper ni se modificaron los originales.')
        return 0
    except Exception as error:
        print('No se completó la operación:', error); return 1
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


if __name__ == '__main__':
    raise SystemExit(main())
