"""Reconstruir una base con archivos locales; no descargar datos ni ejecutar ASR."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.account_source_validation import corrected_account_name, validate_account_source
from app.services.audio_block_evidence import attach_audio_block, binding, validate_evidence
from app.services.checkpoint_reanalysis import reanalyze_checkpoint


def read_json(path):
    return json.loads(Path(path).read_bytes().decode('utf-8-sig'))


def needs_source_checkpoint(checkpoint_path, evidence_path):
    """r23 necesita su origen si no puede acreditarse el contexto por llamada."""
    master = read_json(checkpoint_path)
    receipt = read_json(evidence_path)
    if receipt.get('source_checkpoint_sha256') == hashlib.sha256(Path(checkpoint_path).read_bytes()).hexdigest():
        return False
    items = {i['file_name']: i for i in master.get('items') or []}
    return not all(r.get('file_name') in items and r.get('source_binding') == binding(
        items[r['file_name']].get('result') or {}, items[r['file_name']].get('relation') or {})
        for r in receipt.get('items') or [])


def rebuild_checkpoint(checkpoint_path, evidence_path=None, *, source_checkpoint=None,
                       output_directory=None, use_excel_card=False,
                       expected_calls=None, expected_readings=None):
    source = Path(checkpoint_path).expanduser().resolve()
    raw = source.read_bytes()
    original = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(original, dict) or not isinstance(original.get('items'), list) or not original['items']:
        raise ValueError('Seleccione el checkpoint completo, no el JSON de lecturas.')
    items = original['items']
    if expected_calls is not None and len(items) != expected_calls:
        raise ValueError(f'Se esperaban {expected_calls} llamadas en el lote completo.')
    names = [i.get('file_name') for i in items]
    if not all(names) or len(set(names)) != len(names):
        raise ValueError('Hay nombres ausentes o duplicados en el lote.')
    updated = deepcopy(original)
    corrected = []
    existing_readings = set()
    for item in updated['items']:
        data, relation = item.get('result') or {}, item.get('relation') or {}
        if data.get('archivo') != item['file_name'] or not str(data.get('texto') or '').strip():
            raise ValueError('Una llamada no contiene transcripción válida vinculada a su archivo.')
        if validate_account_source(relation)['review_required']:
            if not use_excel_card:
                raise ValueError('Para corregir nombres indique usar numero_de_tarjeta del Excel.')
            if item.get('output_name_review'):
                raise ValueError('Hay una revisión de nombre incompatible; no se sobrescribe.')
            name = corrected_account_name(relation)
            item['output_name_review'] = {'reviewed_at': datetime.now(timezone.utc).isoformat(),
                'source': 'EXPLICIT_USER_CHOICE_NUMERO_DE_TARJETA',
                'previous_name': relation['nombre_final'], 'corrected_name': name}
            relation['nombre_final'] = name
            corrected.append(item['file_name'])
        record = item.get('audio_block_evidence')
        if record is not None:
            if not validate_evidence(record, data, relation, 'NO DETERMINADO')['valid']:
                raise ValueError('Una lectura existente no corresponde a su cuenta o fue modificada.')
            existing_readings.add(item['file_name'])
    receipt = read_json(evidence_path) if evidence_path is not None else None
    if receipt is not None:
        if not isinstance(receipt, dict) or receipt.get('schema') != 1 or not receipt.get('items'):
            raise ValueError('Seleccione revision_audios_bloque.json con las lecturas completadas.')
        receipt_names = [r.get('file_name') for r in receipt['items']]
        if not all(receipt_names) or len(set(receipt_names)) != len(receipt_names) or set(receipt_names)-set(names):
            raise ValueError('Las lecturas están duplicadas o no pertenecen al lote.')
        existing_readings.update(receipt_names)
    if not existing_readings:
        raise ValueError('Faltan las lecturas adicionales: seleccione revision_audios_bloque.json.')
    if expected_readings is not None and len(existing_readings) != expected_readings:
        raise ValueError(f'Se esperaban {expected_readings} lecturas adicionales vinculadas.')
    updated['local_checkpoint_rebuild'] = {
        'source_checkpoint_sha256': hashlib.sha256(raw).hexdigest(),
        'output_names_corrected': len(corrected), 'linked_readings_expected': len(existing_readings),
        'naming_policy': 'USER_AUTHORIZED_NUMERO_DE_TARJETA' if use_excel_card else 'PRESERVE_NAMES',
        'new_human_audio_confirmations': 0, 'whisper_executed': False,
        'scope': 'EXISTING_LOCAL_EVIDENCE_AND_AUTHORIZED_OUTPUT_NAMES_ONLY'}
    # Copia temporal breve: conserva originales y evita anidar las salidas.
    with TemporaryDirectory(prefix='MRS_base_') as temporary:
        intermediate = Path(temporary)/'base.json'
        intermediate.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
        if evidence_path is not None:
            origin = source_checkpoint
            if receipt.get('source_checkpoint_sha256') == hashlib.sha256(raw).hexdigest():
                origin = source
            result = attach_audio_block(intermediate, evidence_path, output_directory,
                                        source_checkpoint=origin)
        else:
            result = reanalyze_checkpoint(intermediate, output_directory)
    path = Path(result['checkpoint'])
    final = read_json(path)
    if result['outcomes'].get('ERROR'):
        raise ValueError('Una llamada no pudo reanalizarse; revise el detalle generado antes de usar la base.')
    for old, new in zip(original['items'], final['items']):
        for field in ('result', 'amount_audio_review', 'financial_audio_review', 'amount_review_history',
                      'financial_review_history'):
            assert old.get(field) == new.get(field), f'Cambió evidencia original: {field}'
        assert {k:v for k,v in old.get('relation', {}).items() if k != 'nombre_final'} == {
            k:v for k,v in new.get('relation', {}).items() if k != 'nombre_final'}
    revision = result['engine_revision'].rsplit('-', 1)[-1]
    filename = f'Checkpoint_{revision}_95_Audios.json' if len(items) == 95 else f'Checkpoint_{revision}_Recuperado.json'
    destination = path.with_name(filename)
    if destination.exists():
        raise ValueError('No se sobrescriben checkpoints existentes.')
    path.rename(destination)
    from openpyxl import load_workbook
    book = load_workbook(result['report'])
    note = book['NOTA_REANALISIS']
    note.append(['Base reconstruida con archivos locales; no se descargaron ni subieron datos.'])
    note.append(['Nombres corregidos según numero_de_tarjeta previamente autorizado', len(corrected)])
    note.append(['Lecturas adicionales vinculadas en la base', len(existing_readings)])
    note.append(['Confirmaciones nuevas de escucha humana', 0])
    book.save(result['report'])
    book.close()
    assert source.read_bytes() == raw, 'El checkpoint de entrada cambió.'
    return dict(result, checkpoint=str(destination), output_names_corrected=len(corrected),
                linked_readings=len(existing_readings))
