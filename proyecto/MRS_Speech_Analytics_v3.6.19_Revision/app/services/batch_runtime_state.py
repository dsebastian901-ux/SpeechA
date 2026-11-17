"""Vigencia de cada dictamen y compatibilidad de transcripciones guardadas.

La versión de la cabecera indica el programa que guardó el lote, no que todas
sus llamadas hayan pasado por ese programa. La vigencia se acredita por llamada.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    default=str).encode('utf-8')).hexdigest()


@lru_cache(maxsize=1)
def engine_fingerprint():
    root = Path(__file__).resolve().parents[1]
    result = hashlib.sha256()
    for directory in ('services', 'models', 'config'):
        for path in sorted((root / directory).rglob('*')):
            if path.is_file() and path.suffix in {'.py', '.json', '.yaml', '.yml'}:
                result.update(path.relative_to(root).as_posix().encode())
                result.update(path.read_bytes().replace(b'\r\n', b'\n'))
    return result.hexdigest()


def evaluation_inputs(item):
    metadata = item.get('analytics_metadata') or {}
    proof = {key: value for key, value in item.items()
             if key.endswith(('_confirmation', '_audio_review')) or key == 'audio_block_evidence'}
    proof['hostile_interlocutor_exception'] = metadata.get('hostile_interlocutor_exception')
    for key in ('amount_recovery_validation', 'financial_review_validation'):
        proof[key] = (metadata.get(key) or {}).get('human_review_record')
    return {'result': item.get('result'), 'relation': item.get('relation'), 'proof': proof,
            'context_asr_recovery':item.get('context_asr_recovery')}


def source_state(item, output_directory):
    """Detectar sustituciones del audio o del JSON entre ejecuciones sin alterarlos."""
    state = {}
    audio = Path(item.get('path') or '')
    if audio.is_file():
        stat = audio.stat()
        state['audio'] = [stat.st_size, stat.st_mtime_ns]
    if output_directory:
        sidecar = Path(output_directory) / (audio.stem + '.json')
        if sidecar.is_file():
            state['sidecar_sha256'] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    return state


def make_stamp(item, context, output_directory):
    return {**context, 'input_sha256': digest(evaluation_inputs(item)),
            'source': source_state(item, output_directory)}


def is_current(item, context, output_directory):
    return (item.get('status') == 'completado'
            and item.get('evaluation_stamp') == make_stamp(item, context, output_directory))


def compatible_transcription(data, item, runtime):
    if not isinstance(data, dict) or 'texto' not in data:
        return False
    # El nombre completo distingue ejemplo.ogg de ejemplo.wav.
    name = str(data.get('archivo') or '').replace('\\', '/').rsplit('/', 1)[-1]
    if name.casefold() != Path(item['path']).name.casefold():
        return False
    old_path = str(data.get('ruta_audio') or '')
    if old_path:
        normalized = lambda p: str(p).replace('\\', '/').rstrip('/').casefold()
        if normalized(old_path) != normalized(item['path']):
            return False
    fields = {'model': 'modelo', 'language': 'idioma_solicitado',
              'device': 'dispositivo', 'compute_type': 'tipo_calculo',
              'beam_size': 'beam_size', 'vad_filter': 'vad_filter',
              'word_timestamps': 'word_timestamps'}
    for requested, saved in fields.items():
        if saved in data and requested in runtime and data[saved] is not None:
            if str(data[saved]).casefold() != str(runtime[requested]).casefold():
                return False
    # Los JSON antiguos sin configuración siguen siendo recuperables; no se les
    # atribuye retrospectivamente el modelo seleccionado.
    return True
