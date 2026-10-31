"""Reconstrucción local: origen, correcciones autorizadas y evidencia conservada."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from app.services.checkpoint_rebuild import rebuild_checkpoint, needs_source_checkpoint
from app.services.audio_block_evidence import binding


def files(tmp_path, *, bound=False, receipt_text='Lectura adicional sin hechos humanos.'):
    data={'archivo':'example.ogg','texto':'Habla MRS. Soy yo. Ya pagué 1500 pesos. Envíe el comprobante por WhatsApp.',
          'segmentos':[],'duracion_segundos':100,'modelo':'small'}
    relation={'numero_de_tarjeta':'1234567890123456','nombre_final':'0001234567890123999_1PV_TH',
              'estatus_grabacion':'CONVENIO','pago_minimo':'1000','saldo_total':'3000'}
    item={'file_name':'example.ogg','result':data,'relation':relation,
          'classification':{'clasificacion':'REVISAR','aprobado':False,'puntaje_minimo':80}}
    master=tmp_path/'master.json';master.write_text(json.dumps({'items':[item]}))
    receipt={'schema':1,'source_checkpoint_sha256':hashlib.sha256(master.read_bytes()).hexdigest(),
        'model':'small','whisper_executed':True,'completed_calls':1,'errors':0,'human_verified':False,
        'items':[{'file_name':'example.ogg','status':'completado','original_text':data['texto'],
            'original_segments':[],'original_text_sha256':hashlib.sha256(data['texto'].encode()).hexdigest(),
            'audio_duration':100,'audio_sha256':'a'*64,'text':receipt_text,
            'segments':[{'text':receipt_text,'start':0,'end':10}], 'tail_text':'','tail_segments':[]}]}
    if bound:
        receipt['source_checkpoint_sha256']='b'*64
        receipt['items'][0]['source_binding']=binding(data,relation)
    readings=tmp_path/'readings.json';readings.write_text(json.dumps(receipt))
    return master,readings


def run(master,readings,out,**kwargs):
    return rebuild_checkpoint(master,readings,output_directory=out,use_excel_card=True,
                              expected_calls=1,expected_readings=1,**kwargs)


def test_rebuild_corrects_only_authorized_output_name_and_preserves_source(tmp_path):
    master,readings=files(tmp_path);raw=master.read_bytes();receipt_raw=readings.read_bytes()
    result=run(master,readings,tmp_path/'out')
    item=json.loads(Path(result['checkpoint']).read_text())['items'][0]
    old=json.loads(raw)['items'][0]
    assert master.read_bytes()==raw and readings.read_bytes()==receipt_raw
    assert item['result']==old['result']
    assert item['relation']==dict(old['relation'],nombre_final='0001234567890123456_1PV_TH')
    assert item['output_name_review']['source']=='EXPLICIT_USER_CHOICE_NUMERO_DE_TARJETA'
    assert result['output_names_corrected']==result['linked_readings']==1
    assert item['analytics_metadata']['audio_block_evidence_validation']['valid']
    assert not item['audio_block_evidence']['human_verified']
    assert not item['audio_block_evidence']['speaker_roles_confirmed']
    assert item['classification']['clasificacion']=='APROBADO'
    assert Path(result['report']).is_file()


def test_bound_reader_does_not_require_obsolete_source_file(tmp_path):
    master,readings=files(tmp_path,bound=True)
    assert not needs_source_checkpoint(master,readings)
    assert run(master,readings,tmp_path/'out')['linked_readings']==1


def test_legacy_reader_requires_its_exact_old_origin_when_master_differs(tmp_path):
    master,readings=files(tmp_path)
    origin=tmp_path/'origin.json';origin.write_bytes(master.read_bytes())
    payload=json.loads(master.read_text());payload['new_reanalysis_metadata']={}
    master.write_text(json.dumps(payload))
    assert needs_source_checkpoint(master,readings)
    with pytest.raises(ValueError,match='origen'):
        run(master,readings,tmp_path/'bad')
    assert not (tmp_path/'bad').exists()
    assert run(master,readings,tmp_path/'good',source_checkpoint=origin)['linked_readings']==1


def test_wrong_origin_rejected_without_creating_output(tmp_path):
    master,readings=files(tmp_path)
    payload=json.loads(master.read_text());payload['changed']=True;master.write_text(json.dumps(payload))
    wrong=tmp_path/'wrong.json';wrong.write_text('{}')
    with pytest.raises(ValueError,match='hash'):
        run(master,readings,tmp_path/'out',source_checkpoint=wrong)
    assert not (tmp_path/'out').exists()


def test_existing_names_readings_and_review_metadata_survive_another_local_rebuild(tmp_path):
    master,readings=files(tmp_path);first=run(master,readings,tmp_path/'first')
    previous=Path(first['checkpoint']);payload=json.loads(previous.read_text())
    payload['human_review']={'previous_provenance':'preserve-this-record'}
    payload['items'][0]['financial_review_history']=[{'revoked':True,'reason':'historical event'}]
    previous.write_text(json.dumps(payload));raw=previous.read_bytes()
    second=rebuild_checkpoint(previous,output_directory=tmp_path/'second',expected_calls=1,expected_readings=1)
    after=json.loads(Path(second['checkpoint']).read_text())
    for k in ['output_name_review','audio_block_evidence','financial_review_history']:
        assert after['items'][0][k]==payload['items'][0][k]
    assert after['human_review']==payload['human_review'] and previous.read_bytes()==raw
    assert second['output_names_corrected']==0


@pytest.mark.parametrize('calls,readings_count',[(95,1),(1,10)])
def test_expected_batch_and_reading_counts_prevent_partial_base(tmp_path,calls,readings_count):
    master,readings=files(tmp_path)
    with pytest.raises(ValueError,match='esperaban'):
        rebuild_checkpoint(master,readings,output_directory=tmp_path/'out',use_excel_card=True,
                           expected_calls=calls,expected_readings=readings_count)
    assert not (tmp_path/'out').exists()


def test_no_duplicate_calls_are_silently_replaced(tmp_path):
    master,readings=files(tmp_path);p=json.loads(master.read_text());p['items'].append(deepcopy(p['items'][0]));master.write_text(json.dumps(p))
    with pytest.raises(ValueError,match='duplicados'):
        rebuild_checkpoint(master,readings,output_directory=tmp_path/'out',use_excel_card=True)
    assert not (tmp_path/'out').exists()


def test_wrong_card_format_is_not_guessed_from_output_name(tmp_path):
    master,readings=files(tmp_path);p=json.loads(master.read_text());p['items'][0]['relation']['numero_de_tarjeta']='short';master.write_text(json.dumps(p))
    with pytest.raises(ValueError,match='16'):
        run(master,readings,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_existing_incompatible_name_review_is_not_overwritten(tmp_path):
    master,readings=files(tmp_path);p=json.loads(master.read_text());p['items'][0]['output_name_review']={'previous_name':'different'};master.write_text(json.dumps(p))
    with pytest.raises(ValueError,match='incompatible'):
        run(master,readings,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_output_name_change_requires_the_selected_excel_policy(tmp_path):
    master,readings=files(tmp_path)
    with pytest.raises(ValueError,match='numero_de_tarjeta'):
        rebuild_checkpoint(master,readings,output_directory=tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_cached_approval_does_not_override_offensive_asr_evidence(tmp_path):
    master,readings=files(tmp_path,receipt_text='Qué poca madre.')
    p=json.loads(master.read_text());p['items'][0]['classification'].update(aprobado=True,clasificacion='APROBADO');master.write_text(json.dumps(p))
    # Actualizar solo el origen de prueba: nunca se importa su etiqueta.
    r=json.loads(readings.read_text());r['source_checkpoint_sha256']=hashlib.sha256(master.read_bytes()).hexdigest();readings.write_text(json.dumps(r))
    result=run(master,readings,tmp_path/'out');item=json.loads(Path(result['checkpoint']).read_text())['items'][0]
    assert item['classification']['clasificacion']=='REVISAR'
    assert not item['classification']['aprobado']
    assert not item['audio_block_evidence']['human_verified']


def test_missing_readings_does_not_produce_an_incomplete_recovered_checkpoint(tmp_path):
    master,_=files(tmp_path)
    with pytest.raises(ValueError,match='lecturas'):
        rebuild_checkpoint(master,output_directory=tmp_path/'out',use_excel_card=True)
    assert not (tmp_path/'out').exists()


def test_file_selection_flow_reconstructs_from_three_local_json_files(tmp_path,monkeypatch):
    import sys
    from types import SimpleNamespace
    from tools import rebuild_checkpoint_base as cli
    master,readings=files(tmp_path)
    origin=tmp_path/'original.json';origin.write_bytes(master.read_bytes())
    payload=json.loads(master.read_text());payload['reanalysis_marker']=True;master.write_text(json.dumps(payload))
    choices=iter([str(master),str(readings),str(origin)]);titles=[];destroyed=[]
    class Root:
        def withdraw(self):pass
        def destroy(self):destroyed.append(True)
    def choose(**kwargs):
        titles.append(kwargs['title']);return next(choices)
    monkeypatch.setitem(sys.modules,'tkinter',SimpleNamespace(Tk=Root,filedialog=SimpleNamespace(askopenfilename=choose),
        messagebox=SimpleNamespace(showerror=lambda *args:pytest.fail('No se esperaba un error de seleccion.'))))
    monkeypatch.setattr(sys,'argv',['rebuild','--use-excel-card','--expected-calls','1',
        '--expected-readings','1','--output-dir',str(tmp_path/'out')])
    assert cli.main()==0 and len(titles)==3 and destroyed==[True]
    assert (tmp_path/'out/resultados/Checkpoint_r25_Recuperado.json').is_file()


def test_cancel_file_selection_creates_no_output(tmp_path,monkeypatch):
    import sys
    from types import SimpleNamespace
    from tools import rebuild_checkpoint_base as cli
    class Root:
        def withdraw(self):pass
        def destroy(self):pass
    monkeypatch.setitem(sys.modules,'tkinter',SimpleNamespace(Tk=Root,
        filedialog=SimpleNamespace(askopenfilename=lambda **kwargs:''),
        messagebox=SimpleNamespace(showerror=lambda *args:pytest.fail('Cancelar no debe mostrar error.'))))
    monkeypatch.setattr(sys,'argv',['rebuild','--output-dir',str(tmp_path/'out')])
    assert cli.main()==0 and not (tmp_path/'out').exists()


def test_second_file_dialog_explains_checkpoint_mistake_and_allows_retry(tmp_path):
    from types import SimpleNamespace
    from tools.rebuild_checkpoint_base import select_valid_file
    master,readings=files(tmp_path);original=master.read_bytes();choices=iter([str(master),str(readings)])
    errors=[];filters=[]
    def choose(**kwargs):
        filters.append(kwargs['filetypes']);return next(choices)
    selected=select_valid_file(SimpleNamespace(askopenfilename=choose),
        SimpleNamespace(showerror=lambda *args:errors.append(args[1])), 'Segundo paso','readings')
    assert selected==readings and master.read_bytes()==original
    assert len(errors)==1 and 'checkpoint' in errors[0] and 'Comparacion_Bloque_Audios.xlsx' in errors[0]
    assert 'No renombre' in errors[0] and filters[0][0][1]=='revision_audios_bloque*.json'


def test_first_file_dialog_rejects_readings_as_master_and_allows_retry(tmp_path):
    from types import SimpleNamespace
    from tools.rebuild_checkpoint_base import select_valid_file
    master,readings=files(tmp_path);choices=iter([str(readings),str(master)]);errors=[]
    selected=select_valid_file(SimpleNamespace(askopenfilename=lambda **kw:next(choices)),
        SimpleNamespace(showerror=lambda *args:errors.append(args[1])), 'Primer paso','checkpoint',expected_calls=1)
    assert selected==master and len(errors)==1 and 'COMPLETO' in errors[0]


def test_origin_dialog_rejects_wrong_hash_before_reconstruction(tmp_path):
    from types import SimpleNamespace
    from tools.rebuild_checkpoint_base import select_valid_file
    master,readings=files(tmp_path);original=tmp_path/'original.json';original.write_bytes(master.read_bytes())
    payload=json.loads(master.read_text());payload['metadata_changed']=True;master.write_text(json.dumps(payload))
    choices=iter([str(master),str(original)]);errors=[]
    selected=select_valid_file(SimpleNamespace(askopenfilename=lambda **kw:next(choices)),
        SimpleNamespace(showerror=lambda *args:errors.append(args[1])), 'Origen','checkpoint',
        expected_sha256=json.loads(readings.read_text())['source_checkpoint_sha256'])
    assert selected==original and len(errors)==1 and 'ORIGINAL' in errors[0]


def test_cancel_after_bad_readings_selection_leaves_no_output(tmp_path):
    from types import SimpleNamespace
    from tools.rebuild_checkpoint_base import select_valid_file
    master,_=files(tmp_path);choices=iter([str(master),'']);errors=[]
    selected=select_valid_file(SimpleNamespace(askopenfilename=lambda **kw:next(choices)),
        SimpleNamespace(showerror=lambda *args:errors.append(args[1])), 'Lecturas','readings')
    assert selected is None and len(errors)==1 and not (tmp_path/'out').exists()


@pytest.mark.parametrize('payload', ['not JSON', '[]', '{"items":[]}'])
def test_bad_json_has_a_readable_selection_error(tmp_path,payload):
    from tools.rebuild_checkpoint_base import check_selected_file
    p=tmp_path/'invalid.json';p.write_text(payload)
    with pytest.raises(ValueError,match='JSON|lista'):
        check_selected_file(p,'readings')


def test_incomplete_asr_receipt_is_not_reinterpreted_as_completed(tmp_path):
    from tools.rebuild_checkpoint_base import check_selected_file
    _,readings=files(tmp_path);j=json.loads(readings.read_text());j['errors']=1;readings.write_text(json.dumps(j))
    with pytest.raises(ValueError,match='completas'):
        check_selected_file(readings,'readings')


def test_master_count_is_checked_in_file_selection(tmp_path):
    from tools.rebuild_checkpoint_base import check_selected_file
    master,_=files(tmp_path)
    with pytest.raises(ValueError,match='95'):
        check_selected_file(master,'checkpoint',expected_calls=95)


@pytest.mark.parametrize('bom',[False,True])
def test_utf8_accents_survive_rebuild_when_windows_default_is_cp1252(tmp_path,monkeypatch,bom):
    master,readings=files(tmp_path,receipt_text='Ándale, Íñigo. ¿Cómo está José?')
    original=json.loads(master.read_text(encoding='utf-8'))
    original['items'][0]['result']['texto']+=' Ándale, señor.'
    original['items'][0]['relation']['gestor']='Álvaro Núñez'
    master.write_text(json.dumps(original,ensure_ascii=False),encoding='utf-8-sig' if bom else 'utf-8')
    receipt=json.loads(readings.read_text(encoding='utf-8'))
    receipt['source_checkpoint_sha256']=hashlib.sha256(master.read_bytes()).hexdigest()
    receipt['items'][0]['original_text']=original['items'][0]['result']['texto']
    receipt['items'][0]['original_text_sha256']=hashlib.sha256(receipt['items'][0]['original_text'].encode()).hexdigest()
    readings.write_text(json.dumps(receipt,ensure_ascii=False),encoding='utf-8-sig' if bom else 'utf-8')
    raw=master.read_bytes();receipt_raw=readings.read_bytes()
    real_read=Path.read_text
    def windows_read(path,encoding=None,errors=None):
        return real_read(path,encoding=encoding or 'cp1252',errors=errors)
    monkeypatch.setattr(Path,'read_text',windows_read)
    result=run(master,readings,tmp_path/'out')
    saved=json.loads(Path(result['checkpoint']).read_bytes().decode('utf-8-sig'))
    item=saved['items'][0]
    assert item['result']==original['items'][0]['result']
    assert item['relation']['gestor']=='Álvaro Núñez'
    assert item['audio_block_evidence']['text']=='Ándale, Íñigo. ¿Cómo está José?'
    assert item['classification']['clasificacion']=='APROBADO'
    assert master.read_bytes()==raw and readings.read_bytes()==receipt_raw
