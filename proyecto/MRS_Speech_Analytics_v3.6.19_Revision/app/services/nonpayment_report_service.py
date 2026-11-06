"""Motivos expresados en la conversación, separados del dictamen de calidad."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import re

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.services.conversation_evidence import normalize, sentence_evidence


# Primero causas específicas, después falta temporal de dinero o negativa.
# Una propuesta/pregunta del gestor no acredita el motivo del cliente.
PATTERNS = [
    ('DESEMPLEO', r'\b(?:(?:estoy|ando|me quede|me encuentro) (?:sin (?:trabajo|empleo)|desemplead[oa])|no tengo (?:trabajo|empleo)|perdi (?:mi |el )?(?:trabajo|empleo)|me corrieron del trabajo)\b'),
    ('SALUD_O_ACCIDENTE', r'\b(?:(?:tuve|tengo|sufri) (?:un |una )?(?:accidente|enfermedad|problema de salud|cancer)|(?:estoy|estuve|me encuentro) (?:enfermo|enferma|hospitalizad[oa])|me operaron)\b'),
    ('FALLECIMIENTO_REFERIDO', r'\b(?:mi (?:espos[oa]|padre|madre|hij[oa]) (?:fallecio|murio)|(?:fallecio|murio) mi (?:espos[oa]|padre|madre|hij[oa]))\b'),
    ('DESCONOCE_O_DISPUTA_ADEUDO', r'\b(?:no reconozco (?:esa |la |esta )?(?:deuda|cuenta|tarjeta|compra)|no debo|no es mi (?:tarjeta|cuenta)|me (?:estan cobrando|cobraron) de mas|no me respetaron (?:el |mi )?(?:pago|acuerdo|convenio))\b'),
    ('IMPEDIMENTO_PARA_PAGAR', r'\b(?:no me (?:recibieron|aceptaron) (?:el |mi )?pago|no pude (?:hacer|realizar|aplicar) (?:el |mi )?pago (?:por|porque)|no he podido (?:ir a pagar|hacer el pago por))\b'),
    ('ESPERA_INGRESO_O_QUINCENA', r'\b(?:me pagan|me van a pagar|cobro (?:hasta |el |la )|recibo (?:mi |la )?(?:quincena|nomina)|estoy esperando (?:mi |el )?(?:pago|sueldo|deposito|quincena))\b'),
    ('INGRESOS_INSUFICIENTES', r'\b(?:no me alcanza|gano (?:muy )?poco|mis ingresos (?:son bajos|no alcanzan)|me redujeron (?:el |mi )?(?:sueldo|salario))\b'),
    ('FALTA_DE_LIQUIDEZ', r'\b(?:no tengo (?:dinero|esa cantidad|la cantidad)|no cuento con (?:dinero|esa cantidad|recursos)|no dispongo de (?:dinero|esa cantidad|recursos)|no traigo dinero|ando sin dinero)\b'),
    ('OLVIDO_DE_PAGO', r'\b(?:se me olvido (?:pagar|el pago)|se me paso (?:pagar|la fecha|el pago)|se me olvido[, ]+pero (?:hoy|ahora) (?:lo )?voy a pagar)\b'),
    ('NEGATIVA_EXPRESA', r'\bno (?:quiero|voy a|pienso) pagar\b'),
]


def detect_nonpayment(item):
    result = item.get('result') or {}
    text = result.get('texto') or ''
    metadata = item.get('analytics_metadata') or {}
    contact = metadata.get('quality_contact_type') or 'NO DETERMINADO'
    def answer(category, evidence=(), origin='SIN_EVIDENCIA_DE_MOTIVO'):
        evidence = list(evidence)
        return {'primary': category, 'secondary': list(dict.fromkeys(e['category'] for e in evidence if e['category'] != category)),
                'evidence': evidence, 'origin': origin, 'contact': contact}
    if not text.strip():
        return answer('SIN_TRANSCRIPCION' if item.get('status') == 'error' else 'SIN_TRANSCRIPCION_DISPONIBLE')
    if contact == 'NO CONOCEN A DEUDOR':
        return answer('NO_CONOCE_AL_DEUDOR')
    # No atribuir la falta de dinero de un familiar al titular ausente.
    units = sentence_evidence(text, result.get('segmentos') or [])
    holder_turn = any(u['speaker_role'] == 'TITULAR' for u in units)
    if contact.startswith('TERCERO') and not holder_turn:
        return answer('CONTACTO_CON_TERCERO_SIN_MOTIVO_DEL_TITULAR')
    found, paid = [], []
    for unit in units:
        if unit['speaker_role'] == 'GESTOR':
            continue
        value = normalize(unit['text'])
        if '?' in value or '¿' in value:
            continue
        for category, pattern in PATTERNS:
            for match in re.finditer(pattern, value):
                prefix = value[max(0, match.start()-45):match.start()]
                if re.search(r'\b(?:no es cierto que|no dije que|dice que|diga que|repita que|no|nunca|jamas)\s*$', prefix):
                    continue
                found.append(dict(unit, category=category, phrase=match.group()))
        match = re.search(r'\b(?:ya (?:pague|lo pague|realice (?:el )?pago)|(?:lo |el pago lo )?realice (?:desde )?ayer|ya hice (?:el |mi )?pago)\b', value)
        if match and not re.search(r'\b(?:no|nunca|diga que|repita que)\s*$', value[:match.start()]):
            paid.append(dict(unit, category='PAGO_YA_REPORTADO', phrase=match.group()))
    if found:
        # Una causa actual explícita prevalece sobre un pago previo parcial.
        category = next(category for category, _ in PATTERNS if any(e['category'] == category for e in found))
        origin = 'ROL_EXPLICITO_EN_TRANSCRIPCION' if all(e['speaker_role'] != 'NO DETERMINADO' for e in found) else 'INDICIO_TEXTUAL_SIN_VOZ_CONFIRMADA'
        return answer(category, found + paid, origin)
    if paid:
        return answer('PAGO_YA_REPORTADO', paid, 'PAGO_REFERIDO_EN_TRANSCRIPCION')
    return answer('SIN_MOTIVO_IDENTIFICADO')


class NonpaymentReportService:
    @staticmethod
    def companion_path(quality_report):
        quality = Path(quality_report)
        stamp = re.search(r'(\d{8}_\d{6})$', quality.stem)
        suffix = '_' + stamp.group() if stamp else ''
        return quality.with_name('Reporte_Motivos_No_Pago' + suffix + '.xlsx')

    @classmethod
    def report_status(cls, quality_report):
        if not quality_report or not Path(quality_report).exists():
            return {'path': None, 'error': 'No hay reporte final.'}
        try:
            book = load_workbook(quality_report, read_only=True, data_only=True)
        except Exception as error:
            return {'path': None, 'error': str(error)}
        try:
            if 'MOTIVOS_NO_PAGO' not in book.sheetnames:
                return {'path': None, 'error': 'Este reporte no incluye motivos de no pago.'}
            ws = book['MOTIVOS_NO_PAGO']
            path = cls.companion_path(quality_report)
            if ws['B2'].value == 'GENERADO' and path.exists():
                return {'path': str(path), 'error': None}
            return {'path': None, 'error': str(ws['B3'].value or 'No se generó el reporte adicional.')}
        finally:
            book.close()

    @staticmethod
    def _append(ws, values):
        values = [json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for v in values]
        ws.append(values)
        for cell in ws[ws.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = 's'
                cell.number_format = '@'

    @classmethod
    def generate_report(cls, items, quality_report):
        path = cls.companion_path(quality_report)
        path.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook(); wb.remove(wb.active)
        detail = wb.create_sheet('DETALLE_LLAMADAS')
        relation_keys = list(dict.fromkeys(k for i in items for k in (i.get('relation') or {}) if k != 'datos_excel_original'))
        headers = ['Archivo original', 'Motivo principal', 'Otros motivos / pago previo', 'Base de evidencia',
                   'Evidencia ASR', 'Ventanas ASR (s)', 'Interlocutor detectado', 'Clasificación calidad', 'Estado de procesamiento']
        cls._append(detail, headers + ['Excel: '+k for k in relation_keys])
        original = wb.create_sheet('DATOS_EXCEL')
        source_keys = list(dict.fromkeys(k for i in items for k in ((i.get('relation') or {}).get('datos_excel_original') or (i.get('relation') or {})) if k != 'datos_excel_original'))
        cls._append(original, ['Archivo original', 'Origen de datos'] + source_keys)
        counts = Counter(); by_advisor = Counter(); by_mora = Counter(); accounts = defaultdict(set)
        for i in items:
            detected = detect_nonpayment(i)
            category = detected['primary']; relation = i.get('relation') or {}
            file = i.get('file_name') or Path(i.get('path') or '').name
            card = re.sub(r'\D', '', str(relation.get('numero_de_tarjeta') or ''))
            counts[category] += 1
            if len(card) == 16: accounts[category].add(card)
            by_advisor[(category, str(relation.get('gestor') or 'SIN_DATO'), str(relation.get('supervisor') or 'SIN_DATO'))] += 1
            by_mora[(category, str(relation.get('asignacion') or relation.get('mora') or 'SIN_DATO'))] += 1
            evidence = '\n'.join(dict.fromkeys(e['text'] for e in detected['evidence']))
            windows = '; '.join(dict.fromkeys(f"{e['start']}–{e['end']}" for e in detected['evidence'] if e['start'] is not None and e['end'] is not None))
            quality = 'ERROR' if i.get('status') == 'error' else (i.get('classification') or {}).get('clasificacion') or 'SIN_DICTAMEN'
            cls._append(detail, [file, category, '; '.join(detected['secondary']), detected['origin'], evidence,
                                windows, detected['contact'], quality,
                                i.get('status') or 'SIN_DATO'] + [relation.get(k) for k in relation_keys])
            raw = relation.get('datos_excel_original') or relation
            cls._append(original, [file, 'COLUMNAS_ORIGINALES_GUARDADAS' if relation.get('datos_excel_original') else 'RELACION_DISPONIBLE_EN_CHECKPOINT'] + [raw.get(k) for k in source_keys])
        summary = wb.create_sheet('RESUMEN_MOTIVOS', 0)
        cls._append(summary, ['Motivo principal', 'Llamadas', '% del lote', 'Tarjetas distintas con 16 dígitos'])
        for key, count in counts.most_common():
            cls._append(summary, [key, count, round(count/len(items)*100, 2), len(accounts[key])])
        cls._append(summary, ['TOTAL LLAMADAS', sum(counts.values()), 100 if items else 0, None])
        advisor = wb.create_sheet('POR_GESTOR')
        cls._append(advisor, ['Motivo principal', 'Gestor', 'Supervisor', 'Llamadas'])
        for key, count in sorted(by_advisor.items()): cls._append(advisor, [*key, count])
        mora = wb.create_sheet('POR_MORA')
        cls._append(mora, ['Motivo principal', 'Mora Excel', 'Llamadas'])
        for key, count in sorted(by_mora.items()): cls._append(mora, [*key, count])
        notes = wb.create_sheet('NOTAS')
        for text in [
            'Motivos expresados en ASR: este reporte no determina aprobación de calidad ni comprueba el pago en banco.',
            'Una fila por llamada, con un único motivo principal. Causas específicas preceden a liquidez/negativa; los secundarios se muestran aparte.',
            'Los totales cuentan llamadas, no cuentas únicas. Tarjetas distintas se calculan dentro de cada motivo y no son sumables entre motivos.',
            'Las preguntas y palabras identificadas del gestor no se toman como motivos del cliente. Sin voz confirmada se marca indicio textual.',
            'PAGO_YA_REPORTADO, contacto con tercero, desconocimiento, sin motivo y sin transcripción se agrupan aparte de causas económicas.',
            'Los datos se vinculan por la relación del mismo archivo, nunca por número de fila ni por parecido entre tarjetas.',
            'DATOS_EXCEL conserva columnas originales guardadas para lotes nuevos. En checkpoints antiguos solo puede mostrar los campos de relación disponibles.',
            'No se completan motivos ausentes. La evidencia es ASR y no equivale a escucha humana. No se ejecuta Whisper al exportar.',
        ]: cls._append(notes, [text])
        for ws in wb:
            ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
            for c in ws[1]:
                c.font=Font(bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='17365D')
            for col in range(1, ws.max_column+1):
                header=str(ws.cell(1,col).value or '')
                ws.column_dimensions[get_column_letter(col)].width=65 if any(k in header for k in ['Archivo','Evidencia','Origen']) else 28
            for row in ws:
                for c in row: c.alignment=Alignment(vertical='top',wrap_text=True)
        temporary=path.with_name(path.stem+'_nuevo.xlsx')
        try:
            wb.save(temporary); temporary.replace(path)
        finally:
            wb.close()
            if temporary.exists(): temporary.unlink()
        return str(path)
