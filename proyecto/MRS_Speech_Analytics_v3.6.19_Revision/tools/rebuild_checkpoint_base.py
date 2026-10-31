"""Generar una base local con el motor vigente cuando falla la descarga del checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.checkpoint_rebuild import read_json, needs_source_checkpoint, rebuild_checkpoint


def check_selected_file(path, kind, *, expected_calls=None, expected_sha256=None):
    """Explicar el tipo equivocado antes de pedir el siguiente archivo."""
    try:
        payload = read_json(path)
    except (UnicodeError, json.JSONDecodeError, OSError) as error:
        raise ValueError('El archivo no es un JSON legible. Seleccione el JSON, no el Excel ni un audio.') from error
    if not isinstance(payload, dict) or not isinstance(payload.get('items'), list) or not payload['items']:
        raise ValueError('El archivo no contiene una lista de llamadas reconocida.')
    items = payload['items']
    is_checkpoint = all(isinstance(i, dict) and isinstance(i.get('result'), dict) for i in items)
    if kind == 'readings':
        if is_checkpoint:
            raise ValueError('Este archivo es un checkpoint del lote. En este paso necesita '
                'revision_audios_bloque.json, guardado junto a Comparacion_Bloque_Audios.xlsx. '
                'No renombre el checkpoint: son archivos diferentes.')
        if (payload.get('schema') != 1 or not payload.get('source_checkpoint_sha256')
                or payload.get('human_verified') is not False or payload.get('whisper_executed') is not True
                or payload.get('errors') != 0 or payload.get('completed_calls') != len(items)
                or not all(isinstance(i, dict) and i.get('status') == 'completado' for i in items)):
            raise ValueError('No son lecturas ASR completas del bloque. Busque revision_audios_bloque.json '
                'en la carpeta Revision_Audios donde se genero Comparacion_Bloque_Audios.xlsx.')
    else:
        if not is_checkpoint:
            raise ValueError('Este paso requiere el checkpoint COMPLETO del lote, no el archivo de lecturas adicionales.')
        if expected_calls is not None and len(items) != expected_calls:
            raise ValueError(f'Este archivo tiene {len(items)} llamadas; se necesitan las {expected_calls} del lote completo.')
        if expected_sha256 is not None and hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected_sha256:
            raise ValueError('Este no es el checkpoint ORIGINAL con el que se generaron las lecturas. '
                'Seleccione el batch_checkpoint.json de aquella ejecucion.')
    return payload


def select_valid_file(filedialog, messagebox, title, kind, **checks):
    """Una selección errónea permite volver a elegir; cancelar no crea salidas."""
    while True:
        filters = ([('Lecturas del bloque', 'revision_audios_bloque*.json'), ('Archivos JSON', '*.json')]
                   if kind == 'readings' else [('Checkpoints JSON', '*.json')])
        value = filedialog.askopenfilename(title=title, filetypes=filters,
            initialfile='revision_audios_bloque.json' if kind == 'readings' else '')
        if not value:
            return None
        path = Path(value)
        try:
            check_selected_file(path, kind, **checks)
        except ValueError as error:
            messagebox.showerror('Seleccione el archivo correspondiente',
                f'Archivo elegido: {path.name}\n\n{error}\n\nPuede elegir otro archivo o cancelar. Los originales no cambian.')
            continue
        return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--source-checkpoint', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--use-excel-card', action='store_true')
    parser.add_argument('--expected-calls', type=int)
    parser.add_argument('--expected-readings', type=int)
    args = parser.parse_args()
    try:
        if args.checkpoint is None:
            from tkinter import Tk, filedialog, messagebox
            root = Tk(); root.withdraw()
            try:
                args.checkpoint = select_valid_file(filedialog, messagebox,
                    '1. Seleccionar el ultimo checkpoint COMPLETO de las 95 llamadas', 'checkpoint',
                    expected_calls=args.expected_calls)
                if args.checkpoint is None:
                    print('Cancelado; no se modificó ningún archivo.'); return 0
                items = read_json(args.checkpoint).get('items') or []
                linked = sum(bool(i.get('audio_block_evidence')) for i in items)
                if args.evidence is None and (not linked or
                        (args.expected_readings is not None and linked != args.expected_readings)):
                    args.evidence = select_valid_file(filedialog, messagebox,
                        '2. Elegir revision_audios_bloque.json (NO otro checkpoint)', 'readings')
                    if args.evidence is None:
                        print('Cancelado; se necesitan las lecturas para conservarlas en la base.'); return 0
                if args.evidence is not None and args.source_checkpoint is None and needs_source_checkpoint(args.checkpoint, args.evidence):
                    args.source_checkpoint = select_valid_file(filedialog, messagebox,
                        '3. Seleccionar batch_checkpoint.json ORIGINAL usado para las lecturas', 'checkpoint',
                        expected_sha256=read_json(args.evidence).get('source_checkpoint_sha256'))
                    if args.source_checkpoint is None:
                        print('Cancelado; se necesita el origen para comprobar la correspondencia.'); return 0
            finally:
                root.destroy()
        result = rebuild_checkpoint(args.checkpoint, args.evidence,
            source_checkpoint=args.source_checkpoint, output_directory=args.output_dir,
            use_excel_card=args.use_excel_card, expected_calls=args.expected_calls,
            expected_readings=args.expected_readings)
    except Exception as error:
        print('No se completó la reconstrucción:', error)
        print('Los archivos de entrada permanecen intactos.')
        return 1
    print('Base generada:', result['checkpoint'])
    print('Revisión del motor:', result['engine_revision'])
    print('Reporte generado:', result['report'])
    print('Resultados:', result['outcomes'])
    print('Correcciones de nombre:', result['output_names_corrected'])
    print('Lecturas adicionales vinculadas:', result['linked_readings'])
    print('No se ejecutó Whisper, no se procesaron audios y no se registró escucha humana.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
