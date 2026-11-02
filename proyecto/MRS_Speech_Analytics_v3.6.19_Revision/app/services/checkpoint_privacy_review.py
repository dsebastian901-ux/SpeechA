"""Guardar divulgación confirmada en copia y recalcular con el motor habitual."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from app.services.checkpoint_output import create_checkpoint_output
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.privacy_disclosure_review import make_disclosure_confirmation, validate_disclosure_confirmation


def confirm_checkpoint_disclosure(checkpoint_path, file_name, evidence, output_directory=None, *,
                                 actor_confirmed=False, third_party_confirmed=False):
    source = Path(checkpoint_path).expanduser().resolve()
    raw = source.read_bytes()
    original = json.loads(raw.decode('utf-8-sig'))
    items = original.get('items') or []
    names = [i.get('file_name') for i in items]
    if not names or not all(names) or len(set(names)) != len(names) or file_name not in names:
        raise ValueError('Seleccione un checkpoint completo con llamadas únicas y la llamada correcta.')
    index = names.index(file_name)
    item = items[index]
    if item.get('result', {}).get('archivo') != file_name:
        raise ValueError('El nombre interno de la llamada no coincide con el checkpoint.')
    record = make_disclosure_confirmation(item.get('result') or {}, item.get('relation') or {}, evidence,
        actor_confirmed=actor_confirmed, third_party_confirmed=third_party_confirmed,
        audio_evidence=item.get('audio_block_evidence'))
    updated = deepcopy(original)
    target_item = updated['items'][index]
    previous = target_item.get('privacy_disclosure_confirmation')
    valid_previous = validate_disclosure_confirmation(item['result'], item.get('relation') or {},
        previous, item.get('audio_block_evidence'))
    if valid_previous['valid'] and previous['record_sha256'] == record['record_sha256']:
        record = previous
    elif previous is not None:
        target_item.setdefault('privacy_disclosure_history', []).append(deepcopy(previous))
    target_item['privacy_disclosure_confirmation'] = record
    target = create_checkpoint_output(output_directory, 'Confirmacion_Privacidad_MRS_', nested_results=True)
    intermediate = target/'checkpoint_con_divulgacion_confirmada.json'
    intermediate.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
    result = reanalyze_checkpoint(intermediate, target/'resultados')
    final_path = Path(result['checkpoint'])
    final = json.loads(final_path.read_text(encoding='utf-8'))
    if (final['items'][index]['classification'].get('clasificacion') != 'FALLA_GRAVE'
            or not final['items'][index]['analytics_metadata'].get('privacy_validation', {}).get('confirmed_disclosure')):
        raise ValueError('La confirmación no produjo el bloqueo crítico esperado; conserve el origen y revise la salida.')
    final['privacy_confirmation_import'] = {'source_checkpoint_sha256': hashlib.sha256(raw).hexdigest(),
        'confirmed_calls': 1, 'file_name': file_name, 'scope': record['scope'],
        'whisper_executed': False, 'audio_files_copied': False}
    final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
    assert source.read_bytes() == raw, 'El origen cambió durante la confirmación.'
    return result
