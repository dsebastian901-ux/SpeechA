"""Incorporar al lote completo las confirmaciones de un checkpoint ya revisado."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.checkpoint_review_import import import_checkpoint_reviews


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--reviewed", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--relation-excel", type=Path)
    args = parser.parse_args()
    batch, reviewed = args.batch, args.reviewed
    if batch is None or reviewed is None:
        from tkinter import Tk, filedialog, messagebox
        root = Tk(); root.withdraw()
        try:
            if batch is None:
                selected = filedialog.askopenfilename(title="Paso 1: seleccionar checkpoint del lote completo",
                    filetypes=[("Checkpoint JSON", "*.json")])
                if not selected:
                    return
                batch = Path(selected)
            if reviewed is None:
                selected = filedialog.askopenfilename(title="Paso 2: seleccionar checkpoint final ya validado",
                    filetypes=[("Checkpoint JSON", "*.json")])
                if not selected:
                    return
                reviewed = Path(selected)
            try:
                result = import_checkpoint_reviews(batch, reviewed, args.output_dir, args.relation_excel)
            except Exception as error:
                messagebox.showerror("Incorporación de validaciones", str(error), parent=root)
                raise
        finally:
            root.destroy()
    else:
        result = import_checkpoint_reviews(batch, reviewed, args.output_dir, args.relation_excel)
    print("Revisión del motor:", result["engine_revision"])
    print("Llamadas en el lote:", result["evaluations"])
    print("Llamadas con confirmaciones incorporadas:", result["imported_calls"])
    print("Resultados:", result["outcomes"])
    print("Checkpoint nuevo:", result["checkpoint"])
    print("Reporte nuevo:", result["report"])
    if result.get("corrected_excel"):
        print("Excel de cuentas corregido en copia:", result["corrected_excel"])
    print("Se conservaron los originales. No se ejecutó Whisper ni se copiaron audios.")


if __name__ == "__main__":
    main()
