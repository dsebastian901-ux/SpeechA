"""Generar la base r25 localmente cuando no se puede descargar el checkpoint."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.checkpoint_rebuild import read_json, needs_source_checkpoint, rebuild_checkpoint


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
            from tkinter import Tk, filedialog
            root = Tk(); root.withdraw()
            try:
                def select(title):
                    value = filedialog.askopenfilename(title=title, filetypes=[('Archivos JSON', '*.json')])
                    return Path(value) if value else None
                args.checkpoint = select('1. Seleccionar el último checkpoint COMPLETO de las 95 llamadas')
                if args.checkpoint is None:
                    print('Cancelado; no se modificó ningún archivo.'); return 0
                items = read_json(args.checkpoint).get('items') or []
                linked = sum(bool(i.get('audio_block_evidence')) for i in items)
                if args.evidence is None and (not linked or
                        (args.expected_readings is not None and linked != args.expected_readings)):
                    args.evidence = select('2. Seleccionar revision_audios_bloque.json (las diez lecturas)')
                    if args.evidence is None:
                        print('Cancelado; se necesitan las lecturas para conservarlas en la base.'); return 0
                if args.evidence is not None and args.source_checkpoint is None and needs_source_checkpoint(args.checkpoint, args.evidence):
                    args.source_checkpoint = select('3. Seleccionar batch_checkpoint.json ORIGINAL usado para las lecturas')
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
    print('Reporte generado:', result['report'])
    print('Resultados:', result['outcomes'])
    print('Correcciones de nombre:', result['output_names_corrected'])
    print('Lecturas adicionales vinculadas:', result['linked_readings'])
    print('No se ejecutó Whisper, no se procesaron audios y no se registró escucha humana.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
