"""Regresiones sintéticas sin datos de clientes; fronteras ASR controladas."""
from copy import deepcopy
import json

import pytest

from app.services.context_audio_recovery import collect, validate, needs_third_read
from app.services.quality_decision import evaluate_quality


def reading(text, **extra):
    return {'text': text, 'segments': [], **extra}


def fixture(tmp_path):
    audio = tmp_path / 'test.wav'
    audio.write_bytes(b'audio sintetico de prueba')
    data = {'archivo': audio.name, 'ruta_audio': str(audio), 'texto':
            '¿Me puede comunicar con Persona Ejemplo? Sí.',
            'duracion_segundos': 100, 'segmentos': [], 'modelo': 'small'}
    return audio, data, {'numero_de_tarjeta': '1234567890123456'}


def rule_result(texts, purpose, rule):
    from app.services.context_fact_consensus import consensus
    result = consensus(purpose, [reading(t) for t in texts])
    return next(r for r in result['rules'] if r['rule'] == rule)


def test_equivalent_receipt_reads_do_not_require_third():
    attempts = [reading('Gestor: Envíe el comprobante por WhatsApp, por favor.'),
                reading('Gestor: Por favor, mande el ticket por WhatsApp.')]
    assert not needs_third_read('financial', attempts)
    outcome = rule_result([a['text'] for a in attempts], 'financial', 'RECEIPT_REQUEST')
    assert outcome['state'] == 'CONFIRMADO'
    assert len(outcome['matching_evidence']) == 2


def test_equivalent_receipt_without_voice_is_not_attributed_by_repetition():
    texts = ['Envíe el comprobante por WhatsApp, por favor.',
             'Por favor, mande el ticket por WhatsApp.']
    assert rule_result(texts, 'financial', 'RECEIPT_REQUEST')['state'] == 'SIN_ATRIBUCION'
    assert not needs_third_read('financial', [reading(t) for t in texts])


def test_receipt_withdrawal_is_a_real_contradiction_not_majority_vote():
    texts = ['Gestor: Envíe el comprobante por WhatsApp.',
             'Gestor: No es necesario enviar el comprobante.',
             'Gestor: Envíe el ticket por WhatsApp.']
    assert needs_third_read('financial', [reading(t) for t in texts[:2]])
    assert rule_result(texts, 'financial', 'RECEIPT_REQUEST')['state'] == 'CONTRADICTORIO'


def test_third_read_recovers_missing_fact_without_erasing_contradiction():
    texts = ['Gestor: No se entiende la respuesta en este momento.',
             'Gestor: Envíe el comprobante por WhatsApp.',
             'Gestor: Por favor mande el ticket por WhatsApp.']
    assert needs_third_read('financial', [reading(t) for t in texts[:2]])
    assert rule_result(texts, 'financial', 'RECEIPT_REQUEST')['state'] == 'CONFIRMADO'


def test_third_read_without_fact_remains_insufficient():
    texts = ['En este momento no se entiende la frase.',
             'Seguimos sin entender este fragmento de conversación.',
             'No se puede entender lo que se está diciendo.']
    assert rule_result(texts, 'financial', 'AMOUNT')['state'] == 'EVIDENCIA_INSUFICIENTE'
    assert not needs_third_read('financial',[reading(t)for t in texts[:2]])


@pytest.mark.parametrize('reply', ['Sí, soy yo.', 'Exactamente.', 'Sí, dígame.'])
def test_nominal_identity_equivalents_are_consensus(reply):
    texts = [f'Gestor: Tengo el gusto con Persona Ejemplo. Titular: {reply}',
             'Gestor: Tengo el gusto con Persona Ejemplo. Titular: Sí, soy yo.']
    assert rule_result(texts, 'holder', 'IDENTITY')['state'] == 'CONFIRMADO'
    assert not needs_third_read('holder', [reading(t) for t in texts])


def test_apparent_holder_reply_by_third_party_does_not_confirm():
    texts = ['Gestor: Tengo el gusto con Persona Ejemplo. Tercero: Sí, soy yo. Soy su hermano.',
             'Gestor: Tengo el gusto con Persona Ejemplo. Titular: Sí, soy yo.']
    assert rule_result(texts, 'holder', 'IDENTITY')['state'] == 'CONTRADICTORIO'


def test_degraded_readings_do_not_get_a_third_identical_decode():
    attempts = [reading('Envíe el ticket por favor.', segments=[{'avg_logprob': -2.}]),
                reading('Mande el comprobante de pago.', segments=[{'compression_ratio': 4.}])]
    assert not needs_third_read('financial', attempts)


def test_invalid_required_evidence_blocks_even_a_corrected_label():
    metadata = {'context_audio_validation': {'present': True, 'valid': False,
                    'required_findings': ['NEGOTIATION_INVALID_OR_UNCERTAIN']},
                'status_validation': {'detected_status': 'NO DEFINE FECHA DE PAGO'},
                'negotiation_validation': {'valid': True}}
    outcome = evaluate_quality(metadata, 100, duration_seconds=100)
    assert outcome['clasificacion'] == 'REVISAR'
    assert any(f['code'] == 'CONTEXT_AUDIO_REQUIRED_INVALID' for f in outcome['decision_findings'])


def test_invalid_optional_evidence_does_not_invent_a_rejection():
    metadata = {'context_audio_validation': {'present': True, 'valid': False},
                'contact_validation': {'confirmed': True, 'method': 'RESPUESTA_A_IDENTIFICACION'},
                'quality_contact_type': 'TITULAR'}
    assert evaluate_quality(metadata, 100, duration_seconds=100)['clasificacion'] == 'APROBADO'


def test_invalid_identity_evidence_can_be_replaced_by_independent_primary_identity():
    metadata = {'context_audio_validation': {'present': True, 'valid': False,
                                           'required_findings': ['UNIDENTIFIED_CONTACT']},
                'contact_validation': {'confirmed': True, 'method': 'RESPUESTA_A_IDENTIFICACION'},
                'quality_contact_type': 'TITULAR'}
    assert evaluate_quality(metadata, 100, duration_seconds=100)['aprobado']


def test_financial_coincidence_without_voice_cannot_confirm_payment():
    texts = ['¿Puede realizar el pago por 1500 pesos mañana? Sí, de acuerdo.',
             '¿Puede realizar el pago por 1500 pesos mañana? Sí, está bien.']
    assert rule_result(texts, 'financial', 'AMOUNT')['state'] == 'SIN_ATRIBUCION'


@pytest.mark.parametrize('ending', ['Qué poca madre.', 'Vamos a realizar una visita a su domicilio.'])
def test_tail_offense_or_threat_blocks_favorable_recovery(tmp_path, ending):
    audio, data, relation = fixture(tmp_path)
    metadata = {'quality_contact_type': 'CONTACTO NO DETERMINADO',
                'shared_classification': {'clasificacion': 'REVISAR'}}
    def reader(start, end, beam):
        return reading('¿Me puede comunicar con Persona Ejemplo? Sí, soy yo.' if start == 0
                       else 'Esto es el cierre de la llamada. '+ending)
    record = collect(audio, data, relation, metadata, reader, 'small', include_tail=True)
    outcome = validate(record, data, relation, audio)
    assert any(g['purpose'] == 'safety_tail' for g in record['groups'])
    assert outcome['holder']
    assert outcome['review_required'] and outcome['risks']
    decision = evaluate_quality({'context_audio_validation': outcome}, 100, duration_seconds=100)
    assert not decision['aprobado']


def test_checkpoint_roundtrip_recomputes_facts_instead_of_trusting_saved_consensus(tmp_path):
    audio, data, relation = fixture(tmp_path)
    meta = {'quality_contact_type': 'CONTACTO NO DETERMINADO',
            'shared_classification': {'clasificacion': 'REVISAR'}}
    record = collect(audio, data, relation, meta,
                     lambda *args: reading('¿Me puede comunicar con Persona Ejemplo? Sí, soy yo.'), 'small')
    saved = tmp_path / 'checkpoint.json'
    saved.write_text(json.dumps(record))
    restored = json.loads(saved.read_text())
    assert validate(restored, data, relation, audio)['holder']
    changed = deepcopy(restored)
    changed['groups'][0]['consensus']['reason_code'] = 'FAVORABLE_INVENTADO'
    assert not validate(changed, data, relation, audio)['valid']
    audio.write_bytes(b'audio sustituido')
    assert not validate(restored, data, relation, audio)['valid']


def test_unextracted_accepted_plan_is_not_replaced_by_later_channel_intention():
    from app.models.transcriptions import TranscriptionModel
    from app.services.analytics_service import AnalyticsService
    text = ('Gestor: Tengo el gusto con Persona Ejemplo. Titular: Exactamente. '
            'Gestor: Habla MRS. Usted acepta tres pagos, confirma tres pagos. '
            'El primer pago será mañana por 355.60 pesos. Titular: Sí, está bien. '
            'Gestor: Envíe el ticket por WhatsApp. Puede pagar en Farmacias del Ahorro y 7-Eleven. '
            'Titular: Igual creo que lo voy a realizar por transferencia por la aplicación.')
    data = {'archivo': 'sample.ogg', 'texto': text, 'segmentos': [], 'duracion_segundos': 100}
    relation = {'estatus_grabacion': 'CONVENIO', 'asignacion': '1PV', 'pago_minimo': 1000,
                'saldo_total': 4000, 'fecha': '2026-11-20', 'vencimiento': '2026-11-30'}
    result = AnalyticsService.analyze_transcription(TranscriptionModel.from_dict(data), relation)
    assert result.metadata['negotiation_validation']['unresolved_accepted_plan']['review_required']
    assert not result.metadata['shared_classification']['aprobado']


def test_plan_count_question_or_history_is_not_a_confirmed_calendar():
    from app.services.installment_validation import unresolved_accepted_plan
    for text in ['Gestor: ¿Confirma tres pagos?',
                 'Gestor: El mes pasado acordamos tres pagos.',
                 'Gestor: No confirma tres pagos.']:
        assert not unresolved_accepted_plan(text, {}, [])['review_required']


@pytest.mark.parametrize('rule,purpose,text,state',[
    ('AMOUNT','financial','Gestor: ¿Puede realizar el pago por 1500 pesos mañana? Titular: Sí, de acuerdo.','CONFIRMADO'),
    ('COMMITMENT_WITHOUT_DATE','financial','Titular: Yo voy a pagar lo que debo.','CONFIRMADO'),
    ('DISCLOSURE','safety','Tercero: Soy su esposa. Gestor: Su saldo pendiente es de 3000 pesos.','CONFIRMADO'),
    ('DISCLOSURE','safety','Tercero: Soy su esposa, su saldo pendiente es de 3000 pesos.','DESCARTADO_CON_EVIDENCIA'),
    ('PAYMENT_DATE','financial','Gestor: ¿Puede realizar el pago mañana? Titular: Sí, de acuerdo.','CONFIRMADO'),
    ('RECEIPT_REQUEST','financial','Gestor: No es necesario enviar el comprobante.','DESCARTADO_CON_EVIDENCIA'),
    ('REFERENCE','financial','Gestor: La referencia de pago es 1234567890123456.','CONFIRMADO'),
    ('PAYMENT_PLACES','financial','Gestor: Puede pagar en Farmacias del Ahorro y 7-Eleven.','CONFIRMADO'),
    ('OFFENSE','safety','Gestor: Que poca madre, ya terminó la llamada.','CONFIRMADO'),
    ('INTERLOCUTOR_HOSTILITY','safety','Titular: Que poca madre, ya terminó la llamada.','CONFIRMADO'),
    ('HOME_WARNING','safety','Gestor: Vamos a realizar una visita a su domicilio.','CONFIRMADO'),
    ('CONFRONTATION','safety','Gestor: Usted es un mentiroso, ya terminó la llamada.','CONFIRMADO'),
    ('ARCO','safety','Gestor: Puede ejercer sus derechos ARCO para solicitar la baja del número de la base de datos. Envíe su INE y comprobante de la línea al correo privacidad@bradesco.com.mx.','CONFIRMADO'),
])
def test_specific_fact_validators(rule,purpose,text,state):
    assert rule_result([text,text],purpose,rule)['state']==state


def test_attributed_hostility_does_not_create_human_exception():
    texts=['Titular: Que poca madre, ya terminó la llamada.']*2
    result=rule_result(texts,'safety','INTERLOCUTOR_HOSTILITY')
    decision=evaluate_quality({'treatment_validation':{'hostile_interlocutor_review_required':True},
        'context_audio_validation':{'present':True,'valid':True,'fact_validations':[{'rules':[result]}]}},
        100,duration_seconds=90)
    assert decision['clasificacion']=='REVISAR'


def test_receipt_fact_does_not_clear_independent_privacy_or_reference_blocks():
    texts=['Gestor: Envíe el comprobante de pago por WhatsApp.']*2
    result=rule_result(texts,'financial','RECEIPT_REQUEST')
    decision=evaluate_quality({'privacy_validation':{'confirmed_disclosure':True},
        'context_audio_validation':{'present':True,'valid':True,'fact_validations':[{'rules':[result]}]}},
        100,duration_seconds=90)
    assert decision['clasificacion']=='FALLA_GRAVE'


def test_different_confirmed_amounts_do_not_make_a_semantic_consensus():
    texts=['Gestor: ¿Puede realizar el pago por 1500 pesos mañana? Titular: Sí, de acuerdo.',
           'Gestor: ¿Puede realizar el pago por 2500 pesos mañana? Titular: Sí, de acuerdo.']
    assert rule_result(texts,'financial','AMOUNT')['state']=='CONTRADICTORIO'


def test_consensus_is_recomputed_across_conflicting_groups():
    from app.services.context_evidence_policy import confirmed_fact
    from app.services.context_fact_consensus import VALIDATOR_REVISION
    yes=rule_result(['Gestor: Envíe el comprobante por WhatsApp.']*2,'financial','RECEIPT_REQUEST')
    no=rule_result(['Gestor: No es necesario enviar el comprobante.']*2,'financial','RECEIPT_REQUEST')
    assert confirmed_fact({'valid':True,'validator_revision':VALIDATOR_REVISION,
        'fact_validations':[{'rules':[yes]},{'rules':[no]}]},'RECEIPT_REQUEST')is None


def test_reanalysis_reuses_valid_recovery_and_preserves_sources(tmp_path,monkeypatch):
    from app.services.checkpoint_reanalysis import reanalyze_checkpoint
    from app.services.whisper_service import whisper_service
    audio,data,relation=fixture(tmp_path)
    meta={'quality_contact_type':'CONTACTO NO DETERMINADO',
          'shared_classification':{'clasificacion':'REVISAR'}}
    record=collect(audio,data,relation,meta,lambda *a:reading(
        '¿Me puede comunicar con Persona Ejemplo? Sí, soy yo.'),'small')
    item={'path':str(audio),'file_name':audio.name,'result':data,'relation':relation,
          'context_asr_recovery':record,'status':'completado','classification':{}}
    source=tmp_path/'original.json';source.write_text(json.dumps({'items':[item]}))
    original=source.read_bytes();original_audio=audio.read_bytes()
    def forbidden(*args,**kwargs):raise AssertionError('No repetir ASR válido ni descargar modelos')
    monkeypatch.setattr(whisper_service,'recover_context',forbidden)
    monkeypatch.setattr(whisper_service,'load_model',forbidden)
    result=reanalyze_checkpoint(source,tmp_path/'new-results')
    saved=json.loads(__import__('pathlib').Path(result['checkpoint']).read_text())
    assert result['second_listening']['realizadas']==0
    assert saved['items'][0]['context_asr_recovery']==record
    assert source.read_bytes()==original and audio.read_bytes()==original_audio


def test_stable_comparison_uses_identifiers_and_refuses_duplicates(tmp_path):
    from app.services.checkpoint_comparison import compare_checkpoints,compare_payloads
    first={'items':[{'file_name':'a.ogg','classification':{'clasificacion':'REVISAR'}},
                    {'file_name':'b.ogg','classification':{'clasificacion':'APROBADO'}}]}
    second={'items':list(reversed(deepcopy(first['items'])))}
    a,b=tmp_path/'a.json',tmp_path/'b.json'
    a.write_text(json.dumps(first));b.write_text(json.dumps(second))
    result=compare_checkpoints(a,b,tmp_path/'comparison.json')
    assert result['changed']==0 and result['calls']==2
    with pytest.raises(ValueError):compare_checkpoints(a,b,a)
    second['items'].append(deepcopy(second['items'][0]))
    with pytest.raises(ValueError):compare_payloads(first,second)


def test_complete_reading_evidence_is_in_excel_and_program_source(tmp_path):
    from app.services.context_recovery_report import add_context_recovery_sheet,display_trace
    from openpyxl import Workbook
    audio,data,relation=fixture(tmp_path)
    meta={'quality_contact_type':'CONTACTO NO DETERMINADO',
          'shared_classification':{'clasificacion':'REVISAR'}}
    record=collect(audio,data,relation,meta,lambda *a:reading(
        '¿Me puede comunicar con Persona Ejemplo? Sí, soy yo.'),'small')
    context=validate(record,data,relation,audio)
    item={'file_name':audio.name,'context_asr_recovery':record,
          'analytics_metadata':{'context_audio_validation':context},
          'classification':{'clasificacion':'REVISAR','motivo':'Referencia pendiente'}}
    book=Workbook();sheet=add_context_recovery_sheet(book,[item])
    assert sheet.max_row>=3
    assert record['audio_sha256']in display_trace(item)
    assert 'NO_ACREDITADA'in display_trace(item)or 'CONTEXTUAL'in display_trace(item)


def test_recovered_receipt_is_consumed_by_productive_engine_without_changing_score(tmp_path):
    from app.models.transcriptions import TranscriptionModel
    from app.services.analytics_service import AnalyticsService
    audio,data,relation=fixture(tmp_path)
    data['texto']=('Gestor: Habla MRS. Tengo el gusto con Persona Ejemplo. Titular: Sí, soy yo. '
        'Gestor: ¿Puede realizar el pago por 1500 pesos mañana? Titular: Sí, de acuerdo. '
        'Gestor: Puede pagar en Farmacias del Ahorro y 7-Eleven. '
        'A este WhatsApp nos hace llegar el comprobante.')
    relation.update(estatus_grabacion='CONVENIO',fecha='2026-11-20',vencimiento='2026-11-30',
                    corte='2026-11-25',asignacion='1PV',pago_minimo=1000,saldo_total=4000)
    before=AnalyticsService.analyze_transcription(TranscriptionModel.from_dict(data),relation)
    assert before.metadata['convenio_payment_validation']['receipt_request_review_required']
    metadata={'quality_contact_type':'TITULAR','shared_classification':{'clasificacion':'REVISAR',
              'pending_alerts':[{'code':'RECEIPT_UNCERTAIN'}]}}
    record=collect(audio,data,relation,metadata,lambda *a:reading(
        'Gestor: Por favor, envíe el comprobante por WhatsApp.'),'small')
    transcription=TranscriptionModel.from_dict(data)
    transcription.metadata['context_asr_recovery']=record
    after=AnalyticsService.analyze_transcription(transcription,relation)
    assert not after.metadata['convenio_payment_validation']['receipt_request_review_required']
    assert after.metadata['convenio_payment_validation']['receipt_evidence_source']=='LOCAL_AUDIO_CONTEXT'
    assert after.compliance_score==before.compliance_score
    assert after.metadata['shared_classification']['aprobado']
    assert transcription.text==data['texto']
    assert any('RECEIPT_UNCERTAIN'in r['resolves_codes']for g in
               after.metadata['context_audio_validation']['fact_validations']for r in g['rules'])


def test_unconfirmed_date_does_not_become_negotiation_and_amount_is_not_a_day():
    text='Gestor: ¿Puede realizar el pago por 20 pesos? Titular: Sí, de acuerdo.'
    assert rule_result([text,text],'financial','PAYMENT_DATE')['state']=='EVIDENCIA_INSUFICIENTE'
    conditional='Gestor: ¿Puede realizar el pago mañana? Titular: Tal vez, si consigo trabajo.'
    assert rule_result([conditional,conditional],'financial','PAYMENT_DATE')['state']=='EVIDENCIA_INSUFICIENTE'


def test_recovered_fact_cannot_approve_below_eighty_even_with_legacy_lower_threshold():
    metadata={'quality_contact_type':'TITULAR','contact_validation':{'confirmed':True}}
    outcome=evaluate_quality(metadata,79,minimum_score=70,duration_seconds=100)
    assert not outcome['calidad_aprobada']
    assert outcome['puntaje_minimo']==80


def test_identical_offense_with_different_speaker_roles_is_contradictory():
    texts=['Gestor: Que poca madre, ya terminó la llamada.',
           'Titular: Que poca madre, ya terminó la llamada.']
    result=rule_result(texts,'safety','OFFENSE')
    assert result['state']=='CONTRADICTORIO'
    assert result['reason_code']=='EMISORES_INCOMPATIBLES'


def test_commitment_without_date_without_speaker_does_not_confirm_a_negotiation():
    text='Yo voy a pagar lo que debo.'
    assert rule_result([text,text],'financial','COMMITMENT_WITHOUT_DATE')['state']=='SIN_ATRIBUCION'


def test_safety_reference_requires_full_digits_and_checks_account():
    from app.services.context_fact_consensus import consensus
    text='Gestor: La referencia de pago es 1234567890123456.'
    for account,matches in [('1234567890123456',True),('1234567890123499',False)]:
        result=consensus('safety',[reading(text)]*2,{'numero_de_tarjeta':account})
        reference=next(r for r in result['rules']if r['rule']=='REFERENCE')
        assert reference['state']=='CONFIRMADO'
        assert reference['matches_account']is matches


@pytest.mark.parametrize('text,mora,risk',[
    ('Gestor: Vamos a realizar una visita a su domicilio.','1PV',True),
    ('Gestor: Vamos a realizar una visita a su domicilio.','5PV',False),
    ('Gestor: No vamos a realizar una visita a su domicilio.','1PV',False),
    ('Titular: Vamos a realizar una visita a su domicilio.','1PV',False),
])
def test_recovered_home_warning_obeys_existing_mora_and_attribution_rules(tmp_path,text,mora,risk):
    audio,data,relation=fixture(tmp_path);relation['asignacion']=mora
    meta={'quality_contact_type':'TITULAR','shared_classification':{'clasificacion':'REVISAR',
          'pending_alerts':[{'code':'HOME_WARNING_UNATTRIBUTED'}]}}
    record=collect(audio,data,relation,meta,lambda *a:reading(text),'small')
    result=validate(record,data,relation,audio)
    assert any(r['type']=='ADVERTENCIA_DOMICILIARIA_PENDIENTE'for r in result['risks'])is risk
