"""Reportes de varios lotes: selección local, sin depender de proyecto abierto."""
from pathlib import Path
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.services.consolidated_report_service import ConsolidatedReportService as Reports
from app.ui.themes import Theme


class ConsolidatedReportsDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title('Reportes de varios lotes')
        self.geometry('950x690'); self.minsize(850, 620)
        self.grid_columnconfigure(0, weight=1)
        self.paths = []
        self.dataset = None
        self.busy = False
        self.messages = queue.Queue()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.transient(master.winfo_toplevel())
        ctk.CTkLabel(self, text='REPORTES DE VARIOS LOTES', font=ctk.CTkFont(size=23, weight='bold'),
                     text_color=Theme.colors.PRIMARY).grid(row=0, column=0, padx=22, pady=(20, 8), sticky='w')
        ctk.CTkLabel(self, text='Carga local de checkpoints JSON o ZIP. Cada lote cuenta por separado, incluso si repite una llamada.',
                     wraplength=880, anchor='w').grid(row=1, column=0, padx=22, sticky='ew')
        buttons = ctk.CTkFrame(self)
        buttons.grid(row=2, column=0, padx=22, pady=12, sticky='ew')
        self.load_button = ctk.CTkButton(buttons, text='Agregar lotes', command=self._add)
        self.load_button.pack(side='left', padx=10, pady=10)
        self.clear_button = ctk.CTkButton(buttons, text='Limpiar selección', command=self._clear)
        self.clear_button.pack(side='left', padx=10, pady=10)
        self.listbox = ctk.CTkTextbox(self, height=110)
        self.listbox.grid(row=3, column=0, padx=22, sticky='ew')
        self.listbox.configure(state='disabled')
        options = ctk.CTkFrame(self)
        options.grid(row=4, column=0, padx=22, pady=12, sticky='ew')
        options.grid_columnconfigure((1, 3), weight=1)
        self.family = ctk.StringVar(value='Calidad y mejoras')
        self.level = ctk.StringVar(value='General')
        self.group = ctk.StringVar(value='Global')
        self.gestor = ctk.StringVar(value='Todos')
        self.supervisor = ctk.StringVar(value='Todos')
        self.format = ctk.StringVar(value='Excel')
        def option(row, col, title, variable, values, command=None):
            ctk.CTkLabel(options, text=title).grid(row=row, column=col, padx=10, pady=9, sticky='w')
            widget = ctk.CTkOptionMenu(options, variable=variable, values=values, command=command)
            widget.grid(row=row, column=col+1, padx=10, pady=9, sticky='ew')
            return widget
        option(0, 0, 'Tipo', self.family, ['Calidad y mejoras', 'Motivos de no pago', 'Fallas graves'], self._family_changed)
        option(0, 2, 'Nivel', self.level, ['General', 'Detallado'])
        option(1, 0, 'Agrupar', self.group, ['Global', 'Por gestor', 'Por supervisor'])
        self.format_menu = option(1, 2, 'Exportar', self.format, ['Excel'])
        self.gestor_menu = option(2, 0, 'Gestor', self.gestor, ['Todos'])
        self.supervisor_menu = option(2, 2, 'Supervisor', self.supervisor, ['Todos'])
        ctk.CTkLabel(options, text='Desde').grid(row=3, column=0, padx=10, sticky='w')
        self.date_from = ctk.CTkEntry(options, placeholder_text='dd/mm/aaaa (opcional)')
        self.date_from.grid(row=3, column=1, padx=10, pady=9, sticky='ew')
        ctk.CTkLabel(options, text='Hasta').grid(row=3, column=2, padx=10, sticky='w')
        self.date_to = ctk.CTkEntry(options, placeholder_text='dd/mm/aaaa (opcional)')
        self.date_to.grid(row=3, column=3, padx=10, pady=9, sticky='ew')
        self.summary = ctk.CTkLabel(self, text='Sin lotes cargados.', anchor='w', wraplength=880)
        self.summary.grid(row=5, column=0, padx=22, pady=6, sticky='ew')
        self.generate_button = ctk.CTkButton(self, text='Generar reporte', state='disabled', command=self._generate)
        self.generate_button.grid(row=6, column=0, padx=22, pady=12, sticky='w')
        self.status = ctk.CTkLabel(self, text='General: hasta 3 ejemplos por error/agrupación. Detallado: todos los registros seleccionados.',
                                   wraplength=880, anchor='w')
        self.status.grid(row=7, column=0, padx=22, pady=(0, 14), sticky='ew')

    def _family_changed(self, value):
        allowed = ['Excel', 'Word', 'Excel y Word'] if value == 'Fallas graves' else ['Excel']
        self.format_menu.configure(values=allowed)
        if self.format.get() not in allowed: self.format.set('Excel')

    def _add(self):
        if self.busy: return
        files = filedialog.askopenfilenames(parent=self, title='Seleccionar checkpoints de los lotes',
                                            filetypes=[('Checkpoints JSON o ZIP', '*.json *.zip')])
        if not files: return
        paths = list(dict.fromkeys([*self.paths, *map(str, files)]))
        self._work('load', lambda: (paths, Reports.load(paths, deduplicate=False)))

    def _clear(self):
        if self.busy: return
        self.paths = []; self.dataset = None
        self.listbox.configure(state='normal'); self.listbox.delete('1.0', 'end'); self.listbox.configure(state='disabled')
        for menu, value in [(self.gestor_menu,self.gestor), (self.supervisor_menu,self.supervisor)]:
            menu.configure(values=['Todos']); value.set('Todos')
        self.generate_button.configure(state='disabled'); self.summary.configure(text='Sin lotes cargados.')

    def _generate(self):
        if self.busy or not self.dataset: return
        directory = filedialog.askdirectory(parent=self, title='Carpeta para guardar los reportes nuevos')
        if not directory: return
        options = {
            'level': self.level.get().upper(),
            'family': {'Calidad y mejoras':'CALIDAD','Motivos de no pago':'MOTIVOS','Fallas graves':'GRAVES'}[self.family.get()],
            'group_by': {'Global':'GLOBAL','Por gestor':'GESTOR','Por supervisor':'SUPERVISOR'}[self.group.get()],
            'gestor': '' if self.gestor.get() == 'Todos' else self.gestor.get(),
            'supervisor': '' if self.supervisor.get() == 'Todos' else self.supervisor.get(),
            'date_from': self.date_from.get().strip(), 'date_to': self.date_to.get().strip(),
            'formats': {'Excel':('xlsx',),'Word':('docx',),'Excel y Word':('xlsx','docx')}[self.format.get()],
        }
        dataset = self.dataset
        self._work('export', lambda: Reports.generate(dataset, directory, **options))

    def _work(self, operation, function):
        self.busy = True
        for button in [self.load_button, self.clear_button, self.generate_button]: button.configure(state='disabled')
        self.status.configure(text='Cargando lotes…' if operation == 'load' else 'Generando reporte…')
        def run():
            try: self.messages.put((operation, function(), None))
            except Exception as error: self.messages.put((operation, None, str(error)))
        threading.Thread(target=run, daemon=True).start()
        self.after(100, self._poll)

    def _poll(self):
        try: operation, result, error = self.messages.get_nowait()
        except queue.Empty:
            self.after(100, self._poll); return
        self.busy = False
        self.load_button.configure(state='normal'); self.clear_button.configure(state='normal')
        if error:
            self.status.configure(text='No se generó el reporte. Los archivos de entrada permanecen intactos.')
            messagebox.showerror('Reportes de varios lotes', error, parent=self)
        elif operation == 'load':
            self.paths, self.dataset = result
            self.listbox.configure(state='normal'); self.listbox.delete('1.0','end')
            self.listbox.insert('1.0', '\n'.join(s['name'] for s in self.dataset['sources'])); self.listbox.configure(state='disabled')
            calls = self.dataset['calls']
            for menu, variable, key in [(self.gestor_menu,self.gestor,'gestor'),(self.supervisor_menu,self.supervisor,'supervisor')]:
                values = ['Todos', *sorted({r[key] for r in calls})]; menu.configure(values=values)
                if variable.get() not in values: variable.set('Todos')
            self.summary.configure(text=f"{len(self.paths)} lotes · {len(calls)} evaluaciones · {sum(r['severe'] for r in calls)} con falla grave reportada · {len(self.dataset['warnings'])} notas de datos.")
            self.status.configure(text='Lotes cargados. Las notas y datos faltantes se incluyen en el Excel; no se redictaminaron llamadas.')
        else:
            files = '\n'.join(result['files'].values())
            self.status.configure(text=f"Reporte generado: {result['calls']} evaluaciones seleccionadas.")
            messagebox.showinfo('Reportes generados', files, parent=self)
        self.generate_button.configure(state='normal' if self.dataset else 'disabled')

    def _close(self):
        if self.busy:
            messagebox.showinfo('Reportes', 'Espere a que termine la operación antes de cerrar.', parent=self); return
        self.destroy()
