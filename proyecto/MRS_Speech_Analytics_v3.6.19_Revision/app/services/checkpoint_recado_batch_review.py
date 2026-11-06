"""Registrar varios hechos de recado y recalcular una sola vez, en copia."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from app.services.recado_acceptance_review import (
    SCOPE, DELIVERY_SCOPE, make_recado_confirmation, make_recado_delivery_confirmation,
    validate_recado_confirmation)


def prepare_recado_selections(items, accepted_calls='', delivered_calls='', *,
                              acceptances_confirmed=False, messages_confirmed=False, callbacks_confirmed=False):
    """Números de llamada solo seleccionan; los hechos finales se ligan al archivo."""
    if not isinstance(items, list) or not items:
        raise ValueError('Seleccione un checkpoint completo con llamadas.')
    if accepted_calls.strip() and not re.fullmatch(r'[\d,\s]+', accepted_calls):
        raise ValueError('Escriba las llamadas de aceptación separadas por comas.')
    entries = [(int(n), {'scope': SCOPE, 'user_confirmed': acceptances_confirmed})
               for n in re.findall(r'\d+', accepted_calls)]
    for line in delivered_calls.splitlines():
        if not line.strip():
            continue
        number, separator, description = line.partition('|')
        if not separator or not number.strip().isdigit():
            raise ValueError('Cada recado con contacto debe indicar: número de llamada | descripción.')
        entries.append((int(number.strip()), {'scope': DELIVERY_SCOPE,
            'message_description': description.strip(), 'message_confirmed': messages_confirmed,
            'callback_confirmed': callbacks_confirmed}))
    if not entries:
        raise ValueError('Indique al menos una llamada ya comprobada.')
    seen = set(); selected = {}
    for number, fact in entries:
        if not 1 <= number <= len(items):
            raise ValueError(f'La llamada {number} no pertenece al checkpoint seleccionado.')
        if number in seen:
            raise ValueError(f'La llamada {number} está repetida; seleccione un solo alcance.')
        seen.add(number)
        item = items[number-1]
        name = item.get('file_name')
        if not name or name in selected:
            raise ValueError('Hay archivos ausentes o repetidos en la selección.')
        # Validar todos los hechos antes de abrir una carpeta o escribir datos.
        _make_record(item, fact)
        selected[name] = fact
    return selected


def _make_record(item, fact):
    if not isinstance(item, dict) or not isinstance(fact, dict):
        raise ValueError('La llamada o la confirmación no tienen un formato válido.')
    if fact.get('scope') == SCOPE:
        return make_recado_confirmation(item.get('result'), item.get('relation'),
                                        user_confirmed=fact.get('user_confirmed'))
    if fact.get('scope') == DELIVERY_SCOPE:
        return make_recado_delivery_confirmation(item.get('result'), item.get('relation'),
            fact.get('message_description'), message_confirmed=fact.get('message_confirmed'),
            callback_confirmed=fact.get('callback_confirmed'))
    raise ValueError('Alcance de confirmación no reconocido.')


def confirm_checkpoint_recados(checkpoint_path, selections, output_directory=None, *, expected_source_sha256=None):
    from app.services.checkpoint_output import create_checkpoint_output
    from app.services.checkpoint_reanalysis import reanalyze_checkpoint
    source = Path(checkpoint_path).expanduser().resolve(); raw = source.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    if expected_source_sha256 is not None and expected_source_sha256 != source_hash:
        raise ValueError('El checkpoint cambió después de revisar la selección. Ábralo de nuevo.')
    original = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(original, dict):
        raise ValueError('Seleccione un checkpoint completo con llamadas.')
    items = original.get('items') or []; master = {}
    if not items or not isinstance(selections, dict) or not selections:
        raise ValueError('Seleccione un checkpoint completo y al menos una confirmación.')
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('result'), dict):
            raise ValueError('El checkpoint contiene llamadas incompletas.')
        name = item.get('file_name'); data = item.get('result') or {}
        if (not name or name in master or data.get('archivo') != name
                or not str(data.get('texto') or '').strip()):
            raise ValueError('El checkpoint contiene archivos repetidos o datos incompletos.')
        master[name] = item
    if set(selections)-set(master):
        raise ValueError('La selección contiene llamadas ajenas al checkpoint.')
    records = {name: _make_record(master[name], fact) for name, fact in selections.items()}
    updated = deepcopy(original)
    for item in updated['items']:
        name = item['file_name']
        if name not in records:
            continue
        previous = item.get('recado_acceptance_confirmation'); current = records[name]
        valid = validate_recado_confirmation(item['result'], item['relation'], previous)
        if valid['valid'] and previous['record_sha256'] == current['record_sha256']:
            current = previous
        elif previous is not None:
            item.setdefault('recado_acceptance_confirmation_history', []).append(deepcopy(previous))
        item['recado_acceptance_confirmation'] = current
    target = create_checkpoint_output(output_directory, 'Recados_Lote_MRS_', nested_results=True)
    audit = target/'auditoria'; audit.mkdir()
    intermediate = audit/'entrada.json'
    updated['completed'] = False
    updated['recado_review_stage'] = 'INTERMEDIATE_NOT_REANALYZED'
    intermediate.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
    result = reanalyze_checkpoint(intermediate, target/'resultados')
    final_path = Path(result['checkpoint']); final = json.loads(final_path.read_text(encoding='utf-8'))
    if not final['completed'] or result['outcomes'].get('ERROR'):
        raise ValueError('El reanálisis no terminó completo; conserve el origen y revise los errores.')
    for item in final['items']:
        if item['file_name'] in selections and not item['analytics_metadata'].get('recado_acceptance_validation', {}).get('valid'):
            raise ValueError('Una confirmación no validó; conserve el origen y revise la salida.')
    if final.get('recado_batch_confirmation_import'):
        final.setdefault('recado_batch_confirmation_import_history', []).append(
            deepcopy(final['recado_batch_confirmation_import']))
    final['recado_batch_confirmation_import'] = {'source_checkpoint_sha256': source_hash,
        'confirmed_calls': len(selections), 'calls': [{'file_name': name, 'scope': fact['scope']}
                                                     for name, fact in selections.items()],
        'whisper_executed': False, 'audio_files_copied': False}
    final['recado_review_stage'] = 'FINAL_REANALYZED'
    final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
    from openpyxl import load_workbook
    book = load_workbook(result['report']); sheet = book.create_sheet('RECADOS_CONFIRMADOS')
    sheet.append(['Llamada', 'Archivo', 'Hecho confirmado por el usuario', 'Mensaje', 'Resultado'])
    for number, item in enumerate(final['items'], 1):
        if item['file_name'] not in selections:
            continue
        record = item['recado_acceptance_confirmation']
        sheet.append([number, item['file_name'], 'Recado y contacto entregados' if record['scope'] == DELIVERY_SCOPE
                      else 'Aceptación de recado', record.get('message_description', ''),
                      item['classification']['clasificacion']])
    book['NOTA_REANALISIS'].append(['Confirmaciones de recado registradas en una operación', len(selections)])
    book.save(result['report']); book.close()
    assert source.read_bytes() == raw, 'El origen cambió durante la revisión.'
    return dict(result, confirmed_calls=len(selections))
