"""Un parentesco confirmado resuelve solo identidad familiar, no las demás reglas."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.audio_block_evidence import attach_audio_block,binding
from app.services.family_contact_review import make_family_confirmation,validate_family_confirmation
from app.services.checkpoint_reanalysis import reanalyze_checkpoint


TEXT=('Habla MRS. No se encuentra. ¿Qué es usted del señor Carlos? Tu hija. '
      'Es importante que el señor Carlos se comunique inmediatamente con nosotros. '
      'Le dejaré un teléfono. ¿Me lo rectifica para ver si está correcto? 55, 51, 23, 45, 67.')


def fixture():
    data={'archivo':'sample.ogg','texto':TEXT,'segmentos':[],'duracion_segundos':120}
    relation={'estatus_grabacion':'MENSAJE CON FAMILIAR','numero_de_tarjeta':'1234567890123456','asignacion':'1PV'}
    return data,relation


def analyze(data,relation,record):
    t=TranscriptionModel.from_dict(data);t.metadata['family_contact_confirmation']=record
    return A.analyze_transcription(t,relation)


def test_explicit_user_fact_is_separate_from_raw_asr_and_does_not_assign_speaker_roles():
    data,relation=fixture();raw=deepcopy(data)
    assert analyze(data,relation,None).metadata['final_result']=='REVISAR'
    record=make_family_confirmation(data,relation,'HIJA',user_confirmed=True)
    a=analyze(data,relation,record)
    assert a.metadata['final_result']=='APROBADO'
    assert a.metadata['family_contact_validation']['valid']
    assert a.metadata['family_contact_validation']['relationship']=='HIJA'
    assert data==raw and not record.get('audio_verified')
    assert not a.metadata['privacy_validation']['confirmed_disclosure']
    assert 'Parentesco confirmado por usuario: HIJA' in a.metadata['status_validation']['evidence']


@pytest.mark.parametrize('confirmed',[False,None,1])
def test_no_fact_is_created_without_explicit_user_confirmation(confirmed):
    data,relation=fixture()
    with pytest.raises(ValueError,match='explícita'):
        make_family_confirmation(data,relation,'HIJA',user_confirmed=confirmed)


@pytest.mark.parametrize('field,value',[('archivo','other.ogg'),('texto',TEXT+' Otro dato.'),
                                     ('duracion_segundos',121),('segmentos',[{'text':TEXT}])])
def test_changed_source_cannot_reuse_the_family_fact(field,value):
    data,relation=fixture();record=make_family_confirmation(data,relation,'HIJA',user_confirmed=True)
    data[field]=value
    status=validate_family_confirmation(data,relation,record)
    assert status['review_required'] and not status['valid']
    assert not analyze(data,relation,record).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('field,value',[('numero_de_tarjeta','1234567890123999'),('asignacion','2PV')])
def test_changed_account_cannot_reuse_the_family_fact(field,value):
    data,relation=fixture();record=make_family_confirmation(data,relation,'HIJA',user_confirmed=True)
    relation[field]=value
    assert not validate_family_confirmation(data,relation,record)['valid']


def test_output_name_change_does_not_change_the_contact_identity():
    data,relation=fixture();record=make_family_confirmation(data,relation,'HIJA',user_confirmed=True)
    relation['nombre_final']='output_corrected'
    assert validate_family_confirmation(data,relation,record)['valid']


@pytest.mark.parametrize('field,value',[('relationship','ESPOSA'),('user_confirmed',False),('active',False),
                                     ('scope','ALL_QUALITY_RULES'),('record_sha256','x')])
def test_tampered_or_revoked_record_blocks_approval(field,value):
    data,relation=fixture();record=make_family_confirmation(data,relation,'HIJA',user_confirmed=True)
    record[field]=value
    assert not validate_family_confirmation(data,relation,record)['valid']
    assert analyze(data,relation,record).metadata['final_result']=='REVISAR'


@pytest.mark.parametrize('problem',[
    'Tiene una deuda de 500 pesos.', 'Gestor: Tiene una deuda de 500 pesos.',
    'Me trataron mal.', 'No le voy a pasar el recado.', 'La tarjeta termina en 9999.',
    'No lo conozco.', 'Gestor: Vamos a realizar una visita a su domicilio.',
])
def test_family_confirmation_does_not_waive_other_evidence(problem):
    data,relation=fixture();data['texto']+=' '+problem
    record=make_family_confirmation(data,relation,'HIJA',user_confirmed=True)
    a=analyze(data,relation,record)
    assert not a.metadata['shared_classification']['aprobado']
    if problem.startswith('Tiene'):
        assert a.metadata['privacy_validation']['review_required']
        assert 'PEN003' not in {p['id'] for p in a.metadata['penalties']}


def test_family_confirmation_alone_does_not_prove_a_message_was_left():
    data,relation=fixture();data['texto']='Habla MRS. ¿Qué es usted del señor Carlos? Tu hija.'
    record=make_family_confirmation(data,relation,'HIJA',user_confirmed=True)
    assert not analyze(data,relation,record).metadata['shared_classification']['aprobado']


def test_stale_manual_record_is_not_ignored_even_if_new_asr_would_otherwise_approve():
    data,relation=fixture();record=make_family_confirmation(data,relation,'HIJA',user_confirmed=True)
    data['texto']=data['texto'].replace('Tu hija.','Soy su hija.')
    assert analyze(data,relation,None).metadata['final_result']=='APROBADO'
    assert analyze(data,relation,record).metadata['final_result']=='REVISAR'


def local_files(tmp_path):
    data,relation=fixture()
    master=tmp_path/'master.json';master.write_text(json.dumps({'items':[{
        'file_name':'sample.ogg','result':data,'relation':relation,'classification':{'puntaje_minimo':80}}]}))
    receipt={'schema':1,'source_checkpoint_sha256':hashlib.sha256(master.read_bytes()).hexdigest(),
        'model':'small','whisper_executed':True,'completed_calls':1,'errors':0,'human_verified':False,
        'items':[{'file_name':'sample.ogg','status':'completado','original_text':data['texto'],
            'original_segments':[],'original_text_sha256':hashlib.sha256(data['texto'].encode()).hexdigest(),
            'source_binding':binding(data,relation),'audio_duration':120,'audio_sha256':'a'*64,
            'text':data['texto'],'segments':[{'text':data['texto'],'start':0,'end':120}],
            'tail_text':'','tail_segments':[]}]}
    evidence=tmp_path/'readings.json';evidence.write_text(json.dumps(receipt))
    return master,evidence


def test_import_and_later_reanalysis_preserve_fact_original_and_automated_reading_scope(tmp_path):
    master,evidence=local_files(tmp_path);raw=master.read_bytes();eraw=evidence.read_bytes()
    result=attach_audio_block(master,evidence,tmp_path/'out',family_confirmations={'sample.ogg':'HIJA'})
    final=json.loads(Path(result['checkpoint']).read_text());item=final['items'][0]
    assert master.read_bytes()==raw and evidence.read_bytes()==eraw
    assert item['result']==json.loads(raw)['items'][0]['result']
    assert item['classification']['clasificacion']=='APROBADO'
    assert item['family_contact_confirmation']['user_confirmed']
    assert not item['audio_block_evidence']['human_verified']
    assert not item['audio_block_evidence']['speaker_roles_confirmed']
    again=reanalyze_checkpoint(result['checkpoint'],tmp_path/'again')
    updated=json.loads(Path(again['checkpoint']).read_text())['items'][0]
    assert updated['family_contact_confirmation']==item['family_contact_confirmation']
    assert updated['classification']['clasificacion']=='APROBADO'


def test_confirmation_for_a_different_call_is_rejected_before_output(tmp_path):
    master,evidence=local_files(tmp_path)
    with pytest.raises(ValueError,match='bloque seleccionado'):
        attach_audio_block(master,evidence,tmp_path/'out',family_confirmations={'other.ogg':'HIJA'})
    assert not (tmp_path/'out').exists()
