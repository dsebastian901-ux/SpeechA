"""Importación transaccional offline con arquitectura y permisos sintéticos."""
import json
from pathlib import Path
import secrets
import struct
import pytest
from app.services import local_model_catalog as M
from app.services.access_service import AccessStore,activate,ADMIN_NAME
from app.services.batch_runtime_state import compatible_transcription


def binary_model(path,layers=24,hidden=1024,mels=80):
    def string(value):return struct.pack('<H',len(value)+1)+value.encode()+b'\0'
    values=[('encoder/conv1/weight',(hidden,mels,3))]
    for side in ['encoder','decoder']:
        values += [(f'{side}/layer_{i}/weight',(1,))for i in range(layers)]
    raw=struct.pack('<I',6)+string('WhisperSpec')+struct.pack('<II',3,len(values))
    for name,shape in values:
        raw+=string(name)+bytes([len(shape)])+struct.pack('<'+'I'*len(shape),*shape)+struct.pack('<BI',0,4)+b'\0'*4
    path.write_bytes(raw+struct.pack('<I',0))


def folder(tmp_path,layers=24,hidden=1024):
    source=tmp_path/'source';source.mkdir();binary_model(source/'model.bin',layers,hidden)
    (source/'config.json').write_text('{}');(source/'tokenizer.json').write_text('{}')
    return source


@pytest.fixture
def admin(tmp_path,monkeypatch):
    store=AccessStore(tmp_path/'accounts');password=secrets.token_urlsafe(24);store.initialize(password);activate(store)
    monkeypatch.setattr(M,'DATA_DIR',tmp_path/'data')
    import faster_whisper
    loads=[]
    monkeypatch.setattr(faster_whisper,'WhisperModel',lambda *a,**kw:loads.append((a,kw))or object())
    yield store,password,loads
    activate(None)


def test_offline_medium_import_loads_and_publishes_hash_manifest(tmp_path,admin):
    source=folder(tmp_path);result=M.install_local_model(source,'medium')
    assert result['manifest']['architecture']['encoder_layers']==24
    assert result['manifest']['architecture']['hidden_size']==1024
    installed=Path(result['path']);assert M.imported_model_info(installed,verify=True)['model_name']=='medium'
    assert admin[2][0][1]['local_files_only']is True
    assert (source/'model.bin').read_bytes()==(installed/'model.bin').read_bytes()
    assert not any(p.name.startswith('.')for p in installed.parent.iterdir())


def test_small_cannot_be_mislabeled_as_medium(tmp_path,admin):
    with pytest.raises(ValueError,match='no corresponden'):M.install_local_model(folder(tmp_path,12,768),'medium')
    assert not admin[2]


@pytest.mark.parametrize('file',['model.bin','config.json','tokenizer.json'])
def test_missing_or_zero_length_files_do_not_publish_a_model(tmp_path,admin,file):
    source=folder(tmp_path);(source/file).write_bytes(b'')
    with pytest.raises(ValueError):M.install_local_model(source,'medium')
    assert not (M.DATA_DIR/'models/medium').exists()


def test_failed_backend_validation_cleans_stage_without_overwriting_existing_models(tmp_path,admin,monkeypatch):
    import faster_whisper
    source=folder(tmp_path);root=M.DATA_DIR/'models';(root/'small').mkdir(parents=True);(root/'small/keep').write_bytes(b'old')
    monkeypatch.setattr(faster_whisper,'WhisperModel',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('invalid model')))
    with pytest.raises(RuntimeError):M.install_local_model(source,'medium')
    assert sorted(p.name for p in root.iterdir())==['small']
    assert (root/'small/keep').read_bytes()==b'old'


def test_existing_model_is_never_replaced_implicitly(tmp_path,admin):
    source=folder(tmp_path);M.install_local_model(source,'medium')
    before=(M.DATA_DIR/'models/medium/model.bin').read_bytes()
    with pytest.raises(FileExistsError):M.install_local_model(source,'medium')
    assert (M.DATA_DIR/'models/medium/model.bin').read_bytes()==before


def test_operator_cannot_install_model(tmp_path,admin):
    store,password,_=admin;store.create_operator('Operador',password);store.login('Operador',password)
    with pytest.raises(PermissionError):M.install_local_model(folder(tmp_path),'medium')
    assert not (M.DATA_DIR/'models').exists()


def test_expired_authorization_before_publish_keeps_destination_unmodified(tmp_path,admin,monkeypatch):
    import faster_whisper
    store,password,_=admin;source=folder(tmp_path)
    def load(*a,**kw):store.registry._clock=lambda:float('inf');return object()
    monkeypatch.setattr(faster_whisper,'WhisperModel',load)
    with pytest.raises(PermissionError):M.install_local_model(source,'medium')
    assert not list((M.DATA_DIR/'models').iterdir())


def test_imported_model_with_changed_file_is_rejected_without_network_fallback(tmp_path,admin,monkeypatch):
    from app.services import offline_model_service as O
    source=folder(tmp_path);result=M.install_local_model(source,'medium');installed=Path(result['path'])
    (installed/'model.bin').write_bytes(b'changed')
    import faster_whisper.utils
    monkeypatch.setattr(faster_whisper.utils,'download_model',lambda *a,**kw:pytest.fail('No descargar después de manipulación'))
    with pytest.raises(ValueError,match='cambió'):O.local_model_source(installed)


@pytest.mark.parametrize('bad',['model.onnx','model.pt'])
def test_alternate_formats_are_not_silently_renamed(tmp_path,admin,bad):
    source=tmp_path/'source';source.mkdir();(source/bad).write_bytes(b'not CT2')
    with pytest.raises(ValueError,match='CTranslate2'):M.install_local_model(source,'medium')


def test_medium_does_not_reuse_asr_with_an_unknown_model():
    item={'path':'synthetic.wav'};old={'archivo':'synthetic.wav','texto':'Ejemplo.'}
    assert compatible_transcription(old,item,{'model':'small'})
    assert not compatible_transcription(old,item,{'model':'medium'})
    assert not compatible_transcription(dict(old,modelo='small'),item,{'model':'medium'})
    assert compatible_transcription(dict(old,modelo='medium'),item,{'model':'medium'})


def test_model_loaded_before_import_is_reloaded_after_local_identity_changes(tmp_path,monkeypatch):
    import faster_whisper
    from app.services import offline_model_service as O
    from app.services.whisper_service import WhisperService
    monkeypatch.setattr(O,'DATA_DIR',tmp_path/'data');calls=[]
    monkeypatch.setattr(O,'local_model_source',lambda name:str(tmp_path/'model'))
    monkeypatch.setattr(faster_whisper,'WhisperModel',lambda *a,**kw:calls.append(a)or object())
    service=WhisperService();service.load_model('medium','cpu','int8');first=service._model
    target=O.DATA_DIR/'models/medium';target.mkdir(parents=True);(target/'model.bin').write_bytes(b'new import')
    service.load_model('medium','cpu','int8')
    assert len(calls)==2 and service._model is not first


@pytest.mark.parametrize('retry',[False,True])
def test_transcription_and_vad_retry_keep_the_same_model_snapshot(tmp_path,monkeypatch,retry):
    from types import SimpleNamespace
    import wave
    from app.services.whisper_service import WhisperService
    path=tmp_path/'synthetic.wav'
    with wave.open(str(path),'wb')as h:h.setparams((1,2,16000,0,'NONE','not compressed'));h.writeframes(b'\0\0'*1600)
    service=WhisperService();seen=[]
    segment=SimpleNamespace(id=0,start=0,end=.1,text='Texto del modelo original.',words=[],tokens=[],avg_logprob=-.1,compression_ratio=1,no_speech_prob=0,seek=0,temperature=0)
    original=SimpleNamespace(transcribe=lambda *a,**kw:(iter([segment]),SimpleNamespace(duration=.1,language='es',language_probability=1)))
    config={'model':'small','device':'cpu','compute_type':'int8','language':'es','beam_size':5,'vad_filter':retry,'word_timestamps':False}
    monkeypatch.setattr(service,'get_runtime_configuration',lambda:dict(config))
    def load(**kw):service._model=original;service._model_provenance={'model_name':'small'}
    monkeypatch.setattr(service,'load_model',load);run=service._run_transcription
    def raced(**kw):
        seen.append(kw['model']);service._model=object();service._model_provenance={'model_name':'medium'}
        if retry and len(seen)==1:raise RuntimeError('reintento VAD simulado')
        return run(**kw)
    monkeypatch.setattr(service,'_run_transcription',raced)
    result=service.transcribe_audio(path,tmp_path/'out')
    assert len(seen)==(2 if retry else 1)and all(m is original for m in seen)
    assert result['modelo']=='small'and result['modelo_identidad']['model_name']=='small'
    assert result['texto']=='Texto del modelo original.'


def test_context_reread_resolves_the_primary_model_before_collecting_evidence(monkeypatch,tmp_path):
    import numpy as np
    import faster_whisper.audio
    from app.services.whisper_service import WhisperService
    import app.services.context_audio_recovery as recovery
    from types import SimpleNamespace
    service=WhisperService();service._model=object();service._loaded_model_config=('medium','cpu','int8');calls=[]
    original=SimpleNamespace(transcribe=lambda *a,**kw:(iter([SimpleNamespace(text='Resultado small',start=0,end=1)]),None))
    def load(**kwargs):calls.append(kwargs);service._model=original;service._loaded_model_config=('small','cpu','int8')
    monkeypatch.setattr(service,'load_model',load)
    monkeypatch.setattr(faster_whisper.audio,'decode_audio',lambda *a,**kw:np.zeros(16000,dtype=np.float32))
    def collect(audio_path,data,relation,metadata,read_window,*args,**kwargs):
        return read_window(0,1,5)
    monkeypatch.setattr(recovery,'collect',collect)
    result=service.recover_context(tmp_path/'synthetic.wav',{'modelo':'small','dispositivo':'cpu','tipo_calculo':'int8'}, {},{})
    assert calls==[{'model_name':'small','device':'cpu','compute_type':'int8'}]
    assert 'Resultado small'in str(result)
