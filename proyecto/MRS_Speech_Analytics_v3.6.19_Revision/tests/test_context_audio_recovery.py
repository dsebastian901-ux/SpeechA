"""La relectura es del audio, no una excepción por fila ni una aprobación."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import wave

import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.context_audio_recovery import collect,validate,needs_recovery,record_digest
from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service

PRIMARY=('Habla MRS. ¿Me puede comunicar con Persona Ejemplo? Sí. '
         'El banco le requiere un pago de 1500 pesos. Lo voy a revisar. '
         'Puede pagar en Farmacias del Ahorro y 7-Eleven. '
         'Envíe comprobante por WhatsApp.')
REREAD='¿Me puede comunicar con Persona Ejemplo? Sí, soy yo. Habla MRS sobre su tarjeta.'


def fixture(tmp_path,text=PRIMARY):
    path=tmp_path/'synthetic.wav'
    with wave.open(str(path),'wb')as audio:
        audio.setparams((1,2,16000,0,'NONE','not compressed'));audio.writeframes(b'\0\0'*16000)
    data={'archivo':path.name,'ruta_audio':str(path),'texto':text,'segmentos':[],
          'duracion_segundos':90,'modelo':'small'}
    relation={'numero_de_tarjeta':'1234567890123456','estatus_grabacion':'CONVENIO',
        'nombre_final':'1234567890123456_1PV_352_PP_PERSONA_MRS_20261117',
        'asignacion':'1PV','fecha':'2026-11-17','vencimiento':'2026-11-25',
        'pago_minimo':'1000','saldo_total':'3000'}
    return path,data,relation


def make_record(path,data,relation,texts=(REREAD,REREAD)):
    requests=[]
    def reader(start,end,beam):
        requests.append((start,end,beam));return {'text':texts[len(requests)-1],'segments':[]}
    record=collect(path,data,relation,{'shared_classification':{'clasificacion':'REVISAR'},
        'quality_contact_type':'CONTACTO NO DETERMINADO'},reader,'small-test')
    assert len(requests)==2 and requests[0]!=requests[1]
    return record


def analyze(data,relation,record=None):
    t=TranscriptionModel.from_dict(data)
    t.metadata['context_asr_recovery']=record
    return A.analyze_transcription(t,relation)


def test_two_matching_local_reads_resolve_only_holder_identity(tmp_path):
    path,data,relation=fixture(tmp_path);original=deepcopy(data)
    before=analyze(data,relation)
    assert before.metadata['quality_contact_type']=='CONTACTO NO DETERMINADO'
    record=make_record(path,data,relation)
    after=analyze(data,relation,record)
    assert after.metadata['context_audio_validation']['holder']
    assert after.metadata['quality_contact_type']=='TITULAR'
    assert after.metadata['shared_classification']['aprobado']
    assert data==original
    assert not record['human_verified'] and not record['speaker_roles_confirmed']


@pytest.mark.parametrize('second',[
    '¿Me puede comunicar con Otra Persona? Sí, soy yo. Habla MRS sobre la tarjeta.',
    '¿Me puede comunicar con Persona Ejemplo? Soy su esposa y él no está.',
    'No, '*40,
    '¿Me puede comunicar con Persona Ejemplo? No lo conozco, es número equivocado.',
    '¿Me puede comunicar con Persona Ejemplo? No soy yo, pero dígame.',
])
def test_disagreement_third_party_and_asr_loops_do_not_clear_review(tmp_path,second):
    path,data,relation=fixture(tmp_path)
    record=make_record(path,data,relation,(REREAD,second))
    assert not validate(record,data,relation,path)['holder']
    assert not analyze(data,relation,record).metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('change', ['text','account','audio','digest'])
def test_proof_cannot_be_transferred_to_changed_sources(tmp_path,change):
    path,data,relation=fixture(tmp_path);record=make_record(path,data,relation)
    if change=='text':data['texto']+=' Cambio de texto.'
    elif change=='account':relation['numero_de_tarjeta']='1234567890123999'
    elif change=='audio':path.write_bytes(b'otro audio')
    else:record['groups'][0]['attempts'][0]['text']='Texto alterado.'
    assert not validate(record,data,relation,path)['valid']


@pytest.mark.parametrize('problem',[
    'Soy su esposa.',
    'No lo conozco.',
    '¿Tiene contacto con él para dejar un recado? Sí, dígame.',
])
def test_primary_other_person_evidence_has_priority(tmp_path,problem):
    path,data,relation=fixture(tmp_path,PRIMARY+' '+problem)
    record=make_record(path,data,relation)
    assert not validate(record,data,relation,path)['holder']


def test_unrelated_security_alerts_survive_recovered_identity(tmp_path):
    path,data,relation=fixture(tmp_path,PRIMARY+' Gestor: Qué poca madre.')
    record=make_record(path,data,relation)
    result=analyze(data,relation,record)
    assert result.metadata['quality_contact_type']=='TITULAR'
    assert not result.metadata['shared_classification']['aprobado']


def test_new_offense_in_recovery_is_visible_and_blocks_approval(tmp_path):
    path,data,relation=fixture(tmp_path)
    record=make_record(path,data,relation,(REREAD,REREAD+' Qué poca madre.'))
    result=analyze(data,relation,record)
    assert result.metadata['context_audio_validation']['review_required']
    assert not result.metadata['shared_classification']['aprobado']
    assert any(f['code']=='CONTEXT_AUDIO_RISK'
               for f in result.metadata['shared_classification']['decision_findings'])


def test_two_callback_reads_must_agree_on_all_digits(tmp_path):
    path,data,relation=fixture(tmp_path)
    metadata={'shared_classification':{'clasificacion':'REVISAR'},'quality_contact_type':'TERCERO',
        'message_workflow_validation':{'directed_body':True,'recipient_accepted':True,'callback_available':False}}
    replies=['Que se comunique al número de contacto 5512345678.',
             'Que se comunique al número de contacto 5512345678.']
    def read(a,b,beam):return {'text':replies.pop(0),'segments':[]}
    record=collect(path,data,relation,metadata,read,'small-test')
    assert validate(record,data,relation,path)['callback']=='5512345678'
    record['groups'][0]['attempts'][1]['text']='Que se comunique al número de contacto 5512345699.'
    record['record_sha256']=record_digest(record)
    assert validate(record,data,relation,path)['callback']is None


def test_model_unavailable_never_downloads_or_fabricates_recovery(tmp_path,monkeypatch):
    path,data,relation=fixture(tmp_path)
    from app.services.whisper_service import WhisperService
    service=WhisperService()
    assert service.recover_context(path,data,relation,{})is None


@pytest.mark.parametrize('ending,approved',[
    ('Sí, le paso el recado.',True),
    ('No quiero recibir ningún recado, no le voy a pasar el recado.',False),
    ('Sí, le paso el recado. Gestor: Su saldo es de 3000 pesos.',False),
])
def test_callback_consensus_resolves_only_missing_contact(tmp_path,ending,approved):
    text=('Gestor: Habla MRS. ¿Se encuentra Persona Ejemplo? '
          'Tercero: Soy su hermano, no está. Gestor: ¿Le puedo dejar un recado? '
          'Tercero: Sí, dígame. Gestor: Que se comunique con nosotros. '
          'Le doy el número de contacto 55 12 34. Tercero: '+ending)
    path,data,relation=fixture(tmp_path,text)
    relation.update(estatus_grabacion='MENSAJE CON FAMILIAR',
        nombre_final=relation['nombre_final'].replace('_PP_','_3EROS_'))
    before=analyze(data,relation)
    # La misma prueba se evalúa también ante rechazo o divulgación confirmada.
    metadata={'shared_classification':{'clasificacion':'REVISAR'},'quality_contact_type':'TERCERO',
        'message_delivery_validation':{'review_required':True}}
    record=collect(path,data,relation,metadata,lambda *args:{
        'text':'Que se comunique al número de contacto 5512345678.','segments':[]},'small-test')
    after=analyze(data,relation,record)
    assert after.metadata['shared_classification']['aprobado']is approved
    if approved:
        assert not before.metadata['shared_classification']['aprobado']
        assert after.metadata['message_workflow_validation']['complete']


def test_loaded_model_reads_pcm_windows_without_prompt_or_download(tmp_path,monkeypatch):
    from app.services.whisper_service import WhisperService
    path,data,relation=fixture(tmp_path)
    with wave.open(str(path),'wb')as audio:
        audio.setparams((1,2,16000,0,'NONE','not compressed'))
        audio.writeframes(b'\0\0'*16000*90)
    service=WhisperService();calls=[]
    class LocalModel:
        def transcribe(self,samples,**options):
            calls.append((len(samples),options))
            return iter([SimpleNamespace(text=REREAD,start=0.,end=4.,
                avg_logprob=-.2,no_speech_prob=.01,compression_ratio=1.)]),None
    service._model=LocalModel()
    record=service.recover_context(path,data,relation,analyze(data,relation).metadata)
    assert [n for n,_ in calls]==[16000*28,16000*33]
    assert [opts['beam_size']for _,opts in calls]==[5,10]
    assert all(opts['condition_on_previous_text']is False and opts['vad_filter']is False
               and 'initial_prompt'not in opts for _,opts in calls)
    assert validate(record,data,relation,path)['holder']


def test_read_failure_retains_original_review_and_records_error(tmp_path):
    path,data,relation=fixture(tmp_path)
    def broken(*args):raise RuntimeError('Fallo de lectura local')
    record=collect(path,data,relation,analyze(data,relation).metadata,broken,'small-test')
    assert all(a['error']=='RuntimeError'for a in record['groups'][0]['attempts'])
    assert not analyze(data,relation,record).metadata['shared_classification']['aprobado']


def test_normal_new_audio_batch_executes_recovery_before_closing_review(tmp_path,monkeypatch):
    path,data,relation=fixture(tmp_path);output=tmp_path/'project/01_Audios/transcripciones'
    def primary_asr(audio_path,output_directory):
        target=Path(output_directory)/(Path(audio_path).stem+'.json')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(data))
        return {'ruta_json':str(target)}
    monkeypatch.setattr(whisper_service,'transcribe_audio',primary_asr)
    monkeypatch.setattr(whisper_service,'get_runtime_configuration',lambda:{'model':'small'})
    # Frontera del modelo controlada; el servicio, decisiones, copias y reportes son reales.
    monkeypatch.setattr(whisper_service,'_model',object())
    calls=[]
    def recovery(audio_path,raw,context,metadata):
        assert needs_recovery(metadata)=={'holder'}
        calls.append(audio_path);return make_record(path,raw,context)
    monkeypatch.setattr(whisper_service,'recover_context',recovery)
    batch=BatchService();batch.set_files([path])
    results=batch.process_all(output)
    assert len(calls)==len(results)==1
    item=batch.items[0]
    assert item['status']=='completado',item['message']
    assert item['analytics_metadata']['quality_contact_type']=='TITULAR'
    assert item['classification']['aprobado']
    assert item['result']==data
    assert Path(item['classified_audio_path']).read_bytes()==path.read_bytes()
    assert batch.process_all(output)==[]
    from openpyxl import load_workbook
    book=load_workbook(batch.last_report_path,read_only=True,data_only=True)
    try:
        rows=list(book['RESULTADOS'].values)
        assert rows[1][rows[0].index('Relectura local realizada')]=='SI'
        assert rows[1][rows[0].index('Identidad corroborada en relecturas')]=='SI'
    finally:book.close()
    resumed=BatchService();resumed.resume_from_checkpoint(output)
    resumed.items[0]['evaluation_stamp']={}
    def no_inference(*args,**kwargs):raise AssertionError('Actualizar reglas debe reutilizar ASR y evidencia válidos')
    monkeypatch.setattr(whisper_service,'transcribe_audio',no_inference)
    monkeypatch.setattr(whisper_service,'recover_context',no_inference)
    assert len(resumed.process_all(output))==1
    assert resumed.items[0]['transcription_recovered']
    assert resumed.items[0]['classification']['aprobado']


def test_saved_asr_also_recovers_context_without_retranscribing_full_call(tmp_path,monkeypatch):
    path,data,relation=fixture(tmp_path);output=tmp_path/'project/01_Audios/transcripciones'
    output.mkdir(parents=True);(output/(path.stem+'.json')).write_text(json.dumps(data))
    monkeypatch.setattr(whisper_service,'get_runtime_configuration',lambda:{'model':'small'})
    monkeypatch.setattr(whisper_service,'_model',object())
    def forbidden(*args,**kwargs):raise AssertionError('No retranscribir audio completo ni descargar modelos')
    monkeypatch.setattr(whisper_service,'transcribe_audio',forbidden)
    monkeypatch.setattr(whisper_service,'load_model',forbidden)
    calls=[]
    def recover(audio_path,raw,context,metadata):
        calls.append(audio_path);return make_record(path,raw,context)
    monkeypatch.setattr(whisper_service,'recover_context',recover)
    service=BatchService();service.set_files([path]);assert len(service.process_all(output))==1
    item=service.items[0]
    assert item['transcription_recovered']and item['classification']['aprobado']
    assert item['processing_origin']['transcription_source']=='TRANSCRIPCION_EXISTENTE'
    assert item['context_recovery_status']=='FRAGMENTOS_RELEIDOS_LOCALMENTE'
    assert item['result']==data and len(calls)==1
    item['evaluation_stamp']={}
    assert len(service.process_all(output))==1
    assert len(calls)==1


def test_missing_local_model_is_attempted_once_per_batch_and_keeps_saved_asr(tmp_path,monkeypatch):
    path,data,relation=fixture(tmp_path);output=tmp_path/'project/01_Audios/transcripciones'
    output.mkdir(parents=True)
    other=tmp_path/'other.wav';other.write_bytes(path.read_bytes())
    for audio in [path,other]:
        raw=dict(data,archivo=audio.name,ruta_audio=str(audio))
        (output/(audio.stem+'.json')).write_text(json.dumps(raw))
    monkeypatch.setattr(whisper_service,'_model',None)
    monkeypatch.setattr(whisper_service,'get_runtime_configuration',lambda:{'model':'small'})
    attempts=[]
    def unavailable():attempts.append(True);raise FileNotFoundError('Modelo local no instalado')
    monkeypatch.setattr(whisper_service,'load_model',unavailable)
    def forbidden(*args,**kwargs):raise AssertionError('No descargar ni retranscribir llamada completa')
    monkeypatch.setattr(whisper_service,'transcribe_audio',forbidden)
    service=BatchService();service.set_files([path,other])
    assert len(service.process_all(output))==2
    assert len(attempts)==1
    assert all(i['transcription_recovered']for i in service.items)
    assert all(i['classification']['clasificacion']=='REVISAR'for i in service.items)
