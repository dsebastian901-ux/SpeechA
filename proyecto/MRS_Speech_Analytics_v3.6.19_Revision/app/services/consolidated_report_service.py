"""Consolidación local de lotes: reportar resultados guardados, sin red ni redictamen."""
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import uuid
import zipfile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.services.nonpayment_report_service import detect_nonpayment

DAYS = ('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo')
MAX_INPUT = 128 * 1024 * 1024
MOTIVE_ADVICE = {
    'DESEMPLEO': 'Escuchar la situación y explorar alternativas permitidas por la mora y los datos del Excel, sin asumir negativa ni prometer condiciones no autorizadas.',
    'FALTA_DE_LIQUIDEZ': 'Explorar capacidad y fecha de ingreso; validar importes y plazos por mora antes de confirmar un acuerdo.',
    'INGRESOS_INSUFICIENTES': 'Revisar alternativas autorizadas y aceptación real del cliente; no confirmar montos inviables unilateralmente.',
    'SALUD_O_ACCIDENTE': 'Atender con empatía, evitar solicitar información médica innecesaria y seguir el protocolo aplicable.',
    'ESPERA_INGRESO_O_QUINCENA': 'Relacionar fecha de ingreso y plazo autorizado por mora; no extender vencimientos ni confirmar acuerdos sin aceptación.',
    'OLVIDO_DE_PAGO': 'Reforzar claridad de fecha, importe y canales oficiales; comprobar comprensión y consentimiento para seguimiento.',
    'DESCONOCE_O_DISPUTA_ADEUDO': 'Canalizar la aclaración con evidencia y trato respetuoso; no presentar la disputa como negativa confirmada.',
    'IMPEDIMENTO_PARA_PAGAR': 'Identificar la barrera y explicar opciones oficiales disponibles y convenios correctos, sin inventar establecimientos.',
    'NEGATIVA_EXPRESA': 'Mantener trato profesional, registrar la declaración y seguir el protocolo sin amenazas ni hostigamiento.',
}

CALL_HEADERS = ['Fecha llamada', 'Día', 'Tarjeta Excel', 'Gestor', 'Supervisor', 'Archivo audio',
                'Clasificación reportada', 'Puntaje', 'Motivo no pago', 'Falla grave reportada', 'Lote origen']
ERROR_HEADERS = CALL_HEADERS + ['Código error', 'Categoría error', 'Descripción error', 'Grave',
                                'Evidencia localizada', 'Ventana ASR (s)', 'Contexto ASR (no prueba del error)']
ADVICE = {
    'PEN003': 'Reforzar identificación del interlocutor y límites de divulgación a terceros. Validar voz y destinatario antes de atribuir la falta.',
    'PEN001': 'Reforzar presentación del despacho; contrastar variantes de MRS en el audio antes de confirmar omisión.',
    'PEN_ARCO_OMISION': 'Practicar el proceso completo ARCO: derechos, correo oficial, identificación y comprobante de línea cuando corresponda.',
    'PEN_GROSERIA_GESTOR': 'Atención inmediata al trato profesional y cierre de llamada; revisar evidencia y responsable.',
    'PEN_GROSERIA_SIN_ATRIBUCION': 'Escuchar el cierre completo y confirmar quién usa la expresión antes de atribuir responsabilidad.',
    'PEN_QUEJA_MALTRATO': 'Revisar la queja y recuperar la llamada previa; atender al cliente sin aprobar ni culpar automáticamente al gestor actual.',
    'PEN_ESPERA_PROLONGADA': 'Retomar contacto antes de 65 segundos; revisar el intervalo y diferenciar espera de cola posterior a la despedida.',
    'PEN_CONV_LUGARES': 'Contrastar la lista completa y reforzar dos establecimientos autorizados distintos cuando aplique, sin duplicar marcas.',
    'PEN_CONV_WHATSAPP': 'Reforzar solicitud del ticket/comprobante y especificación del canal; contrastar expresiones equivalentes en audio.',
    'PEN012': 'Reforzar la prohibición de amenazas de visitas/diligencias en cuentas de 1–2 PV y revisar la atribución del hablante.',
}


def _json(data):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d: raise ValueError('El archivo contiene claves JSON duplicadas.')
            d[k] = v
        return d
    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=unique)


def _date(value):
    if not value: return None
    if isinstance(value, datetime): return value.date()
    if isinstance(value, date): return value
    value = str(value).strip()
    try: return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
    except ValueError: pass
    for fmt in ('%d/%m/%Y', '%d/%m/%Y %H:%M:%S', '%Y%m%d'):
        try: return datetime.strptime(value, fmt).date()
        except ValueError: pass
    return None


def _updated(value):
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
    except (TypeError, ValueError, OverflowError): return None


def _base(value):
    return str(value or '').replace('\\', '/').rsplit('/', 1)[-1]


def _evidence(metadata, code):
    if code == 'PEN003': candidates = (metadata.get('privacy_validation') or {}).get('evidence') or []
    elif code == 'PEN_ESPERA_PROLONGADA': candidates = (metadata.get('wait_validation') or {}).get('intervals') or []
    elif code == 'PEN_QUEJA_MALTRATO': candidates = (metadata.get('treatment_validation') or {}).get('mistreatment_report_evidence') or []
    elif code.startswith('PEN_GROSERIA'): candidates = (metadata.get('treatment_validation') or {}).get('offensive_language_evidence') or []
    else: candidates = []
    if isinstance(candidates, dict): candidates = [candidates]
    if isinstance(candidates, str): return candidates, ''
    texts, windows = [], []
    for e in candidates:
        if not isinstance(e, dict): continue
        text = e.get('text') or e.get('phrase') or e.get('before_text') or ''
        if text and text not in texts: texts.append(str(text))
        a, b = e.get('start', e.get('inicio')), e.get('end', e.get('fin'))
        if a is not None and b is not None: windows.append(f'{a}–{b}')
    return ' | '.join(texts), ' | '.join(dict.fromkeys(windows))


def _record(item, source):
    relation = item.get('relation') or {}
    result = item.get('result') or {}
    analytics = item.get('analytics') or {}
    if not all(isinstance(v, dict) for v in (relation, result, analytics)):
        raise ValueError('Una llamada contiene datos de cuenta o análisis con formato inválido.')
    metadata = item.get('analytics_metadata') or analytics.get('metadata') or {}
    classification = item.get('classification') or metadata.get('shared_classification') or {}
    if not all(isinstance(v, dict) for v in (relation, result, analytics, metadata, classification)):
        raise ValueError('Una llamada contiene datos de cuenta o dictamen con formato inválido.')
    filename = _base(relation.get('archivo_original') or item.get('file_name') or result.get('archivo') or item.get('path'))
    if not filename: raise ValueError('Una llamada carece de identificador de audio.')
    actual_date = _date(relation.get('fecha'))
    date_basis = 'Excel: fecha' if actual_date else ''
    if not actual_date:
        for m in re.finditer(r'(?<!\d)(20\d{6})(?:\d{6})?(?!\d)', filename):
            actual_date = _date(m[1])
            if actual_date: date_basis = 'Fecha en nombre de audio'; break
    card = str(relation.get('numero_de_tarjeta') or '').strip()
    raw_class = str(classification.get('clasificacion') or metadata.get('final_result') or
                    ('ERROR' if item.get('status') == 'error' else 'SIN DICTAMEN')).upper()
    failures = metadata.get('critical_failures') or []
    penalties = metadata.get('penalties') or []
    errors = {}
    for p in [*penalties, *failures]:
        if not isinstance(p, dict): continue
        code = str(p.get('id') or 'SIN_CODIGO')
        e = errors.setdefault(code, {'code': code, 'category': str(p.get('category') or 'Sin categoría'),
                                    'reasons': [], 'grave': False})
        reason = str(p.get('reason') or 'Sin descripción en origen')
        if reason not in e['reasons']: e['reasons'].append(reason)
        e['grave'] = e['grave'] or p.get('invalidates') is True
    severe = raw_class == 'FALLA_GRAVE' or any(e['grave'] for e in errors.values())
    if severe and not any(e['grave'] for e in errors.values()):
        errors['GRAVE_SIN_DESGLOSE'] = {'code': 'GRAVE_SIN_DESGLOSE', 'category': 'Sin desglose',
            'reasons': ['FALLA_GRAVE en origen sin criterio desglosado; recuperar evidencia.'], 'grave': True}
    for e in errors.values():
        e['evidence'], e['window'] = _evidence(metadata, e['code'])
        e['reason'] = ' | '.join(e.pop('reasons'))
    motive = detect_nonpayment(item)
    record = {'file': filename, 'card': card, 'gestor': str(relation.get('gestor') or 'SIN GESTOR'),
              'supervisor': str(relation.get('supervisor') or 'SIN SUPERVISOR'), 'date': actual_date,
              'date_basis': date_basis, 'classification': raw_class,
              'score': item.get('compliance_score', analytics.get('compliance_score')),
              'motive': motive['primary'], 'motive_evidence': ' | '.join(dict.fromkeys(e['text'] for e in motive['evidence'])),
              'motive_basis': motive['origin'], 'severe': severe, 'errors': list(errors.values()),
              'source': source['name'], 'source_hash': source['sha256'], 'updated': source['updated'],
              'context': str(result.get('texto') or '')[:500],
              'original_excel': relation.get('datos_excel_original') or relation,
              'processing': item.get('status') or 'SIN ESTADO'}
    call_id = str(relation.get('id_llamada') or '').strip()
    # Un nombre grabación con fecha/ID o un id_llamada es estable ante reanálisis.
    if call_id: identity = ('id', call_id)
    elif re.search(r'(?<!\d)20\d{12}(?!\d)', filename) or (re.search(r'(?<!\d)20\d{6}(?!\d)', filename) and re.search(r'\d{16,}', filename)):
        identity = ('audio', filename.casefold())
    elif card and actual_date: identity = ('cuenta_fecha_audio', card, actual_date.isoformat(), filename.casefold())
    else: identity = None
    record['identity'] = identity
    return record


def _call_row(r):
    return [r['date'].isoformat() if r['date'] else '', DAYS[r['date'].weekday()] if r['date'] else '',
            r['card'], r['gestor'], r['supervisor'], r['file'], r['classification'], r['score'],
            r['motive'], 'SI' if r['severe'] else 'NO', r['source']]


def _error_rows(calls, severe_only=False):
    for r in calls:
        for e in r['errors']:
            if not severe_only or e['grave']:
                yield r, e, _call_row(r) + [e['code'], e['category'], e['reason'], 'SI' if e['grave'] else 'NO',
                                           e['evidence'], e['window'], r['context']]


def _groups(calls, keys):
    grouped = defaultdict(list)
    for r in calls: grouped[tuple(r[k] for k in keys)].append(r)
    return [(key, values) for key, values in sorted(grouped.items())]


def _approved(category):
    return category.startswith('APROBADO') or category == 'APROBADA'


def _summary(calls, keys):
    return [list(k) + [len(rows), sum(_approved(r['classification']) for r in rows),
                       sum(r['classification'] == 'REVISAR' for r in rows), sum(r['severe'] for r in rows)]
            for k, rows in _groups(calls, keys)]


def _common(calls, keys):
    data = defaultdict(lambda: {'calls': 0, 'grave': 0, 'category': '', 'reason': ''})
    for r in calls:
        for e in r['errors']:
            key = tuple(r[k] for k in keys) + (e['code'],)
            entry = data[key]; entry['calls'] += 1; entry['grave'] += int(e['grave'])
            entry['category'] = e['category']; entry['reason'] = e['reason']
    return [list(k) + [v['category'], v['calls'], v['grave'], v['reason']]
            for k, v in sorted(data.items(), key=lambda kv: (-kv[1]['calls'], kv[0]))]


def _recommendations(calls, keys):
    rows = []
    for row in _common(calls, keys):
        prefix, code, category, count, graves, reason = row[:len(keys)], *row[len(keys):]
        immediate = graves > 0 or code == 'PEN_QUEJA_MALTRATO'
        frequency = sum(1 for r in calls if all(r[k] == v for k, v in zip(keys, prefix)))
        cadence = 'INMEDIATA' if immediate else 'SEMANAL' if frequency and count / frequency >= .2 else 'MENSUAL'
        advice = ADVICE.get(code)
        if advice is None and ('NEG' in code or 'MONTO' in code or 'FECHA' in code):
            advice = 'Practicar negociación según mora, importes del Excel, aceptación y fechas autorizadas; validar parcialidades sin aplicar un plazo único a todas las moras.'
        rows.append(prefix + [code, count, cadence, advice or
            'Contrastar el criterio reportado con el audio, documentar la causa y realizar retroalimentación sobre casos confirmados.'])
    return rows


class ConsolidatedReportService:
    @staticmethod
    def load(paths, *, deduplicate=False):
        paths = list(paths)
        if not paths: raise ValueError('Seleccione al menos un checkpoint de lote.')
        sources, calls, duplicates, warnings, chosen = [], [], [], [], {}
        for index, path in enumerate(paths, 1):
            path = Path(path)
            if path.stat().st_size > MAX_INPUT: raise ValueError(f'{path.name}: archivo demasiado grande.')
            raw = path.read_bytes()
            if path.suffix.lower() == '.zip':
                with zipfile.ZipFile(path) as archive:
                    entries = [i for i in archive.infolist() if not i.is_dir() and i.filename.lower().endswith('.json')]
                    if len(entries) != 1 or entries[0].file_size > MAX_INPUT:
                        raise ValueError('El ZIP debe contener un solo checkpoint JSON de hasta 128 MB.')
                    raw = archive.read(entries[0])
            elif path.suffix.lower() != '.json': raise ValueError('Cargue checkpoints JSON o un ZIP que contenga un checkpoint.')
            payload = _json(raw)
            if not isinstance(payload, dict) or not isinstance(payload.get('items'), list):
                raise ValueError(f'{path.name}: no es un checkpoint de lote.')
            if not all(isinstance(i, dict) for i in payload['items']): raise ValueError('El lote contiene registros inválidos.')
            source = {'name': f'Lote {index:02d}: {path.parent.name}/{path.name}', 'file_name': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                      'updated': _updated(payload.get('updated_at')), 'calls': len(payload['items']),
                      'completed': payload.get('completed') is True, 'revision': (payload.get('reanalysis') or {}).get('engine_revision', '')}
            sources.append(source)
            if not source['completed']: warnings.append(f'{path.name}: lote no marcado como completo; incluye estados pendientes/error.')
            for item in payload['items']:
                r = _record(item, source)
                if not r['date']: warnings.append(f"{r['file']}: fecha de llamada no disponible; no se usa la fecha de procesamiento.")
                if not r['card']: warnings.append(f"{r['file']}: tarjeta del Excel no disponible; no se completa desde el audio.")
                elif not re.fullmatch(r'\d{16}', r['card']): warnings.append(f"{r['file']}: tarjeta de origen incompleta o con formato distinto de 16 dígitos; se conserva sin completarla.")
                if r['severe'] and _approved(r['classification']):
                    warnings.append(f"{r['file']}: aprobación y falla crítica contradictorias en origen; se informa sin redictaminar.")
                identity = r['identity'] if deduplicate else None
                if identity is None:
                    calls.append(r)
                    if deduplicate: warnings.append(f"{r['file']}: identidad insuficiente para deduplicar con seguridad; se conserva el registro.")
                    continue
                if identity not in chosen:
                    chosen[identity] = len(calls); calls.append(r); continue
                old = calls[chosen[identity]]
                # La hora del archivo/USB no equivale a la fecha de evaluación.
                newer = r['updated'] is not None and (old['updated'] is None or r['updated'] > old['updated'])
                equal = r['updated'] == old['updated']
                if equal and r['source_hash'] != old['source_hash']:
                    warnings.append(f"{r['file']}: empate/sin fecha de evaluación; se conserva el último lote seleccionado, revisar origen.")
                keep, discard = (r, old) if newer or equal else (old, r)
                calls[chosen[identity]] = keep
                duplicates.append({'audio': r['file'], 'kept': keep['source'], 'discarded': discard['source'],
                                   'kept_class': keep['classification'], 'discarded_class': discard['classification'],
                                   'discarded_grave': discard['severe']})
        return {'calls': calls, 'sources': sources, 'duplicates': duplicates,
                'warnings': list(dict.fromkeys(warnings)), 'deduplicate': deduplicate}

    @staticmethod
    def select(dataset, *, gestor='', supervisor='', date_from='', date_to='', family='CALIDAD'):
        if family not in {'CALIDAD', 'MOTIVOS', 'GRAVES'}: raise ValueError('Tipo de reporte inválido.')
        start, end = _date(date_from), _date(date_to)
        if date_from and start is None or date_to and end is None: raise ValueError('Fecha inválida; use dd/mm/aaaa.')
        if start and end and start > end: raise ValueError('El inicio no puede ser posterior al fin.')
        return [r for r in dataset['calls'] if (not gestor or r['gestor'] == gestor)
                and (not supervisor or r['supervisor'] == supervisor)
                and (not start or r['date'] and r['date'] >= start)
                and (not end or r['date'] and r['date'] <= end)
                and (family != 'GRAVES' or r['severe'])]

    @classmethod
    def generate(cls, dataset, output_directory, *, level='GENERAL', family='CALIDAD', group_by='GLOBAL',
                 gestor='', supervisor='', date_from='', date_to='', formats=('xlsx',)):
        if level not in {'GENERAL', 'DETALLADO'}: raise ValueError('Seleccione general o detallado.')
        if group_by not in {'GLOBAL', 'GESTOR', 'SUPERVISOR'}: raise ValueError('Agrupación inválida.')
        formats = tuple(dict.fromkeys(formats))
        if not formats or any(f not in {'xlsx', 'docx'} for f in formats): raise ValueError('Formato inválido.')
        if 'docx' in formats and family != 'GRAVES': raise ValueError('Word está disponible para la recopilación de fallas graves.')
        calls = cls.select(dataset, gestor=gestor, supervisor=supervisor, date_from=date_from, date_to=date_to, family=family)
        if family == 'GRAVES':
            calls = [dict(r, errors=[e for e in r['errors'] if e['grave']]) for r in calls]
        keys = {'GLOBAL': (), 'SUPERVISOR': ('supervisor',), 'GESTOR': ('supervisor', 'gestor')}[group_by]
        report = {'calls': calls, 'level': level, 'family': family, 'group_by': group_by, 'keys': keys,
                  'dataset': dataset, 'filters': {'gestor': gestor, 'supervisor': supervisor, 'desde': date_from, 'hasta': date_to}}
        output_directory = Path(output_directory); output_directory.mkdir(parents=True, exist_ok=True)
        target = Path(tempfile.mkdtemp(prefix='Reporte_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_', dir=output_directory))
        files = {}
        try:
            if 'xlsx' in formats:
                files['xlsx'] = target/f'Reporte_{family}_{level}.xlsx'; cls._excel(report, files['xlsx'])
            if 'docx' in formats:
                files['docx'] = target/f'Fallas_Graves_{level}.docx'; cls._word(report, files['docx'])
        except Exception:
            shutil.rmtree(target); raise
        return {'files': {k: str(v) for k, v in files.items()}, 'calls': len(calls),
                'severe_calls': sum(r['severe'] for r in calls), 'directory': str(target)}

    @staticmethod
    def _examples(report):
        rows = list(_error_rows(report['calls'], report['family'] == 'GRAVES'))
        if report['level'] == 'DETALLADO': return rows
        result, counts = [], Counter()
        for r, e, row in rows:
            key = tuple(r[k] for k in report['keys']) + (e['code'],)
            if counts[key] < 3: result.append((r, e, row)); counts[key] += 1
        return result

    @classmethod
    def _excel(cls, report, path):
        wb = Workbook(); wb.remove(wb.active)
        calls, keys, family, dataset = report['calls'], report['keys'], report['family'], report['dataset']
        def sheet(name, headers, rows):
            ws = wb.create_sheet(name)
            for values in [headers, *rows]:
                ws.append([json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for v in values])
                for c in ws[ws.max_row]:
                    if isinstance(c.value, str): c.data_type = 's'; c.number_format = '@'
                    c.alignment = Alignment(vertical='top', wrap_text=True)
            ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
            for c in ws[1]: c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='4B276B')
            for i, h in enumerate(headers, 1): ws.column_dimensions[get_column_letter(i)].width = 65 if any(w in h for w in ['Descripción', 'Evidencia', 'Contexto', 'Recomendación']) else 25
        sheet('RESUMEN', ['Indicador', 'Valor'], [
            ['Tipo', family], ['Detalle', report['level']], ['Agrupación', report['group_by']], ['Filtros', report['filters']],
            ['Lotes cargados', len(dataset['sources'])], ['Registros seleccionados', len(calls)],
            ['Llamadas con falla grave reportada', sum(r['severe'] for r in calls)],
            ['Duplicados excluidos del universo', len(dataset['duplicates'])], ['Deduplicación', 'SI' if dataset['deduplicate'] else 'NO']])
        sheet('POR_GESTOR', ['Supervisor', 'Gestor', 'Llamadas', 'Aprobadas en origen', 'Revisar en origen', 'Con falla grave'], _summary(calls, ('supervisor','gestor')))
        sheet('POR_LOTE_GESTOR', ['Lote','Supervisor','Gestor','Evaluaciones','Aprobadas en origen','Revisar en origen','Con falla grave'], _summary(calls, ('source','supervisor','gestor')))
        sheet('POR_LOTE_SUPERVISOR', ['Lote','Supervisor','Evaluaciones','Aprobadas en origen','Revisar en origen','Con falla grave'], _summary(calls, ('source','supervisor')))
        sheet('POR_SUPERVISOR', ['Supervisor','Llamadas','Aprobadas en origen','Revisar en origen','Con falla grave'], _summary(calls, ('supervisor',)))
        motive_counts = Counter(tuple(r[k] for k in keys) + (r['motive'],) for r in calls)
        sheet('MOTIVOS_NO_PAGO', [*keys, 'Motivo principal', 'Llamadas'], [list(k)+[v] for k,v in sorted(motive_counts.items(), key=lambda kv:(-kv[1],kv[0]))])
        motive_advice = [list(k)+[v, MOTIVE_ADVICE.get(k[-1], 'Conservar la categoría reportada; confirmar el motivo con el titular cuando sea posible sin atribuirle declaraciones de terceros.')]
                         for k,v in sorted(motive_counts.items(), key=lambda kv:(-kv[1],kv[0]))]
        sheet('RECOMENDACIONES_MOTIVOS', [*keys,'Motivo principal','Evaluaciones','Recomendación'], motive_advice)
        if family != 'GRAVES':
            motive_examples, examples_seen = [], Counter()
            for r in calls:
                key = tuple(r[k] for k in keys) + (r['motive'],)
                if report['level'] == 'DETALLADO' or examples_seen[key] < 3:
                    motive_examples.append(_call_row(r)+[r['motive_basis'],r['motive_evidence']])
                    examples_seen[key] += 1
            sheet('EJEMPLOS_MOTIVOS', CALL_HEADERS+['Base motivo','Evidencia motivo'], motive_examples)
        sheet('ERRORES_COMUNES', [*keys,'Código error','Categoría','Llamadas','Con criterio grave','Descripción reportada'], _common(calls, keys))
        sheet('RECOMENDACIONES', [*keys,'Código error','Llamadas','Atención sugerida','Recomendación'], _recommendations(calls, keys))
        examples = cls._examples(report)
        sheet('FALLAS_GRAVES' if family == 'GRAVES' else 'EJEMPLOS', ERROR_HEADERS, [row for r,e,row in examples])
        if report['level'] == 'DETALLADO':
            sheet('DETALLE_LLAMADAS', CALL_HEADERS+['Estado procesamiento','Origen fecha','Base motivo','Evidencia motivo'],
                  [_call_row(r)+[r['processing'],r['date_basis'],r['motive_basis'],r['motive_evidence']] for r in calls])
            sheet('DETALLE_ERRORES', ERROR_HEADERS, [row for r,e,row in _error_rows(calls, family == 'GRAVES')])
            original_keys = list(dict.fromkeys(k for r in calls for k in r['original_excel']))
            sheet('DATOS_EXCEL', ['Archivo audio',*original_keys], [[r['file'], *['' if r['original_excel'].get(k) is None else str(r['original_excel'][k]) for k in original_keys]] for r in calls])
        sheet('ORIGEN_LOTES', ['Archivo lote','SHA256 checkpoint','Registros','Completo','Revisión'],
              [[s['name'],s['sha256'],s['calls'],'SI' if s['completed'] else 'NO',s['revision']] for s in dataset['sources']])
        sheet('DUPLICADOS', ['Audio','Lote conservado','Lote excluido','Clasificación conservada','Clasificación anterior','Grave anterior'],
              [[d['audio'],d['kept'],d['discarded'],d['kept_class'],d['discarded_class'],'SI' if d['discarded_grave'] else 'NO'] for d in dataset['duplicates']])
        notes = ['Consolidación de resultados guardados. No ejecuta Whisper ni cambia dictámenes.',
                 'Las recomendaciones son para revisión/capacitación; confirme evidencia y responsable en audio.',
                 'La falta de evidencia localizada no permite inventar una cita que pruebe una omisión.',
                 'El contexto ASR es solo referencia. No se certifica escucha humana.',
                 'Cada lote cuenta por separado por indicación de la usuaria. Una misma llamada puede aportar una evaluación en varios lotes.',
                 'Un motivo principal por evaluación; pago ya reportado, terceros y falta de evidencia se separan de causas de no pago.',
                 'Sin fecha de llamada no se usa la de procesamiento. Un filtro de fechas excluye registros sin fecha.',
                 'General presenta hasta tres ejemplos por criterio y agrupación; detallado incluye todos.',
                 *dataset['warnings']]
        sheet('NOTAS', ['Notas'], [[n] for n in notes])
        wb.save(path); wb.close()

    @classmethod
    def _word(cls, report, path):
        from docx import Document
        from docx.shared import Pt
        doc = Document(); doc.styles['Normal'].font.size = Pt(10)
        doc.add_heading('Recopilación de fallas graves', 0)
        doc.add_paragraph(f"Nivel: {report['level']} | Agrupación: {report['group_by']} | Llamadas: {len(report['calls'])}")
        doc.add_paragraph('Resultados reportados por los lotes. No se realizó nueva dictaminación ni escucha del audio. Confirme evidencia y responsable antes de atribuir una falta.')
        doc.add_heading('Resumen y recomendaciones', 1)
        for row in _recommendations(report['calls'], report['keys']): doc.add_paragraph(' | '.join(map(str,row)), style='List Bullet')
        examples = cls._examples(report)
        if not examples: doc.add_paragraph('No hay fallas graves reportadas con los filtros seleccionados.')
        for index, (r,e,row) in enumerate(examples,1):
            doc.add_heading(f"{index}. {e['code']} — {r['file']}", 2)
            doc.add_paragraph(f"Fecha: {r['date'].isoformat() if r['date'] else 'No disponible'} | Día: {DAYS[r['date'].weekday()] if r['date'] else 'No disponible'}")
            doc.add_paragraph(f"Tarjeta del Excel: {r['card'] or 'No disponible'} | Gestor: {r['gestor']} | Supervisor: {r['supervisor']}")
            doc.add_paragraph('Error reportado: '+e['reason'])
            doc.add_paragraph('Evidencia localizada: '+(e['evidence'] or 'No disponible; consultar audio original.'))
            if e['window']: doc.add_paragraph('Ventana ASR (s): '+e['window'])
            doc.add_paragraph('Contexto ASR (no prueba del error): '+(r['context'] or 'No disponible'))
            doc.add_paragraph('Lote origen: '+r['source'])
        if report['dataset']['duplicates']: doc.add_paragraph('Existen registros duplicados. El Excel de consolidación conserva la trazabilidad de los resultados anteriores.')
        doc.save(path)
