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
    args = parser.parse_args()
    source = args.checkpoint
    if source is None:
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        selected = filedialog.askopenfilename(title="Seleccionar batch_checkpoint.json",
                                             filetypes=[("Checkpoint JSON", "*.json")])
        root.destroy()
        if not selected:
            print("Reanálisis cancelado.")
            return
        source = Path(selected)
    result = reanalyze_checkpoint(source, args.output_dir)
    print("Evaluaciones:", result["evaluations"])
    print("Resultados:", result["outcomes"])
    print("Reporte nuevo:", result["report"])
    print("Checkpoint nuevo:", result["checkpoint"])
    print("Se conservaron los originales. No se ejecutó Whisper ni se copiaron audios.")


if __name__ == "__main__":
    main()
