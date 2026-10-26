"""Carpetas independientes para evitar rutas acumuladas al revisar un lote."""
import os
from pathlib import Path
import tempfile


WINDOWS = os.name == "nt"
# Margen por debajo de MAX_PATH, incluida la copia temporal del reporte Excel.
WINDOWS_PATH_BUDGET = 240


def default_output_root():
    return Path.home() / "MRS_Resultados"


def _check_path_length(target, nested_results):
    results = target / "resultados" if nested_results else target
    paths = [results / "04_Reportes" / "Reporte_Reanalisis_Reglas_nuevo.xlsx",
             target / "checkpoint_con_validacion.json",
             target / "Datos_Cuentas_Corregidos.xlsx"]
    if WINDOWS and any(len(str(path).encode("utf-16-le")) // 2 >= WINDOWS_PATH_BUDGET for path in paths):
        raise ValueError(
            "La ruta de salida es demasiado larga para Windows. "
            "Elija una carpeta corta con --output-dir, por ejemplo C:\\MRS_Resultados. "
            "El checkpoint original permanece intacto.")


def create_checkpoint_output(output_directory, prefix, *, nested_results=False):
    if output_directory is None:
        base = default_output_root().expanduser().resolve()
        _check_path_length(base / (prefix + "00000000"), nested_results)
        base.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=prefix, dir=base))
    target = Path(output_directory).expanduser().resolve()
    _check_path_length(target, nested_results)
    if target.exists() and any(target.iterdir()):
        raise ValueError("Seleccione una carpeta de salida nueva y vacía; no se sobrescriben archivos.")
    target.mkdir(parents=True, exist_ok=True)
    return target
