"""Abrir la GUI y comprobar la validación de trato, sin modificar llamadas."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import customtkinter as ctk
from app.core.application import SpeechAnalyticsApplication
from app.models.transcriptions import TranscriptionModel
from app.ui.views.analytics_view import AnalyticsView


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def main():
    with tempfile.TemporaryDirectory(prefix="mrs-gui-") as directory:
        path = Path(directory)/"synthetic.json"
        path.write_text(json.dumps({"archivo": "synthetic.wav", "texto": "Habla MRS."}), encoding="utf-8")
        app = SpeechAnalyticsApplication()
        try:
            app.window.update()
            assert app.window.winfo_exists()
            container = ctk.CTkToplevel(app.window)
            container.geometry("1100x760")
            view = AnalyticsView(container)
            view.pack(fill="both", expand=True)
            view.selected_transcription = TranscriptionModel("synthetic.wav", "synthetic.wav", "Habla MRS.", json_path=str(path))
            app.window.update()
            view.validate_treatment()
            app.window.update()
            checks = [w for w in descendants(container) if isinstance(w, ctk.CTkCheckBox)]
            assert len(checks) == 4 and all(w.get() == 0 for w in checks)
            app.window.after(300, app.window.quit)
            app.run()
        finally:
            app.window.destroy()
    print("GUI y diálogo de validación de trato comprobados; sin confirmaciones preseleccionadas.")


if __name__ == "__main__":
    main()
