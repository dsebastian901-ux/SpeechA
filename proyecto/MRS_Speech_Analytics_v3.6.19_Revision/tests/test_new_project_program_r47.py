"""Programa completo con frontera ASR controlada, sin checkpoint previo.

Se ejecutan relación Excel, reglas, decisión, copias binarias y ambos reportes.
No acredita reconocimiento acústico ni se reutiliza un dictamen del lote real.
"""
from copy import deepcopy
import json
from pathlib import Path
import wave

from openpyxl import Workbook, load_workbook
import pytest

from app.config.release import APP_VERSION
from app.config import app_info, settings
from app.services.analytics_service import AnalyticsService as A
from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service

CARD = '0000111122223333'
BASE = dict(estatus_grabacion='CONVENIO', asignacion='C1', fecha='2026-11-05',
            corte=20, vencimiento='2026-12-31', pago_minimo=6000, saldo_total=15000)
PLAN = ('Habla MRS. Soy yo. Para liquidar su cuenta. '
        'El segundo monto más para el día 16 sería de 4800 pesos. '
        'Entonces, sería el 1200 pesos el día de hoy? Sí, ahorita paso a pagar. '
        'Y sería uno más por 4800. Sí. '
        'Solo que si paga todo mañana serían 5500. Lo voy a intentar. '
        '¿No puedo pagar con otra tarjeta de crédito? No, solo de débito. '
        'Envíe su comprobante por WhatsApp.')
PAID = ('Habla MRS. Soy yo. Ya pagué 6000 pesos ayer. '
        'Envíe su comprobante por WhatsApp.')
RETAG = ('Habla MRS. Soy yo. Puede realizar un pago de 1000 pesos mañana. '
         'Puede pagar en Farmacias del Ahorro y 7-Eleven. '
         'Envíe su comprobante por WhatsApp. No tengo esa cantidad.')

CASES = [
    ('plan_aceptado', PLAN, BASE, 'APROBADO'),
    ('queja_previa', PLAN+' Me habló una señorita y me habló bien grosera.', BASE, 'NO_APROBADO'),
    ('groseria_al_final', PLAN+' Con una chingada.', BASE, 'REVISAR'),
    ('cuatro_digitos_repetidos', PLAN+' Le doy únicamente la terminación 3333, 3333.', BASE, 'APROBADO'),
    ('historial_transferencia', PAID+' Yo hice una transferencia ayer.', BASE, 'APROBADO'),
    ('datos_transferencia_nuevos', PLAN+' Deposite en la cuenta bancaria 123456789012345678.', BASE, 'REVISAR'),
    ('privacidad_confirmada', 'Habla MRS. Familiar: Soy su madre.\nGestor: Tiene una deuda de 1500 pesos.',
     dict(BASE, estatus_grabacion='RECADO REF1'), 'FALLA_GRAVE'),
    ('recado_sin_saldo', 'Habla MRS. Soy su madre. Dígale que se comunique al número de contacto. Le paso el recado.',
     dict(BASE, estatus_grabacion='RECADO REF1'), 'APROBADO'),
    ('referencia_distinta', PLAN+' La referencia de pago de 16 dígitos es 1111222233334444.', BASE, 'REVISAR'),
    ('arco_omitido', 'Habla MRS. No lo conozco, es número equivocado. Le damos de baja el número.',
     dict(BASE, estatus_grabacion='NO CONOCEN A DEUDOR'), 'FALLA_GRAVE'),
    ('cambio_de_estatus', RETAG,
     dict(BASE, asignacion='1PV', vencimiento='2026-11-20', pago_minimo=1000, saldo_total=3000),
     'APROBADO_ETIQUETA_CORREGIDA'),
    ('rechazo_por_puntaje', 'Habla MRS. Soy yo. Puede realizar un pago de 3000 pesos para regularizar su cuenta.',
     dict(BASE, asignacion='1PV', vencimiento='2026-11-20', pago_minimo=2500, saldo_total=5000),
     'NO_APROBADO_MENOR_80'),
    ('liquidacion_prohibida', PLAN, dict(BASE, asignacion='1PV'), 'REVISAR'),
    ('espera_65_segundos', PAID, BASE, 'REVISAR'),
    ('espera_64_segundos', PAID, BASE, 'APROBADO'),
    ('lugares_autorizados', PLAN+' Puede pagar en Farmacias del Ahorro y 7-Eleven.', BASE, 'APROBADO'),
    *[(alias.replace('.', '')+'_ticker', PLAN.replace('Habla MRS','Mi nombre es Ana de Jurídico '+alias+' Consultores en representación del banco').replace('Envíe su comprobante','Esperamos su ticker'),
       BASE, 'APROBADO') for alias in ('M.A.R.S', 'M.R', 'DMRS', 'MIRS')],
]


def run_fresh(tmp_path, monkeypatch, cases):
    # A fresh project cannot import old decisions or review confirmations.
    import app.services.checkpoint_reanalysis as reanalysis
    monkeypatch.setattr(reanalysis, 'reanalyze_checkpoint',
                        lambda *a, **k: pytest.fail('No cargar ni reanalizar checkpoint'))
    audio_dir = tmp_path/'originales';audio_dir.mkdir()
    excel = tmp_path/'cuentas.xlsx'
    wb = Workbook();ws = wb.active;ws.title = 'Relacion_Audios'
    headers = ['archivo_original', 'gestor', 'supervisor', 'nombre_final', 'numero_de_tarjeta', *BASE]
    ws.append(headers)
    sources, raw_outputs = [], {}
    for key, text, context, expected in cases:
        source = audio_dir/(key+'.wav')
        with wave.open(str(source), 'wb') as wav:
            wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            wav.writeframes(b'\0\0' * 160)
        name = CARD+'_'+context['asignacion']+'_352_PP_GESTOR EJEMPLO_MRS_20261105'
        row = dict(context, archivo_original=source.name, gestor='Gestor ejemplo',
                   supervisor='Supervisor ejemplo', nombre_final=name, numero_de_tarjeta=CARD)
        ws.append([row[h] for h in headers]);sources.append(source)
        raw_outputs[source.name] = {'archivo':source.name, 'texto':text,
                                   'duracion_segundos':150, 'segmentos':[]}
        if key in {'espera_65_segundos', 'espera_64_segundos'}:
            gap = 65 if key == 'espera_65_segundos' else 64
            units = [{'inicio':0, 'fin':20, 'texto':text},
                     {'inicio':20, 'fin':25, 'texto':'Un momento, permítame verificar.', 'speaker_role':'GESTOR'},
                     {'inicio':25+gap, 'fin':30+gap, 'texto':'Gracias por esperar, retomamos.', 'speaker_role':'GESTOR'}]
            raw_outputs[source.name]['segmentos'] = units
            raw_outputs[source.name]['texto'] = ' '.join(u['texto'] for u in units)
    wb.save(excel);wb.close();original_excel=excel.read_bytes()
    output = tmp_path/'proyecto/02_Audios/Transcripciones'
    calls = []
    def asr(audio_path, output_directory):
        name=Path(audio_path).name;target=Path(output_directory)/(Path(name).stem+'.json')
        assert not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(raw_outputs[name]),encoding='utf-8')
        calls.append(name)
        return {'ruta_json':str(target)}
    monkeypatch.setattr(whisper_service, 'transcribe_audio', asr)
    batch=BatchService();batch.set_files([str(p) for p in sources]);batch.set_relation_excel(excel)
    assert not output.exists()
    # Batch creates its first recovery checkpoint before starting ASR, by design.
    assert len(batch.process_all(output_directory=output))==len(cases)
    assert calls==[p.name for p in sources]
    assert excel.read_bytes()==original_excel
    for i,case in zip(batch.items,cases):
        assert i['status']=='completado',i['message']
        assert not i['transcription_recovered']
        assert i['result']==raw_outputs[i['file_name']]
        assert i['classification']['clasificacion']==case[-1], (case[0],i['classification'])
        assert i['analytics_metadata']['engine_revision']==APP_VERSION==app_info.APP_VERSION==settings.APP_VERSION
        assert i['analytics_metadata']['final_result']==case[-1]
        assert i['processing_origin']==dict(flow='PROCESAMIENTO_POR_LOTES',engine_revision=APP_VERSION,
                                           transcription_source='WHISPER_NUEVO')
        assert Path(i['classified_audio_path']).read_bytes()==(audio_dir/i['file_name']).read_bytes()
    return batch


@pytest.mark.parametrize('case',CASES,ids=[c[0] for c in CASES])
def test_general_rules_apply_to_new_project_before_any_checkpoint_review(tmp_path,monkeypatch,case):
    # Initial checkpoint is correctly written before ASR; no old checkpoint is read.
    batch=run_fresh(tmp_path,monkeypatch,[case])
    i=batch.items[0]
    expected=case[-1]
    if case[0]=='lugares_autorizados':
        assert len(i['analytics_metadata']['convenio_payment_validation']['authorized_places_detected'])>=2
        assert i['compliance_score']==100
    if case[0] in {'plan_aceptado','cuatro_digitos_repetidos'}:
        assert i['compliance_score']==80
        assert i['analytics_metadata']['negotiation_validation']['accepted_schedule']['confirmed']
    checkpoint=json.loads(Path(batch.checkpoint_path).read_text(encoding='utf-8'))
    assert checkpoint['engine_revision']==APP_VERSION and checkpoint['completed']
    assert checkpoint['items'][0]['classification']['clasificacion']==expected
    workbook=load_workbook(batch.last_report_path,data_only=True)
    try:
        control=list(workbook['CONTROL_PROCESAMIENTO'].values)
        assert control[1]==(APP_VERSION,i['file_name'],'WHISPER_NUEVO','PROCESAMIENTO_POR_LOTES')
        results=list(workbook['RESULTADOS'].values);headers=results[0]
        assert results[1][headers.index('Clasificación física')]==expected
        assert 'CUENTAS_REETIQUETADAS' in workbook and 'RESUMEN_REETIQUETADO' in workbook
        if expected=='APROBADO_ETIQUETA_CORREGIDA':
            assert Path(i['classified_audio_path']).parent.name=='APROBADOS_ETIQUETA_CORREGIDA'
            assert Path(i['classified_audio_path']).stem.split('_')[3]=='TH'
            assert workbook['CUENTAS_REETIQUETADAS'].max_row==2
    finally:workbook.close()
    assert Path(batch.last_nonpayment_report_path).is_file()


@pytest.mark.parametrize('phrase', [
    'Deposite en la cuenta bancaria 123456789012345678.',
    'Puede pagar en la cuenta de destino 123456789012345678.',
    'Realice el pago al número de cuenta 123456789012345678.',
])
def test_destination_account_instruction_requires_validation_without_word_transfer(phrase):
    from app.services.payment_instruction_validation import transfer_instructions
    assert transfer_instructions(phrase)
    metadata=A.calculate_basic_compliance(PAID+' '+phrase,BASE)
    assert metadata['convenio_payment_validation']['transfer_data_review']


@pytest.mark.parametrize('phrase', [
    'No deposite en la cuenta bancaria 123456789012345678.',
    'Titular: Ya deposité en la cuenta bancaria 123456789012345678.',
    'Ya deposité en la cuenta bancaria 123456789012345678.',
    'Me dijeron que deposite en la cuenta bancaria 123456789012345678.',
])
def test_reported_or_negated_account_is_not_a_new_agent_instruction(phrase):
    from app.services.payment_instruction_validation import transfer_instructions
    assert not transfer_instructions(phrase)
