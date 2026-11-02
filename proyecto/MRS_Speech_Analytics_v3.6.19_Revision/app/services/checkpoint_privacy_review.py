"""Guardar divulgación confirmada en copia y recalcular con el motor habitual."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from app.services.checkpoint_output import create_checkpoint_output
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.privacy_disclosure_review import make_disclosure_confirmation, validate_disclosure_confirmation


def confirm_checkpoint_disclosure(checkpoint_path, file_name, evidence, output_directory=None, *,
                                 actor_confirmed=False, third_party_confirmed=False,home_warning=False,warning_confirmed=False):
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
    field='home_warning_confirmation' if home_warning else 'privacy_disclosure_confirmation'
    if home_warning:
        from app.services.home_warning_review import make_warning_confirmation,validate_warning_confirmation
        record=make_warning_confirmation(item.get('result') or {},item.get('relation') or {},evidence,
            actor_confirmed=actor_confirmed,warning_confirmed=warning_confirmed,audio_evidence=item.get('audio_block_evidence'))
        validate=validate_warning_confirmation
    else:
        record = make_disclosure_confirmation(item.get('result') or {}, item.get('relation') or {}, evidence,
            actor_confirmed=actor_confirmed, third_party_confirmed=third_party_confirmed,
            audio_evidence=item.get('audio_block_evidence'))
        validate=validate_disclosure_confirmation
    updated = deepcopy(original)
    target_item = updated['items'][index]
    previous = target_item.get(field)
    valid_previous = validate(item['result'], item.get('relation') or {},
        previous, item.get('audio_block_evidence'))
    if valid_previous['valid'] and previous['record_sha256'] == record['record_sha256']:
        record = previous
    elif previous is not None:
        history_field='home_warning_confirmation_history' if home_warning else 'privacy_disclosure_history'
        target_item.setdefault(history_field, []).append(deepcopy(previous))
    target_item[field] = record
    target = create_checkpoint_output(output_directory,
        'Confirmacion_Advertencia_MRS_' if home_warning else 'Confirmacion_Privacidad_MRS_', nested_results=True)
    intermediate = target/('checkpoint_con_advertencia_confirmada.json' if home_warning else 'checkpoint_con_divulgacion_confirmada.json')
    intermediate.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
    result = reanalyze_checkpoint(intermediate, target/'resultados')
    final_path = Path(result['checkpoint'])
    final = json.loads(final_path.read_text(encoding='utf-8'))
    confirmed=(final['items'][index]['analytics_metadata'].get('home_recovery_warning',{}).get('confirmed') if home_warning
               else final['items'][index]['analytics_metadata'].get('privacy_validation', {}).get('confirmed_disclosure'))
    if final['items'][index]['classification'].get('clasificacion') != 'FALLA_GRAVE' or not confirmed:
        raise ValueError('La confirmación no produjo el bloqueo crítico esperado; conserve el origen y revise la salida.')
    import_field='home_warning_confirmation_import' if home_warning else 'privacy_confirmation_import'
    if final.get(import_field):final.setdefault(import_field+'_history',[]).append(deepcopy(final[import_field]))
    final[import_field] = {'source_checkpoint_sha256': hashlib.sha256(raw).hexdigest(),
        'confirmed_calls': 1, 'file_name': file_name, 'scope': record['scope'],
        'whisper_executed': False, 'audio_files_copied': False}
    final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
    assert source.read_bytes() == raw, 'El origen cambió durante la confirmación.'
    return result
