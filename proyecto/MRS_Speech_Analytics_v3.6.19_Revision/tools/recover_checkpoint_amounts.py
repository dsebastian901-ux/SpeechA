"""Releer ofertas sin importe en audio y conservar el checkpoint original."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.checkpoint_amount_recovery import recover_checkpoint_amounts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--audio-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.checkpoint is None:
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        selected = filedialog.askopenfilename(title="Seleccionar batch_checkpoint.json", filetypes=[("Checkpoint JSON", "*.json")])
        folder = filedialog.askdirectory(title="Seleccionar carpeta con los audios originales") if selected else ""
        root.destroy()
        if not selected or not folder:
            print("Recuperación cancelada.")
            return
        args.checkpoint, args.audio_dir = Path(selected), Path(folder)
    result = recover_checkpoint_amounts(args.checkpoint, args.audio_dir, args.output_dir)
    print("Revisión del motor:", result["engine_revision"])
    print("Llamadas con oferta incompleta:", result["checked_calls"])
    print("Importes recuperados:", result["recovered_amounts"])
    print("Ventanas pendientes:", result["pending_windows"])
    print("Resultados:", result["outcomes"])
    print("Reporte nuevo:", result["report"])
    print("Checkpoint nuevo:", result["checkpoint"])
    print("Se conservaron los textos y archivos originales. Las lecturas adicionales no certifican autorización de descuentos.")


if __name__ == "__main__":
    main()
