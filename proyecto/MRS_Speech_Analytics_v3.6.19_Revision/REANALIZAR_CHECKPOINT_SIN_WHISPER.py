"""Reanalizar checkpoint del lote SIN ejecutar Whisper ni volver a copiar audios.

Con argumentos: python REANALIZAR_CHECKPOINT_SIN_WHISPER.py "ruta/checkpoint.json"
Sin argumentos: abre selector de archivos (Tkinter).
Genera una nueva carpeta en ~/MRS_Resultados; conserva el checkpoint original.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    window = None
    messagebox = None
    try:
        if len(sys.argv) > 1:
            checkpoint = Path(sys.argv[1]).expanduser()
        else:
            import tkinter as tk
            from tkinter import filedialog, messagebox as mb
            messagebox = mb
            window = tk.Tk()
            window.withdraw()
            selected = filedialog.askopenfilename(
                title="Selecciona el checkpoint que deseas reanalizar sin Whisper",
                filetypes=[("Checkpoint JSON", "*.json"), ("Todos los archivos", "*.*")],
            )
            if not selected:
                print("Operación cancelada; el checkpoint no se modificó.")
                return 0
            checkpoint = Path(selected)
        if not checkpoint.is_file():
            raise FileNotFoundError(f"No se encontró el checkpoint: {checkpoint}")
        from app.services.checkpoint_reanalysis import reanalyze_checkpoint
        print(f"Reanalizando reglas sobre transcripciones existentes: {checkpoint}")
        result = reanalyze_checkpoint(str(checkpoint), output_directory=None)
        output = (
            "REANÁLISIS TERMINADO (sin ejecutar Whisper)\n\n"
            f"Audios evaluados: {result['evaluations']}\n"
            f"Resultados: {result['outcomes']}\n"
            f"Reporte: {result['report']}\n"
            f"Checkpoint nuevo: {result['checkpoint']}\n\n"
            "El archivo original no fue sobrescrito."
        )
        print(output)
        if messagebox is not None:
            messagebox.showinfo("MRS · Reanálisis sin Whisper", output)
        return 0
    except Exception as error:
        import traceback
        traceback.print_exc()
        if messagebox is not None:
            messagebox.showerror("MRS · Error de reanálisis", str(error))
        return 1
    finally:
        if window is not None:
            window.destroy()


if __name__ == "__main__":
    raise SystemExit(main())
