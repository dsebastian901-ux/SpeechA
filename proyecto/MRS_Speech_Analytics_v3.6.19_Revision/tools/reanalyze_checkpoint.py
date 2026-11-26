"""Reevaluar reglas y, cuando corresponda, fragmentos con Whisper exclusivamente local."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.checkpoint_reanalysis import reanalyze_checkpoint


def whisper_execution_message(result):
    readings=result.get('second_listening')or{}
    if readings.get('realizadas',0)and readings.get('errores',0):
        return 'Se ejecutaron lecturas parciales con errores; consultar cada fragmento y su consenso.'
    if readings.get('realizadas',0):
        return 'Se ejecutó Whisper local en los fragmentos registrados.'
    if readings.get('errores',0):
        return 'La relectura registró errores; consultar el detalle antes de afirmar su ejecución completa.'
    return 'No se ejecutó Whisper.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument('--no-acoustic',action='store_true',help='Solo reglas; no ejecutar nuevas lecturas acústicas.')
    parser.add_argument('--relation-excel',type=Path,help='Excel de cuentas para completar solamente mora faltante.')
    parser.add_argument('--fill-mora-from-excel',action='store_true',help='Seleccionar el Excel de cuentas y recuperar mora faltante.')
    parser.add_argument('--use-excel-card', action='store_true',
        help='Corregir en copia el identificador de nombre_final usando numero_de_tarjeta, según la política autorizada.')
    parser.add_argument('--copy-corrected-labels',action='store_true',help='Copiar solo aprobadas con etiqueta corregida, sin mover originales.')
    parser.add_argument('--audio-dir',type=Path,help='Carpeta de audios locales para corroboración o copias corregidas.')
    parser.add_argument('--labels-output-dir',type=Path,help='Carpeta nueva y vacía para las copias corregidas.')
    parser.add_argument('--review-model',choices=['auto','primary','medium'],default='auto',
        help='Segunda escucha: Medium local si está importado, modelo primario o Medium obligatorio.')
    args = parser.parse_args()
    if args.use_excel_card and (args.fill_mora_from_excel or args.relation_excel):
        parser.error('Use por separado la corrección de nombres y la recuperación de mora; conserve cada salida.')
    source = args.checkpoint
    if source is None:
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        title=('Seleccionar Checkpoint_r27_Recuperado.json para completar mora'
               if args.fill_mora_from_excel or args.relation_excel else 'Seleccionar checkpoint completo ACTUAL para reanalizar')
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
        print('Reanalizando reglas; las nuevas escuchas, si corresponden, usan exclusivamente el modelo local.',flush=True)
        result = reanalyze_checkpoint(source, args.output_dir,relation_excel=excel,
            acoustic=not args.no_acoustic,audio_directory=args.audio_dir,review_model=args.review_model)
    if excel is not None:
        import json
        saved=json.loads(Path(result['checkpoint']).read_text(encoding='utf-8'))
        print('Moras recuperadas del Excel:',saved['mora_excel_update']['filled'])
    print("Revisión del motor:", result["engine_revision"])
    print("Evaluaciones:", result["evaluations"])
    print("Resultados:", result["outcomes"])
    print("Reporte nuevo:", result["report"])
    from app.services.nonpayment_report_service import NonpaymentReportService
    companion = NonpaymentReportService.report_status(result['report'])
    if companion['path']:
        print('Reporte de motivos de no pago:', companion['path'])
    else:
        print('Reporte adicional no generado:', companion['error'])
    print("Checkpoint nuevo:", result["checkpoint"])
    if args.copy_corrected_labels:
        audio_dir=args.audio_dir
        if audio_dir is None:
            from tkinter import Tk,filedialog
            root=Tk();root.withdraw()
            selected=filedialog.askdirectory(title='Carpeta de los audios originales para las etiquetas corregidas')
            root.destroy()
            audio_dir=Path(selected) if selected else None
        if audio_dir is None:
            print('Reportes generados. Copia de etiquetas cancelada; originales conservados.')
        else:
            from app.services.corrected_label_export import export_corrected_labels
            copied=export_corrected_labels(result['checkpoint'],audio_dir,args.labels_output_dir)
            print('Copias con etiqueta corregida:',copied['copied'])
            print('Carpeta separada:',copied['folder'])
            print('Registro de copias:',copied['manifest'])
            from app.services.retagging_report import record_label_export
            record_label_export(result['report'],copied['manifest'])
            print('Cuentas y copias registradas en la hoja CUENTAS_REETIQUETADAS del reporte final.')
        print('Originales conservados.',whisper_execution_message(result))
    else:
        print('Se conservaron los originales; no se copiaron audios.',whisper_execution_message(result))


if __name__ == "__main__":
    from app.services.access_service import require_admin_tool
    require_admin_tool()
    main()
