"""Aceptación de recado confirmada por el usuario, sin sustituir la lectura ASR."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from app.services.audio_block_evidence import binding, digest

SCOPE = 'RECIPIENT_ACCEPTED_RECADO_ONLY'


def review_digest(record):
    return digest({k: record.get(k) for k in (
        'schema', 'scope', 'source_binding', 'source', 'user_confirmed', 'active')})


def make_recado_confirmation(data, relation, *, user_confirmed=False):
    if user_confirmed is not True:
        raise ValueError('La aceptación del recado requiere confirmación explícita del usuario.')
    if (not isinstance(data, dict) or not data.get('archivo')
            or not str(data.get('texto') or '').strip() or not isinstance(relation, dict)
            or not re.fullmatch(r'\d{16}', str(relation.get('numero_de_tarjeta') or ''))):
        raise ValueError('Faltan transcripción o tarjeta para vincular la confirmación.')
    record = {'schema': 1, 'scope': SCOPE, 'source_binding': binding(data, relation),
              'source': 'EXPLICIT_USER_RECADO_ACCEPTANCE_CONFIRMATION',
              'user_confirmed': True, 'active': True,
              'reviewed_at': datetime.now(timezone.utc).isoformat()}
    record['record_sha256'] = review_digest(record)
    return record


def validate_recado_confirmation(data, relation, record):
    status = {'present': record is not None, 'valid': False, 'review_required': False,
              'recipient_accepted': False, 'record': deepcopy(record)}
    if record is None:
        return status
    status.update(review_required=True,
                  reason='La confirmación de recado no corresponde a la llamada actual; revisar o revocar.')
    try:
        expected = make_recado_confirmation(data, relation, user_confirmed=record.get('user_confirmed'))
        if (record.get('active') is not True or record.get('record_sha256') != review_digest(record)
                or any(record.get(k) != expected[k] for k in
                       ('schema', 'scope', 'source_binding', 'source'))):
            return status
    except (ValueError, TypeError, AttributeError):
        return status
    status.update(valid=True, review_required=False, recipient_accepted=True)
    status.pop('reason', None)
    return status


def confirm_checkpoint_recado(checkpoint_path, file_name, output_directory=None, *, user_confirmed=False):
    from app.services.checkpoint_output import create_checkpoint_output
    from app.services.checkpoint_reanalysis import reanalyze_checkpoint
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
    record = make_recado_confirmation(item.get('result'), item.get('relation'), user_confirmed=user_confirmed)
    updated = deepcopy(original)
    target_item = updated['items'][index]
    previous = target_item.get('recado_acceptance_confirmation')
    if validate_recado_confirmation(item['result'], item['relation'], previous)['valid']:
        record = previous
    elif previous is not None:
        target_item.setdefault('recado_acceptance_confirmation_history', []).append(deepcopy(previous))
    target_item['recado_acceptance_confirmation'] = record
    target = create_checkpoint_output(output_directory, 'Confirmacion_Recado_MRS_', nested_results=True)
    intermediate = target/'checkpoint_con_recado_confirmado.json'
    intermediate.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
    result = reanalyze_checkpoint(intermediate, target/'resultados')
    final_path = Path(result['checkpoint'])
    final = json.loads(final_path.read_text(encoding='utf-8'))
    if not final['items'][index]['analytics_metadata'].get('recado_acceptance_validation', {}).get('valid'):
        raise ValueError('No se validó la confirmación; conserve el origen y revise la salida.')
    if final.get('recado_confirmation_import'):
        final.setdefault('recado_confirmation_import_history', []).append(deepcopy(final['recado_confirmation_import']))
    final['recado_confirmation_import'] = {'source_checkpoint_sha256': hashlib.sha256(raw).hexdigest(),
        'file_name': file_name, 'confirmed_calls': 1, 'scope': SCOPE,
        'whisper_executed': False, 'audio_files_copied': False}
    final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
    from openpyxl import load_workbook
    book = load_workbook(result['report'])
    book['NOTA_REANALISIS'].append(['Aceptación de recado confirmada por el usuario', file_name])
    book['NOTA_REANALISIS'].append(['La confirmación solo acredita aceptación; se mantienen las demás validaciones.'])
    book.save(result['report'])
    book.close()
    assert source.read_bytes() == raw, 'El origen cambió durante la confirmación.'
    return result
