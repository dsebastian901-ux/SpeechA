"""Hallazgos del segundo bloque: evidencia contextual y atribución conservadora."""
from copy import deepcopy
import json
from pathlib import Path
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import assess_recado,assess_privacy,financial_answer_evidence,reported_card_clarification
from app.services.asr_evidence_quality import reading_quality,usable_groups
from app.services.privacy_disclosure_review import disclosure_candidates,make_disclosure_confirmation
from app.services.home_warning_review import warning_candidates,make_warning_confirmation,validate_warning_confirmation
from app.services.checkpoint_privacy_review import confirm_checkpoint_disclosure
from app.services.checkpoint_reanalysis import reanalyze_checkpoint

WARNING='De lo contrario, se estará trabajando sobre la recuperación total en el domicilio establecido por el sistema.'
BASE='Habla MRS. Soy su hermana. ¿Le puedo dejar un recado? Sí. Que se comunique con nosotros al número telefónico 5551234567. '


def fixture(text=BASE,mora='1PV'):
    return ({'archivo':'sample.ogg','texto':text,'segmentos':[],'duracion_segundos':120},
            {'estatus_grabacion':'MENSAJE CON FAMILIAR','numero_de_tarjeta':'1234567890123456','asignacion':mora})


def analyze(data,relation,**reviews):
    t=TranscriptionModel.from_dict(data);t.metadata.update(reviews)
    return A.analyze_transcription(t,relation)


def test_callback_acknowledgement_yo_le_digo_is_reception_in_context_only():
    text='Habla MRS. Es mi esposa. Que se comunique ese número para llegar a un arreglo. Ok, yo le digo.'
    a=analyze(*fixture(text))
    assert a.metadata['final_result']=='APROBADO'
    assert any(e.get('method')=='CONFIRMA_AVISO_TRAS_RECONTACTO' for e in a.metadata['status_validation']['recado_evidence']['evidence']['acceptance'])


@pytest.mark.parametrize('text',['Yo le digo.','Yo le digo que no puedo pagar.',
    'Que se comunique ese número. Gestor: Yo le digo.',
    'Que se comunique ese número. ¿Yo le digo?', 'Que se comunique ese número. Diga que yo le digo.'])
def test_unrelated_quoted_question_or_agent_yo_le_digo_does_not_prove_reception(text):
    assert not any(e.get('method')=='CONFIRMA_AVISO_TRAS_RECONTACTO' for e in assess_recado(text)['acceptance'])


DELAYED=('Habla MRS. No llega. ¿Puedo dejarlo un número de telefónico para que la señorita Ana se pueda comunicar con nosotros? '
         'A ver, espérame, tengo las manos ocupadas. A ver, espérame. A ver, díselo. Es el 5551. Ajá. 2345. Ajá. 67. Ok.')


def test_wait_then_explicit_dictation_request_and_complete_number_is_received():
    data,relation=fixture(DELAYED);relation['estatus_grabacion']='MENSAJE CON TERCERO'
    a=analyze(data,relation)
    assert a.metadata['final_result']=='APROBADO'
    assert any(e.get('method')=='SOLICITA_DICTADO_TRAS_ESPERA_CON_CONTACTO_COMPLETO' for e in assess_recado(DELAYED)['acceptance'])


@pytest.mark.parametrize('text',[
    DELAYED.replace('A ver, díselo.',''),
    DELAYED.replace('A ver, díselo.','Gestor: A ver, díselo.'),
    DELAYED.replace('2345. Ajá. 67.','23.'),
    DELAYED.replace('se pueda comunicar con nosotros','pague 1000 pesos'),
    DELAYED.replace('Puedo dejarlo','No le puedo dejarlo'),
    DELAYED.replace('Puedo dejarlo','Dice que le puedo dejarlo'),
])
def test_waiting_alone_wrong_role_or_incomplete_callback_cannot_become_reception(text):
    assert not any(e.get('method')=='SOLICITA_DICTADO_TRAS_ESPERA_CON_CONTACTO_COMPLETO' for e in assess_recado(text)['acceptance'])


CLARIFICATION=('Habla MRS. Soy yo. Yo perdí la tarjeta y ya levanté el reporte. '
               '¿Le otorgaron folio? Sí. Me dijeron que marcara para conocer la resolución. '
               'Comuníquese al banco para verificar el dictamen.')


def test_reported_card_loss_folio_and_resolution_followup_identify_clarification():
    data,relation=fixture(CLARIFICATION);relation['estatus_grabacion']='ACLARACION'
    a=analyze(data,relation)
    assert a.metadata['final_result']=='APROBADO'
    assert a.metadata['status_validation']['detected_status']=='ACLARACION'
    assert a.metadata['clarification_validation']['confirmed']


@pytest.mark.parametrize('text',[
    CLARIFICATION.replace('Yo perdí la tarjeta','No perdí la tarjeta'),
    CLARIFICATION.replace('¿Le otorgaron folio? Sí.','¿Le otorgaron folio?'),
    CLARIFICATION.replace('¿Le otorgaron folio? Sí.','¿No le otorgaron folio? Sí.'),
    CLARIFICATION.replace('¿Le otorgaron folio? Sí.','¿Le otorgaron folio? Gestor: Sí.'),
    'Yo perdí la tarjeta.',
])
def test_card_loss_alone_missing_or_ambiguous_case_number_does_not_confirm_clarification(text):
    assert not reported_card_clarification(text)['confirmed']


def test_clarification_does_not_waive_a_new_negotiation():
    data,relation=fixture(CLARIFICATION+' Me comprometo a pagar 1000 pesos mañana.');relation['estatus_grabacion']='ACLARACION'
    a=analyze(data,relation)
    assert a.metadata['status_validation']['detected_status']!='ACLARACION'
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('role,confirmed,review',[('GESTOR',True,False),('NO DETERMINADO',False,True),('TERCERO',False,False)])
def test_standalone_amount_after_balance_question_uses_response_speaker(role,confirmed,review):
    text='¿De cuánto es el saldo? 9.549.'
    segments=[{'text':'¿De cuánto es el saldo?','speaker_role':'TERCERO','start':80,'end':82},
              {'text':'9.549.','speaker_role':role,'start':82,'end':84}]
    p=assess_privacy(text,segments,third_party_confirmed=True)
    assert p['confirmed_disclosure'] is confirmed and p['review_required'] is review
    if confirmed:assert any(e.get('method')=='IMPORTE_RESPONDIDO_A_PREGUNTA_DE_SALDO' for e in p['evidence'])


def test_balance_answer_after_handoff_to_holder_is_not_third_party_disclosure():
    text='Tercero: Soy su hermana. Titular: Soy yo. ¿De cuánto es el saldo? Gestor: 9549.'
    p=assess_privacy(text,third_party_confirmed=True,titular=True)
    assert not p['confirmed_disclosure']
    data,relation=fixture(text)
    assert not disclosure_candidates(data,relation)


@pytest.mark.parametrize('question',['¿Cuál es el teléfono?','¿Cuál es el folio?','¿De cuánto fue su pago?',
                                    '¿De cuántos dígitos es la referencia?','¿De cuánto es el tal?'])
def test_unrelated_question_or_asr_variant_without_balance_context_is_not_financial_answer(question):
    assert not financial_answer_evidence(question+' 9549.')


def test_tal_asr_variant_needs_previous_balance_context_and_remains_unknown_without_manual_proof():
    text='Habla MRS. Soy su esposo. Tiene un saldo pendiente. ¿De cuánto es el tal lo que presenta? 9.549.'
    data,relation=fixture(text);original=deepcopy(data)
    before=analyze(data,relation)
    assert before.metadata['privacy_validation']['review_required'] and before.metadata['final_result']=='REVISAR'
    candidates=disclosure_candidates(data,relation)
    assert len(candidates)==1 and candidates[0]['question_text']
    proof=make_disclosure_confirmation(data,relation,candidates[0],actor_confirmed=True,third_party_confirmed=True)
    after=analyze(data,relation,privacy_disclosure_confirmation=proof)
    assert after.metadata['final_result']=='FALLA_GRAVE' and data==original


@pytest.mark.parametrize('mora',['1PV','2PV'])
def test_unattributed_home_recovery_warning_blocks_approval_without_false_critical(mora):
    data,relation=fixture(BASE+WARNING,mora)
    a=analyze(data,relation)
    assert a.metadata['home_recovery_warning']['review_required']
    assert a.metadata['final_result']=='REVISAR'
    assert 'PEN012' not in {p['id'] for p in a.metadata['penalties']}


@pytest.mark.parametrize('mora',['1PV','2PV'])
def test_known_agent_home_recovery_warning_is_critical(mora):
    a=analyze(*fixture(BASE+'Gestor: '+WARNING,mora))
    assert 'PEN012' in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['final_result']=='FALLA_GRAVE'


@pytest.mark.parametrize('wording',[WARNING.replace('se estará','no se estará'), 'Dice que '+WARNING,'Me dijeron que '+WARNING])
def test_negated_or_reported_warning_is_not_current_agent_warning(wording):
    a=analyze(*fixture(BASE+wording))
    assert not a.metadata['home_recovery_warning']['confirmed']
    assert not a.metadata['home_recovery_warning']['review_required']


@pytest.mark.parametrize('mora',['3PV','4PV','C1'])
def test_new_home_recovery_rule_is_scoped_to_early_moras(mora):
    a=analyze(*fixture(BASE+WARNING,mora))
    assert not a.metadata['home_recovery_warning']['applies']


def test_user_warning_confirmation_is_context_bound_and_survives_reanalysis(tmp_path):
    data,relation=fixture(BASE+WARNING)
    proof=make_warning_confirmation(data,relation,warning_candidates(data,relation)[0],actor_confirmed=True,warning_confirmed=True)
    assert validate_warning_confirmation(data,relation,proof)['valid']
    source=tmp_path/'source.json';payload={'items':[{'file_name':data['archivo'],'result':data,'relation':relation}]}
    source.write_text(json.dumps(payload));raw=source.read_bytes()
    out=confirm_checkpoint_disclosure(source,data['archivo'],proof['evidence'],tmp_path/'out',
        home_warning=True,actor_confirmed=True,warning_confirmed=True)
    final=json.loads(Path(out['checkpoint']).read_text())
    assert final['items'][0]['classification']['clasificacion']=='FALLA_GRAVE'
    record=final['items'][0]['home_warning_confirmation']
    assert not record.get('audio_verified') and source.read_bytes()==raw
    again=reanalyze_checkpoint(out['checkpoint'],tmp_path/'again')
    later=json.loads(Path(again['checkpoint']).read_text())
    assert later['items'][0]['home_warning_confirmation']==record
    assert later['items'][0]['classification']['clasificacion']=='FALLA_GRAVE'


@pytest.mark.parametrize('field,value',[('asignacion','C1'),('numero_de_tarjeta','1234567890123999')])
def test_warning_confirmation_cannot_move_to_another_account_or_mora(field,value):
    data,relation=fixture(BASE+WARNING)
    record=make_warning_confirmation(data,relation,warning_candidates(data,relation)[0],actor_confirmed=True,warning_confirmed=True)
    relation[field]=value
    assert not validate_warning_confirmation(data,relation,record)['valid']
    assert not analyze(data,relation,home_warning_confirmation=record).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('actor,warning',[(False,True),(True,False),(1,True),(True,1)])
def test_warning_requires_both_explicit_user_facts(actor,warning):
    data,relation=fixture(BASE+WARNING)
    with pytest.raises(ValueError,match='explícitamente'):
        make_warning_confirmation(data,relation,warning_candidates(data,relation)[0],actor_confirmed=actor,warning_confirmed=warning)


@pytest.mark.parametrize('field,value',[('active',False),('actor','TERCERO'),('scope','ALL_CALLS'),('record_sha256','x')])
def test_altered_warning_record_is_review_not_false_critical(field,value):
    data,relation=fixture(BASE+WARNING)
    record=make_warning_confirmation(data,relation,warning_candidates(data,relation)[0],actor_confirmed=True,warning_confirmed=True)
    record[field]=value
    a=analyze(data,relation,home_warning_confirmation=record)
    assert a.metadata['final_result']=='REVISAR' and 'PEN012' not in {p['id'] for p in a.metadata['penalties']}


@pytest.mark.parametrize('mode',['compressed','misaligned'])
def test_two_word_asr_loop_is_marked_without_discarding_valid_neighbour(mode):
    values=[{'text':'Texto válido.','start':0,'end':1}]
    for n in range(12):
        values.append({'text':'Las noticias.','start':1+n,'end':2+n,
            'compression_ratio':6 if mode=='compressed' else 2.8,
            'words':[{'word':' Las','start':1+n,'end':1+n if mode=='misaligned' else 1.5+n},
                     {'word':' noticias','start':1.5+n,'end':2+n}]})
    q=reading_quality(values)
    assert q['degraded'] and q['bad_segment_indices']==list(range(1,13))
    assert usable_groups(values)==['Texto válido.']


def test_normal_slow_repetition_without_alignment_or_compression_anomaly_is_kept():
    values=[{'text':'¿Me escucha?','start':n*4,'end':n*4+2,'compression_ratio':1.2} for n in range(8)]
    assert not reading_quality(values)['degraded']


@pytest.mark.parametrize('prefix',['No sé si ','No es verdad que ','Supongamos que '])
def test_hypothetical_or_uncertain_loss_does_not_confirm_clarification(prefix):
    text=CLARIFICATION.replace('Yo perdí la tarjeta',prefix+'yo perdí la tarjeta')
    assert not reported_card_clarification(text)['confirmed']


def test_balance_answer_confirmation_survives_checkpoint_roundtrip(tmp_path):
    data,relation=fixture(BASE+'¿De cuánto es el saldo? 9.549.')
    source=tmp_path/'source.json';source.write_text(json.dumps({'items':[{'file_name':'sample.ogg','result':data,'relation':relation}]}))
    candidates=disclosure_candidates(data,relation)
    result=confirm_checkpoint_disclosure(source,'sample.ogg',candidates[0],tmp_path/'out',actor_confirmed=True,third_party_confirmed=True)
    final=json.loads(Path(result['checkpoint']).read_text())
    assert final['items'][0]['classification']['clasificacion']=='FALLA_GRAVE'
    assert final['items'][0]['result']==data


def test_second_reading_import_preserves_previous_receipt_and_call_evidence(tmp_path):
    import hashlib
    from app.services.audio_block_evidence import attach_audio_block,binding
    data,relation=fixture()
    source=tmp_path/'source.json';source.write_text(json.dumps({'items':[{'file_name':'sample.ogg','result':data,'relation':relation}]}))
    receipt={'schema':1,'source_checkpoint_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'model':'small','whisper_executed':True,'completed_calls':1,'errors':0,'human_verified':False,
        'items':[{'file_name':'sample.ogg','status':'completado','original_text':data['texto'],
            'original_segments':[],'original_text_sha256':hashlib.sha256(data['texto'].encode()).hexdigest(),
            'source_binding':binding(data,relation),'audio_duration':120,'audio_sha256':'a'*64,
            'text':data['texto'].strip(),'segments':[{'text':data['texto'].strip(),'start':0,'end':120}],
            'tail_text':'','tail_segments':[]}]}
    reading=tmp_path/'reading.json';reading.write_text(json.dumps(receipt));raw=reading.read_bytes()
    first=attach_audio_block(source,reading,tmp_path/'first')
    a=json.loads(Path(first['checkpoint']).read_text())
    second=attach_audio_block(first['checkpoint'],reading,tmp_path/'second')
    b=json.loads(Path(second['checkpoint']).read_text())
    assert reading.read_bytes()==raw
    assert b['audio_block_import_history'][-1]==a['audio_block_import']
    assert b['items'][0]['result']==a['items'][0]['result']
    assert b['items'][0]['audio_block_evidence']==a['items'][0]['audio_block_evidence']


def test_cli_home_warning_mode_requires_explicit_flags_and_generates_critical_result(tmp_path,monkeypatch):
    import sys
    from tools import confirm_privacy_disclosure as cli
    data,relation=fixture(BASE+WARNING)
    source=tmp_path/'source.json';source.write_text(json.dumps({'items':[{'file_name':'sample.ogg','result':data,'relation':relation}]}))
    args=['confirm','--home-warning','--checkpoint',str(source),'--call','1','--candidate','1',
          '--confirm-gestor','--output-dir',str(tmp_path/'out')]
    monkeypatch.setattr(sys,'argv',args)
    assert cli.main()==1 and not (tmp_path/'out').exists()
    monkeypatch.setattr(sys,'argv',args+['--confirm-warning'])
    assert cli.main()==0
    final=json.loads((tmp_path/'out/resultados/checkpoint_reanalizado.json').read_text())
    assert final['items'][0]['classification']['clasificacion']=='FALLA_GRAVE'
    assert final['items'][0]['home_warning_confirmation']['warning_confirmed']
