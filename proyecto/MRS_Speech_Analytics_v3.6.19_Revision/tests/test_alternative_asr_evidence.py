"""Lecturas alternativas: calidad técnica, procedencia y conservación del lote."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel
from app.services.audio_block_evidence import binding,record_digest,validate_evidence,attach_audio_block
from app.services.asr_evidence_quality import reading_quality,block_reading_quality,usable_groups
from app.services.conversation_evidence import dictated_privacy_email,assess_privacy


def segment(text,start=0,end=10,**extra):return {'text':text,'start':start,'end':end,**extra}


def test_repeat_with_bad_alignment_is_not_a_customer_refusal():
    seg=segment('no, '*80,3,7,compression_ratio=20,
                words=[{'word':' no','start':7,'end':7} for _ in range(80)])
    q=reading_quality([seg])
    assert q['degraded'] and q['warnings'][0]['reason']=='REPETICION_ASR'
    assert not usable_groups([seg])


@pytest.mark.parametrize('text',['No, no, no.','Sí, sí, sí, claro.','Veintidós, veintidós, cincuenta y cinco.'])
def test_natural_short_repetition_is_not_a_reading_failure(text):
    assert not reading_quality([segment(text,compression_ratio=2)])['degraded']


def test_a_bad_tail_does_not_erase_a_valid_primary_expletive():
    first=[segment('Hasta luego. ¡Uta!',0,3)]
    closing=[segment('no, '*20,2,4,compression_ratio=6)]
    q=block_reading_quality(first,closing)
    assert not q['primary']['degraded'] and q['tail']['degraded']
    assert 'Uta' in usable_groups(first)[0]


def test_split_repetition_is_marked_without_discarding_normal_adjacent_speech():
    values=[segment('¿Qué ocurrió?',0,2,compression_ratio=4)]
    values += [segment('Yo me llamo.',3+i*.1,3+(i+1)*.1,compression_ratio=4) for i in range(8)]
    q=reading_quality(values)
    assert q['bad_segment_indices']==list(range(1,9))
    assert usable_groups(values)==['¿Qué ocurrió?']


def test_bad_gap_does_not_join_words_into_a_new_assertion():
    values=[segment('No',0,1),segment('no, '*20,1,2,compression_ratio=8),segment('tiene una deuda.',2,4)]
    assert usable_groups(values)==['No','tiene una deuda.']


@pytest.mark.parametrize('text,expected',[
    ('El correo es privacidad, número uno, arroba, bradesco.com.mx.',True),
    ('Es privacidad. Número 1. Arroba. B de bueno, R de rosa. Bradesco.com.mx.',True),
    ('Es privacidad, número dos, arroba, bradesco.com.mx.',False),
    ('Es privacidad, número uno, arroba, bradescard.com.mx.',False),
    ('Es privacidad, número uno, arroba, un dominio parecido.',False),
    ('Cliente: Es privacidad, número uno, arroba, bradesco.com.mx.',False),
    ('No es privacidad, número uno, arroba, bradesco.com.mx.',False),
])
def test_dictated_mail_never_guesses_or_changes_domain(text,expected):
    assert dictated_privacy_email(text)['detected'] is expected


def test_monthly_arrears_asr_variant_preserves_privacy_review_not_fake_pen003():
    p=assess_privacy('Soy su amiga. Tiene una mensalidad vencida.',third_party_confirmed=True)
    assert p['review_required'] and not p['confirmed_disclosure']


def make_record(data,relation,text,segments=None):
    values=segments if segments is not None else [segment(text)]
    r={'schema':1,'kind':'AUTOMATED_ASR_ONLY','binding':binding(data,relation),
       'source_checkpoint_sha256':'a'*64,'receipt_sha256':'b'*64,'audio_sha256':'c'*64,
       'model':'small','human_verified':False,'speaker_roles_confirmed':False,
       'text':text,'segments':values,'tail_text':'','tail_segments':[]}
    r['record_sha256']=record_digest(r);return r


def sample():
    data={'archivo':'example.ogg','texto':'Habla MRS. Soy yo. Ya pagué 1500 pesos. Envíe comprobante por WhatsApp.',
          'segmentos':[],'duracion_segundos':100,'modelo':'small'}
    relation={'estatus_grabacion':'CONVENIO','numero_de_tarjeta':'1234567890123456','pago_minimo':'1000','saldo_total':'3000'}
    return data,relation


def test_technical_loop_does_not_invent_a_quality_penalty_or_cancel_original_proof():
    data,relation=sample();r=make_record(data,relation,'no, '*20,[segment('no, '*20,compression_ratio=7)])
    t=TranscriptionModel.from_dict(data);t.metadata['audio_block_evidence']=r
    a=A.analyze_transcription(t,relation)
    q=a.metadata['audio_block_evidence_validation']
    assert q['valid'] and q['quality']['degraded'] and not q['review_required']
    assert a.metadata['final_result']=='APROBADO' and a.compliance_score==100


def test_new_offensive_phrase_is_review_not_an_inferred_agent_critical_failure():
    data,relation=sample();r=make_record(data,relation,'Qué poca madre.')
    t=TranscriptionModel.from_dict(data);t.metadata['audio_block_evidence']=r
    a=A.analyze_transcription(t,relation)
    assert a.metadata['final_result']=='REVISAR'
    assert not a.metadata['critical_failures'] and a.compliance_score==100


def test_new_wrong_card_is_not_ignored_just_because_original_reading_was_safe():
    data,relation=sample();r=make_record(data,relation,'Su tarjeta termina en 9999.')
    t=TranscriptionModel.from_dict(data);t.metadata['audio_block_evidence']=r
    a=A.analyze_transcription(t,relation)
    assert a.metadata['final_result']=='REVISAR'
    assert any(v['type']=='REFERENCIA_ADICIONAL_POR_CONFIRMAR' for v in a.metadata['audio_block_evidence_validation']['risks'])
    assert a.compliance_score==100


def test_mail_success_does_not_waive_financial_disclosure_to_unknown_recipient():
    data,relation=sample();data['texto']='Habla MRS. No la conozco.'
    relation['estatus_grabacion']='NO CONOCEN A DEUDOR'
    r=make_record(data,relation,'Presenta una mensualidad vencida.')
    v=validate_evidence(r,data,relation,'NO CONOCEN A DEUDOR')
    assert v['review_required'] and v['risks'][0]['type']=='PRIVACIDAD_SIN_HABLANTE_CONFIRMADO'


@pytest.mark.parametrize('field,value',[('texto','Texto cambiado'),('segmentos',[{'texto':'nuevo'}]),('duracion_segundos',101)])
def test_changed_source_invalidates_supplement_without_reusing_cached_review(field,value):
    data,relation=sample();r=make_record(data,relation,'Lectura adicional.')
    data[field]=value
    v=validate_evidence(r,data,relation,'TITULAR')
    assert not v['valid'] and v['review_required']


def test_tampered_reading_is_not_trusted_even_when_binding_is_unchanged():
    data,relation=sample();r=make_record(data,relation,'Lectura adicional.')
    r['text']='Otro texto'
    assert not validate_evidence(r,data,relation,'TITULAR')['valid']


def test_import_from_original_checkpoint_preserves_newer_name_review_and_raw_evidence(tmp_path):
    data,relation=sample();relation['nombre_final']='0001234567890123456_1PV_TH'
    old={'items':[{'file_name':'example.ogg','result':data,'relation':dict(relation,nombre_final='0001234567890123000_1PV_TH'),
        'classification':{'clasificacion':'REVISAR','puntaje_minimo':80}}]}
    origin=tmp_path/'origin.json';origin.write_text(json.dumps(old))
    current=deepcopy(old);current['items'][0]['relation']=relation
    review={'source':'EXPLICIT_USER_CHOICE_NUMERO_DE_TARJETA','previous_name':old['items'][0]['relation']['nombre_final'],'corrected_name':relation['nombre_final']}
    current['items'][0]['output_name_review']=review
    master=tmp_path/'master.json';master.write_text(json.dumps(current));raw=master.read_bytes()
    evi={'schema':1,'source_checkpoint_sha256':hashlib.sha256(origin.read_bytes()).hexdigest(),
         'human_verified':False,'model':'small','whisper_executed':True,'completed_calls':1,'errors':0,
         'items':[{'file_name':'example.ogg','status':'completado','original_text':data['texto'],
                   'original_segments':data['segmentos'],'original_text_sha256':hashlib.sha256(data['texto'].encode()).hexdigest(),
                   'audio_duration':100,'audio_sha256':'c'*64,'text':'Lectura alternativa.','segments':[segment('Lectura alternativa.')],
                   'tail_text':'','tail_segments':[],'classification':{'aprobado':True},'human_verified':True}]}
    reads=tmp_path/'reads.json';reads.write_text(json.dumps(evi))
    result=attach_audio_block(master,reads,tmp_path/'out',source_checkpoint=origin)
    saved=json.loads(Path(result['checkpoint']).read_text());item=saved['items'][0]
    assert master.read_bytes()==raw
    assert item['result']==data and item['relation']==relation and item['output_name_review']==review
    assert not item['audio_block_evidence']['human_verified'] and 'classification' not in item['audio_block_evidence']
    assert item['analytics_metadata']['audio_block_evidence_validation']['valid']
    # Confirmed human facts are not created by an alternative ASR pass.
    assert 'amount_audio_review' not in item and 'financial_audio_review' not in item
    # Future rule-only reanalysis keeps this evidence linked.
    from app.services.checkpoint_reanalysis import reanalyze_checkpoint
    second=reanalyze_checkpoint(result['checkpoint'],tmp_path/'again')
    after=json.loads(Path(second['checkpoint']).read_text())['items'][0]
    assert after['audio_block_evidence']==item['audio_block_evidence']
    assert after['analytics_metadata']['audio_block_evidence_validation']['valid']


@pytest.mark.parametrize('domain',['sub.bradesco.com.mx','bradesco.com.mx.otro.org'])
def test_dictation_does_not_accept_authorized_domain_inside_a_different_domain(domain):
    assert not dictated_privacy_email('Es privacidad, número uno, arroba, '+domain+'.')['detected']


@pytest.mark.parametrize('field,value',[('numero_de_tarjeta','9999999999999999'),('pago_minimo','2000'),('estatus_grabacion','NO CONOCEN A DEUDOR')])
def test_changed_account_does_not_reuse_asr_from_another_context(field,value):
    data,relation=sample();r=make_record(data,relation,'Lectura adicional.')
    relation[field]=value
    assert not validate_evidence(r,data,relation,'TITULAR')['valid']


def test_additional_offense_does_not_discard_existing_four_fact_human_exception():
    data,relation=sample();r=make_record(data,relation,'Qué poca madre.')
    t=TranscriptionModel.from_dict(data);t.metadata['audio_block_evidence']=r
    t.metadata['hostile_interlocutor_exception']={k:True for k in ('audio_verified','interlocutor_hostile_or_lascivious','prevented_script','agent_professional')}
    a=A.analyze_transcription(t,relation)
    assert a.metadata['final_result']=='APROBADO_CON_EXCEPCION'


def test_reading_json_is_not_reanalyzed_as_ten_failed_calls(tmp_path):
    from app.services.checkpoint_reanalysis import reanalyze_checkpoint
    source=tmp_path/'reading.json';source.write_text(json.dumps({'schema':1,'source_checkpoint_sha256':'a'*64,
        'items':[{'file_name':'example.ogg','original_text':'Texto anterior.'}]}))
    with pytest.raises(ValueError,match='lectura adicional'):
        reanalyze_checkpoint(source,tmp_path/'output')
    assert not (tmp_path/'output').exists()
