"""Contrato de segunda escucha; dobles controlados, sin descargar pesos."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.services.whisper_service import WhisperService
from app.services import context_audio_recovery as C


def test_prior_complaint_window_points_to_treatment_not_an_unrelated_payment():
    from app.services.medium_review_plan import plan_for_item
    item={'result':{'texto':'Puede pagar 900 pesos. En la llamada anterior me trataron mal.',
        'duracion_segundos':120,'segmentos':[
            {'inicio':0,'fin':10,'texto':'Puede pagar 900 pesos.'},
            {'inicio':100,'fin':110,'texto':'En la llamada anterior me trataron mal.'}]},
        'classification':{'clasificacion':'REVISAR','decision_findings':[
            {'code':'MISTREATMENT_REPORT','severity':'REVIEW','reasons':['Queja previa']}]},
        'analytics_metadata':{'negotiation_validation':{'commitment_evidence':{'evidence':'Puede pagar 900 pesos.'}},
            'treatment_validation':{'mistreatment_report_evidence':[{'text':'En la llamada anterior me trataron mal.'}]}}}
    assert [(r['start'],r['end'])for r in plan_for_item(item)]==[(97.,113.)]
    assert item['classification']['clasificacion']=='REVISAR'


def test_separate_medium_reviewer_does_not_switch_back_to_source_small(monkeypatch,tmp_path):
    from app.services import offline_model_service as O,local_model_catalog as M
    primary=WhisperService();primary._model=object();primary._loaded_model_config=('small','cpu','int8')
    original=primary._model;loaded=[];seen=[]
    monkeypatch.setattr(O,'local_model_source',lambda name:str(tmp_path))
    monkeypatch.setattr(M,'inspect_model',lambda source,name:seen.append((source,name)))
    def load(self,model_name=None,**kw):
        self._model=object();self._loaded_model_config=(model_name,'cpu','int8');loaded.append(model_name)
    monkeypatch.setattr(WhisperService,'load_model',load)
    def collect(self,path,data,relation,metadata,model,label,**kw):
        assert self is not primary and model is self._model
        assert label=='Faster-Whisper:medium'and kw['focused']
        assert data['modelo']=='small'
        return {'model':label,'groups':[]}
    monkeypatch.setattr(WhisperService,'_collect_context',collect)
    result=primary.recover_medium_context(tmp_path/'sample.wav',{'modelo':'small'},{},{})
    assert result['model']=='Faster-Whisper:medium'
    assert primary._model is original and primary._loaded_model_config==('small','cpu','int8')
    assert loaded==[str(tmp_path)]and seen==[(str(tmp_path),'medium')]


def test_wrong_medium_architecture_never_loads_or_labels_small_as_medium(monkeypatch,tmp_path):
    from app.services import offline_model_service as O,local_model_catalog as M
    monkeypatch.setattr(O,'local_model_source',lambda name:str(tmp_path))
    def wrong(*a):raise ValueError('Pesos no corresponden a medium')
    monkeypatch.setattr(M,'inspect_model',wrong)
    monkeypatch.setattr(WhisperService,'load_model',lambda *a,**k:pytest.fail('No cargar antes de comprobar arquitectura'))
    with pytest.raises(ValueError):WhisperService().recover_medium_context(tmp_path/'x.wav',{}, {},{})


@pytest.mark.parametrize('available,expected',[(True,'medium'),(False,'primary')])
def test_live_review_dispatch_uses_imported_medium_without_changing_primary(monkeypatch,available,expected):
    service=WhisperService();monkeypatch.setattr(WhisperService,'has_local_medium_review',property(lambda self:available))
    monkeypatch.setattr(service,'recover_medium_context',lambda *a:'medium')
    monkeypatch.setattr(service,'recover_context',lambda *a:'primary')
    assert service.recover_review_context('sample.wav',{}, {},{})==expected


def test_focused_medium_does_not_third_read_a_missing_primary_identity_fact(tmp_path):
    audio=tmp_path/'sample.wav';audio.write_bytes(b'controlled test only')
    data={'texto':'Me puede comunicar con Marina Robles.','duracion_segundos':12,
          'segmentos':[{'inicio':0,'fin':12,'texto':'Me puede comunicar con Marina Robles.'}]}
    metadata={'quality_contact_type':'CONTACTO NO DETERMINADO','shared_classification':{
        'clasificacion':'REVISAR','decision_findings':[{'code':'UNIDENTIFIED_CONTACT','severity':'REVIEW','reasons':['Confirmar respuesta nominal']} ]}}
    original=deepcopy(data);calls=[]
    def read(a,b,beam):
        calls.append((a,b,beam));return {'text':'No está la titular, soy su hermana.','segments':[]}
    record=C.collect(audio,data,{},metadata,read,'Faster-Whisper:medium',focused=True)
    assert data==original and len(calls)==2
    assert all(0<=a<b<=12 and b-a<=45 for a,b,_ in calls)
    assert record['groups'][0]['primary_text']==data['texto']
    assert not record['groups'][0]['third_read_required_by_primary_disagreement']
    assert record['independent_sources']==1 and not record['human_verified']
    assert C.validate(record,data,{},audio)['holder']is False


def test_medium_execution_report_does_not_count_error_records_as_completed():
    assert C.execution_status({'model':'Faster-Whisper:medium','groups':[{'attempts':[
        {'error':'RuntimeError','text':''},{'error':'RuntimeError','text':''}]}]})['completed']==0
    assert C.execution_status({'groups':[{'attempts':[{'text':''},{'text':'Algo','error':'x'}]}]})['completed']==1


def test_medium_report_requires_bound_validated_record_and_window_coverage(tmp_path):
    from app.services.medium_review_plan import execution_for_window
    path=tmp_path/'sample.wav';path.write_bytes(b'controlled test data')
    data={'texto':'Me comunica con Marina Robles.','duracion_segundos':10,
          'segmentos':[{'inicio':0,'fin':10,'texto':'Me comunica con Marina Robles.'}]}
    metadata={'quality_contact_type':'CONTACTO NO DETERMINADO','shared_classification':{
        'clasificacion':'REVISAR','decision_findings':[{'code':'UNIDENTIFIED_CONTACT','severity':'REVIEW','reasons':['Confirmar identidad']} ]}}
    record=C.collect(path,data,{},metadata,lambda *a:{'text':'No está la titular, soy su hermana.','segments':[]},'Faster-Whisper:medium',focused=True)
    item={'result':data,'relation':{},'context_asr_recovery':record,'analytics_metadata':{'context_audio_validation':{'valid':True}}}
    assert execution_for_window(item,'UNIDENTIFIED_CONTACT',0,10)=='MEDIUM_EJECUTADO_REGISTRO_VALIDADO'
    assert execution_for_window(item,'UNIDENTIFIED_CONTACT',0,12)=='NO_EJECUTADO_COMPLETO'
    item['result']=dict(data,texto='Otra llamada.')
    assert execution_for_window(item,'UNIDENTIFIED_CONTACT',0,10)=='REGISTRO_MEDIUM_NO_VINCULADO'
