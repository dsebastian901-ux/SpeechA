"""Comprobación local de arranque. No abre GUI, modelos ni cuentas.

Se ejecuta con cada Python candidato antes de importar la aplicación.
No instala paquetes ni descarga dependencias o pesos de Whisper.
"""
import importlib
import struct
import sys


COMPONENTS = (
    ('tkinter', 'Tkinter incluido con Python'),
    ('customtkinter', 'customtkinter'),
    ('PIL.Image', 'Pillow'),
    ('openpyxl', 'openpyxl'),
    ('faster_whisper', 'faster-whisper'),
    ('av', 'av'),
    ('imageio_ffmpeg', 'imageio-ffmpeg'),
    ('docx', 'python-docx'),
    ('cryptography.hazmat.primitives.asymmetric.ed25519', 'cryptography'),
)


def missing_components(importer=None):
    importer = importlib.import_module if importer is None else importer
    missing = []
    for module, package in COMPONENTS:
        try:
            importer(module)
        except Exception as error:
            # Una dependencia presente con DLL incompatible tampoco sirve
            # para arrancar; no ocultar esa diferencia como instalacion lista.
            missing.append((package, type(error).__name__, str(error)))
    return missing


def main():
    print('Python comprobado: ' + sys.executable, flush=True)
    if sys.version_info < (3, 10) or struct.calcsize('P') != 8:
        print('Se necesita Python 3.10 o posterior de 64 bits.')
        return 1
    missing = missing_components()
    for package, kind, reason in missing:
        print('  No disponible: ' + package + ' (' + kind + ': ' + reason + ')')
    if missing:
        return 1
    print('Componentes locales verificados. No se descargaron modelos ni paquetes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
