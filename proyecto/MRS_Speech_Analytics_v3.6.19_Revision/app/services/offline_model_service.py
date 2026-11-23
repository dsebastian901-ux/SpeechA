"""Localizar Whisper sin descargas, incluido el tokenizer que evita otra descarga."""
from pathlib import Path

from app.config.settings import DATA_DIR


def local_model_source(name):
    selected = Path(str(name)).expanduser()
    candidates = [selected] if selected.is_dir() else []
    if selected.name == str(name):
        candidates += [DATA_DIR/'models'/str(name), Path(__file__).resolve().parents[1]/'resources/models'/str(name)]
    model = next((p for p in candidates if p.is_dir()), None)
    if model is None:
        # El nombre de la función es histórico en Faster-Whisper. Con este
        # parámetro exclusivamente consulta su caché; no solicita la red.
        from faster_whisper.utils import download_model
        try:
            model = Path(download_model(str(name), local_files_only=True))
        except Exception as error:
            raise FileNotFoundError(f"Modelo '{name}' no disponible localmente. La administradora debe importar el modelo completo mediante USB.") from error
    required = ['config.json', 'model.bin', 'tokenizer.json']
    missing = [f for f in required if not (model/f).is_file() or (model/f).stat().st_size == 0]
    if missing:
        raise FileNotFoundError('Modelo local incompleto: '+', '.join(missing)+'. Importe los archivos faltantes por USB; no se realizarán descargas.')
    from app.services.local_model_catalog import imported_model_info
    imported_model_info(model,verify=True)
    return str(model.resolve())


def local_model_identity(name):
    """Token local barato para detectar una importación sin descargar ni cargar pesos."""
    selected=Path(str(name)).expanduser()
    candidates=[selected]if selected.is_dir()else[]
    if selected.name==str(name):candidates += [DATA_DIR/'models'/str(name),Path(__file__).resolve().parents[1]/'resources/models'/str(name)]
    for folder in candidates:
        if folder.is_dir():
            return tuple((file,(folder/file).stat().st_size,(folder/file).stat().st_mtime_ns)
                         for file in ['model.bin','config.json','tokenizer.json','mrs_model_manifest.json']if(folder/file).is_file())
    return None
