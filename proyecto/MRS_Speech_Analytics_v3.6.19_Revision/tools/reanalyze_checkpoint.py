"""Seleccionar un checkpoint y generar un reporte nuevo sin ejecutar Whisper."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.checkpoint_reanalysis import reanalyze_checkpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument('--relation-excel',type=Path,help='Excel de cuentas para completar solamente mora faltante.')
    parser.add_argument('--fill-mora-from-excel',action='store_true',help='Seleccionar el Excel de cuentas y recuperar mora faltante.')
    parser.add_argument('--use-excel-card', action='store_true',
        help='Corregir en copia el identificador de nombre_final usando numero_de_tarjeta, según la política autorizada.')
    args = parser.parse_args()
    if args.use_excel_card and (args.fill_mora_from_excel or args.relation_excel):
        parser.error('Use por separado la corrección de nombres y la recuperación de mora; conserve cada salida.')
    source = args.checkpoint
    if source is None:
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        title=('Seleccionar Checkpoint_r27_Recuperado.json para completar mora'
               if args.fill_mora_from_excel or args.relation_excel else 'Seleccionar batch_checkpoint.json')
        selected = filedialog.askopenfilename(title=title,
                                             filetypes=[("Checkpoint JSON", "*.json")])
        root.destroy()
        if not selected:
            print("Reanálisis cancelado.")
            return
        source = Path(selected)
    excel=args.relation_excel
    if args.fill_mora_from_excel and excel is None:
        from tkinter import Tk, filedialog
        root=Tk();root.withdraw()
        selected=filedialog.askopenfilename(title='Seleccionar Excel de cuentas con mora (Calidad Noviembre.xlsx)',
                                           filetypes=[('Excel de cuentas','*.xlsx *.xlsm')])
        root.destroy()
        if not selected:
            print('Cancelado; no se modificaron los archivos de entrada.');return
        excel=Path(selected)
    if args.use_excel_card:
        from app.services.checkpoint_rebuild import rebuild_checkpoint
        result = rebuild_checkpoint(source, output_directory=args.output_dir, use_excel_card=True,
                                    require_readings=False)
        print('Identificadores de nombre corregidos con numero_de_tarjeta:', result['output_names_corrected'])
    else:
        result = reanalyze_checkpoint(source, args.output_dir,relation_excel=excel)
    if excel is not None:
        import json
        saved=json.loads(Path(result['checkpoint']).read_text(encoding='utf-8'))
        print('Moras recuperadas del Excel:',saved['mora_excel_update']['filled'])
    print("Revisión del motor:", result["engine_revision"])
    print("Evaluaciones:", result["evaluations"])
    print("Resultados:", result["outcomes"])
    print("Reporte nuevo:", result["report"])
    print("Checkpoint nuevo:", result["checkpoint"])
    print("Se conservaron los originales. No se ejecutó Whisper ni se copiaron audios.")


if __name__ == "__main__":
    main()
