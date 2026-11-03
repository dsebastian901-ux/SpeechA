"""Hechos de recado confirmados por el usuario, separados de la lectura ASR."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from app.services.audio_block_evidence import binding, digest
from app.services.conversation_evidence import assess_privacy

SCOPE = 'RECIPIENT_ACCEPTED_RECADO_ONLY'
DELIVERY_SCOPE = 'RECADO_AND_CALLBACK_DELIVERED_ONLY'


def review_digest(record):
    keys = ('schema', 'scope', 'source_binding', 'source', 'user_confirmed', 'active')
    if record.get('scope') == DELIVERY_SCOPE:
        keys += ('message_description', 'message_confirmed', 'callback_confirmed')
    return digest({k: record.get(k) for k in keys})


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


def make_recado_delivery_confirmation(data, relation, message_description, *,
                                     message_confirmed=False, callback_confirmed=False):
    if message_confirmed is not True or callback_confirmed is not True:
        raise ValueError('Confirme por separado la entrega del recado y del contacto para el titular.')
    if (not isinstance(message_description, str) or not 5 <= len(message_description.strip()) <= 500):
        raise ValueError('Describa el recado escuchado, entre 5 y 500 caracteres.')
    record = make_recado_confirmation(data, relation, user_confirmed=True)
    record.update(scope=DELIVERY_SCOPE, source='EXPLICIT_USER_RECADO_DELIVERY_CONFIRMATION',
                  message_description=message_description.strip(), message_confirmed=True, callback_confirmed=True)
    record['record_sha256'] = review_digest(record)
    return record


def validate_recado_confirmation(data, relation, record):
    status = {'present': record is not None, 'valid': False, 'review_required': False,
              'recipient_accepted': False, 'message_delivered': False,
              'callback_delivered': False, 'record': deepcopy(record)}
    if record is None:
        return status
    status.update(review_required=True,
                  reason='La confirmación de recado no corresponde a la llamada actual; revisar o revocar.')
    try:
        if record.get('scope') == DELIVERY_SCOPE:
            expected = make_recado_delivery_confirmation(data, relation, record.get('message_description'),
                message_confirmed=record.get('message_confirmed'), callback_confirmed=record.get('callback_confirmed'))
        else:
            expected = make_recado_confirmation(data, relation, user_confirmed=record.get('user_confirmed'))
        if (record.get('active') is not True or record.get('record_sha256') != review_digest(record)
                or any(record.get(k) != expected[k] for k in
                       ('schema', 'scope', 'source_binding', 'source', 'user_confirmed'))):
            return status
    except (ValueError, TypeError, AttributeError):
        return status
    delivered = expected['scope'] == DELIVERY_SCOPE
    status.update(valid=True, review_required=False, recipient_accepted=not delivered,
                  message_delivered=delivered, callback_delivered=delivered)
    status.pop('reason', None)
    if delivered:
        description = expected['message_description']
        privacy = assess_privacy(description, [{'text': description, 'speaker_role': 'GESTOR'}],
                                 third_party_confirmed=True)
        if privacy['confirmed_disclosure'] or privacy['review_required']:
            # Este alcance acredita entrega, no autoriza contenido financiero.
            # Una descripción humana puede ser un resumen y no una cita literal:
            # se revisa, sin inventar PEN003 ni certificar la atribución completa.
            status.update(review_required=True,
                reason='El recado descrito contiene información financiera por verificar; '
                       'la confirmación de entrega no exime privacidad.')
    return status


def confirm_checkpoint_recado(checkpoint_path, file_name, output_directory=None, *, user_confirmed=False,
                              message_description=None, message_confirmed=False, callback_confirmed=False):
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
    if message_description is None:
        record = make_recado_confirmation(item.get('result'), item.get('relation'), user_confirmed=user_confirmed)
    else:
        record = make_recado_delivery_confirmation(item.get('result'), item.get('relation'), message_description,
            message_confirmed=message_confirmed, callback_confirmed=callback_confirmed)
    updated = deepcopy(original)
    target_item = updated['items'][index]
    previous = target_item.get('recado_acceptance_confirmation')
    if (validate_recado_confirmation(item['result'], item['relation'], previous)['valid']
            and previous['record_sha256'] == record['record_sha256']):
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
        'file_name': file_name, 'confirmed_calls': 1, 'scope': record['scope'],
        'whisper_executed': False, 'audio_files_copied': False}
    final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
    from openpyxl import load_workbook
    book = load_workbook(result['report'])
    book['NOTA_REANALISIS'].append([
        'Recado y contacto entregados, confirmados por el usuario' if record['scope'] == DELIVERY_SCOPE
        else 'Aceptación de recado confirmada por el usuario', file_name])
    book['NOTA_REANALISIS'].append(['Alcance de la confirmación', record['scope']])
    book['NOTA_REANALISIS'].append(['Se conservan las transcripciones y las demás validaciones.'])
    book.save(result['report'])
    book.close()
    assert source.read_bytes() == raw, 'El origen cambió durante la confirmación.'
    return result
