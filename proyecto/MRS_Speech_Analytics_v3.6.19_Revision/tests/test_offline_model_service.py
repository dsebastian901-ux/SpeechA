from pathlib import Path
import pytest
import faster_whisper
from faster_whisper import utils
from app.services import offline_model_service as O
from app.services.whisper_service import WhisperService, WhisperServiceError


def model_folder(tmp_path):
    p=tmp_path/'modelo';p.mkdir()
    for name in ['config.json','model.bin','tokenizer.json']:(p/name).write_bytes(b'fixture')
    return p


def test_existing_model_requires_no_cache_or_network(tmp_path,monkeypatch):
    path=model_folder(tmp_path)
    monkeypatch.setattr(utils,'download_model',lambda *a,**k:pytest.fail('No consultar un repositorio si ya existe carpeta local'))
    assert O.local_model_source(path)==str(path.resolve())


@pytest.mark.parametrize('missing',['config.json','model.bin','tokenizer.json'])
def test_incomplete_model_does_not_fall_back_to_internet(tmp_path,monkeypatch,missing):
    path=model_folder(tmp_path);(path/missing).unlink()
    monkeypatch.setattr(utils,'download_model',lambda *a,**k:pytest.fail('Sin descargas alternativas'))
    with pytest.raises(FileNotFoundError,match=missing):O.local_model_source(path)


def test_cached_resolution_explicitly_forbids_network(tmp_path,monkeypatch):
    path=model_folder(tmp_path);calls=[]
    def cached(name,**kwargs):calls.append((name,kwargs));return str(path)
    monkeypatch.setattr(O,'DATA_DIR',tmp_path/'data')
    monkeypatch.setattr(utils,'download_model',cached)
    assert O.local_model_source('small')==str(path.resolve())
    assert calls==[('small',{'local_files_only':True})]


def test_loader_uses_local_model_and_reuses_without_reloading(tmp_path,monkeypatch):
    path=model_folder(tmp_path);calls=[];marker=object()
    monkeypatch.setattr(O,'local_model_source',lambda name:str(path))
    def create(source,**kwargs):calls.append((source,kwargs));return marker
    monkeypatch.setattr(faster_whisper,'WhisperModel',create)
    w=WhisperService();w.load_model(model_name='small',device='cpu',compute_type='int8')
    w.load_model(model_name='small',device='cpu',compute_type='int8')
    assert w._model is marker and len(calls)==1
    assert calls[0]==(str(path),{'device':'cpu','compute_type':'int8','local_files_only':True})


def test_missing_cache_returns_usb_instruction_without_network_retry(tmp_path,monkeypatch):
    monkeypatch.setattr(O,'DATA_DIR',tmp_path/'data')
    calls=[]
    def unavailable(name,**kwargs):calls.append(kwargs);raise FileNotFoundError('cache missing')
    monkeypatch.setattr(utils,'download_model',unavailable)
    with pytest.raises(FileNotFoundError,match='USB'):O.local_model_source('small')
    assert calls==[{'local_files_only':True}]


def test_actual_cache_lookup_cannot_contact_internet(tmp_path,monkeypatch):
    import socket
    def forbidden(*a,**k):pytest.fail('No se permite consultar internet')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(O,'DATA_DIR',tmp_path/'data')
    with pytest.raises(FileNotFoundError,match='USB'):
        O.local_model_source('mrs-offline-test/model-not-in-cache')
