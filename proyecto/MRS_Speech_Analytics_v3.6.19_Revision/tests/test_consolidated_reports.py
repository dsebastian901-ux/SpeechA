from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import zipfile

from docx import Document
from openpyxl import load_workbook
import pytest

from app.services.consolidated_report_service import ConsolidatedReportService as C


def call(n, *, gestor='Ana', supervisor='Sup A', grave=False, complaint=False, text='Titular: No tengo dinero.', day='2026-11-01'):
    penalty = {'id':'PEN003' if grave else 'PEN_QUEJA_MALTRATO' if complaint else 'PEN001',
               'category':'Privacidad' if grave else 'Trato' if complaint else 'Identificación',
               'reason':'Saldo revelado a tercero' if grave else 'Queja de mala atención' if complaint else 'Presentación ausente',
               'invalidates':grave, 'points':100 if grave else 0}
    return {'file_name':f'audio_{n}.ogg','status':'completado','compliance_score':95,
            'relation':{'archivo_original':f'audio_{n}.ogg','id_llamada':str(n),'gestor':gestor,'supervisor':supervisor,
                        'fecha':day,'numero_de_tarjeta':'0123456789012345',
                        'datos_excel_original':{'Dato extra':'=SAMPLE()','Tarjeta':'0123456789012345'}},
            'classification':{'clasificacion':'FALLA_GRAVE' if grave else 'REVISAR'},
            'result':{'archivo':f'audio_{n}.ogg','texto':text,'segmentos':[]},
            'analytics_metadata':{'penalties':[penalty], 'critical_failures':[penalty] if grave else [],
                'privacy_validation':{'evidence':[{'text':'Tiene un saldo de 900 pesos.','start':12,'end':15,'speaker_role':'GESTOR'}]} if grave else {}}}


def checkpoint(tmp_path, directory, items, updated='2026-11-01T15:00:00+00:00'):
    p=tmp_path/directory/'batch_checkpoint.json';p.parent.mkdir()
    p.write_text(json.dumps({'completed':True,'updated_at':updated,'items':items}),encoding='utf-8')
    return p


def load_excel(path):
    return load_workbook(path,data_only=False)


def test_counts_each_batch_separately_as_requested_and_preserves_origins(tmp_path):
    a=checkpoint(tmp_path,'uno',[call(1),call(2,gestor='Bea',supervisor='Sup B')])
    b=checkpoint(tmp_path,'dos',[call(1,grave=True)],'2026-11-02T15:00:00+00:00')
    hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [a,b]}
    data=C.load([a,b]);assert len(data['calls'])==3
    assert not data['deduplicate'] and not data['duplicates']
    assert len({s['name'] for s in data['sources']})==2
    result=C.generate(data,tmp_path/'out',level='DETALLADO')
    w=load_excel(result['files']['xlsx'])
    try:
        assert w['DETALLE_LLAMADAS'].max_row==4
        assert len(list(w['POR_LOTE_GESTOR'].values))==4
        rows=list(w['POR_GESTOR'].values)
        assert sum(row[2] for row in rows[1:])==3
        assert sum(row[5] for row in rows[1:])==1
        assert w['DATOS_EXCEL']['B2'].value=='=SAMPLE()'
        assert w['DATOS_EXCEL']['B2'].data_type=='s'
        assert not any(c.data_type=='f' for ws in w for row in ws for c in row)
        r=list(w['DETALLE_LLAMADAS'].values);h=r[0]
        assert r[1][h.index('Tarjeta Excel')]=='0123456789012345'
        assert r[1][h.index('Día')]=='domingo'
    finally:w.close()
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==digest for p,digest in hashes.items())


def test_grave_word_and_excel_include_real_case_context_and_not_pending_complaint(tmp_path):
    p=checkpoint(tmp_path,'uno',[call(1,grave=True),call(2,complaint=True)])
    data=C.load([p]);before=deepcopy(data)
    out=C.generate(data,tmp_path/'out',level='DETALLADO',family='GRAVES',formats=('xlsx','docx'))
    assert out['calls']==out['severe_calls']==1
    assert data==before
    w=load_excel(out['files']['xlsx'])
    try:
        assert w['FALLAS_GRAVES'].max_row==2
        r=list(w['FALLAS_GRAVES'].values);assert '12–15' in r[1]
        assert not any('QUEJA' in str(c.value) for row in w['FALLAS_GRAVES'] for c in row)
    finally:w.close()
    text='\n'.join(p.text for p in Document(out['files']['docx']).paragraphs)
    for value in ['2026-11-01','domingo','0123456789012345','Ana','Sup A','PEN003','audio_1.ogg','Tiene un saldo de 900 pesos.']:
        assert value in text
    assert 'audio_2.ogg' not in text


def test_general_caps_examples_detailed_keeps_every_grave_case(tmp_path):
    p=checkpoint(tmp_path,'uno',[call(i,grave=True) for i in range(8)])
    d=C.load([p])
    a=C.generate(d,tmp_path/'out',family='GRAVES',level='GENERAL')
    b=C.generate(d,tmp_path/'out',family='GRAVES',level='DETALLADO')
    wa=load_excel(a['files']['xlsx']);wb=load_excel(b['files']['xlsx'])
    try:
        assert wa['FALLAS_GRAVES'].max_row==4
        assert wb['FALLAS_GRAVES'].max_row==9
        assert list(wa['ERRORES_COMUNES'].values)[1][2]==8
    finally:wa.close();wb.close()


def test_primary_motive_totals_examples_and_coaching_without_quality_errors(tmp_path):
    i=call(1,text='Titular: Me quedé sin trabajo. No tengo dinero.')
    i['analytics_metadata']['penalties']=[]
    p=checkpoint(tmp_path,'uno',[i,call(2,text='Titular: Ya pagué.')])
    d=C.load([p]);out=C.generate(d,tmp_path/'out',family='MOTIVOS',group_by='GESTOR')
    w=load_excel(out['files']['xlsx'])
    try:
        rows=list(w['MOTIVOS_NO_PAGO'].values)
        assert sum(r[-1] for r in rows[1:])==2
        assert {r[-2] for r in rows[1:]}=={'DESEMPLEO','PAGO_YA_REPORTADO'}
        assert w['EJEMPLOS_MOTIVOS'].max_row==3
        assert any('mora' in str(c.value) for row in w['RECOMENDACIONES_MOTIVOS'] for c in row)
    finally:w.close()


def test_duplicate_penalty_code_and_failure_only_count_one_call(tmp_path):
    i=call(1,grave=True);i['analytics_metadata']['penalties']*=2
    d=C.load([checkpoint(tmp_path,'uno',[i])]);out=C.generate(d,tmp_path/'out')
    w=load_excel(out['files']['xlsx'])
    try:assert list(w['ERRORES_COMUNES'].values)[1][2:4]==(1,1)
    finally:w.close()


def test_unknown_date_not_replaced_by_processing_date_and_filters_explicit(tmp_path):
    i=call(1,day='');j=call(2,day='02/11/2026')
    d=C.load([checkpoint(tmp_path,'uno',[i,j])])
    assert d['calls'][0]['date'] is None
    assert len(C.select(d,date_from='01/11/2026'))==1
    with pytest.raises(ValueError):C.select(d,date_from='mal')
    with pytest.raises(ValueError):C.select(d,date_from='03/11/2026',date_to='01/11/2026')


def test_recording_filename_date_is_allowed_and_not_assignment_date(tmp_path):
    i=call(1,day='');i['relation']['archivo_original']='fixture-20261014154547.ogg'
    i['relation']['fecha_asignacion']='2026-01-01'
    d=C.load([checkpoint(tmp_path,'uno',[i])])
    assert d['calls'][0]['date']==date(2026,10,14)


def test_filters_supervisor_and_gestor_exactly(tmp_path):
    p=checkpoint(tmp_path,'uno',[call(1),call(2,gestor='Ana',supervisor='Sup B'),call(3,gestor='Bea')])
    d=C.load([p]);assert len(C.select(d,gestor='Ana',supervisor='Sup B'))==1


def test_optional_dedup_uses_evaluation_time_not_file_selection_order(tmp_path):
    older=checkpoint(tmp_path,'uno',[call(1)])
    newer=checkpoint(tmp_path,'dos',[call(1,grave=True)],'2026-11-02T15:00:00+00:00')
    d=C.load([newer,older],deduplicate=True)
    assert len(d['calls'])==1 and d['calls'][0]['severe']
    assert len(d['duplicates'])==1


def test_utf8_bom_zip_and_reject_wrong_files(tmp_path):
    p=checkpoint(tmp_path,'uno',[call(1)])
    p.write_bytes(b'\xef\xbb\xbf'+p.read_bytes())
    z=tmp_path/'batch.zip'
    with zipfile.ZipFile(z,'w') as arc:arc.writestr('../../batch_checkpoint.json',p.read_bytes())
    assert len(C.load([z])['calls'])==1
    assert not (tmp_path.parent/'batch_checkpoint.json').exists()
    wrong=tmp_path/'revision.json';wrong.write_text('{"readings":[]}')
    with pytest.raises(ValueError):C.load([wrong])


def test_unknown_cards_not_completed_from_asr_and_source_mismatch_not_approved(tmp_path):
    i=call(1,grave=True,text='Tarjeta 9999888877776666.')
    i['relation']['numero_de_tarjeta']='';i['classification']['clasificacion']='APROBADO'
    d=C.load([checkpoint(tmp_path,'uno',[i])])
    assert d['calls'][0]['card']=='' and d['calls'][0]['classification']=='APROBADO'
    assert d['calls'][0]['severe']
    assert any('contradictorias' in w for w in d['warnings'])


def test_empty_grave_selection_creates_valid_word_and_excel(tmp_path):
    d=C.load([checkpoint(tmp_path,'uno',[call(1,complaint=True)])])
    out=C.generate(d,tmp_path/'out',family='GRAVES',formats=('xlsx','docx'))
    assert out['calls']==0
    assert 'No hay fallas graves' in '\n'.join(p.text for p in Document(out['files']['docx']).paragraphs)


def test_no_clinical_or_audio_analysis_executed(tmp_path,monkeypatch):
    from app.services.analytics_service import AnalyticsService
    from app.services.whisper_service import whisper_service
    def fail(*a,**k):pytest.fail('Consolidar no debe redictaminar ni retranscribir')
    monkeypatch.setattr(AnalyticsService,'analyze_transcription',fail)
    monkeypatch.setattr(whisper_service,'transcribe_audio',fail)
    d=C.load([checkpoint(tmp_path,'uno',[call(1)])])
    C.generate(d,tmp_path/'out')


def test_failed_export_removes_partial_outputs_not_sources(tmp_path,monkeypatch):
    p=checkpoint(tmp_path,'uno',[call(1,grave=True)]);raw=p.read_bytes();d=C.load([p])
    monkeypatch.setattr(C,'_word',lambda *args:(_ for _ in ()).throw(OSError('prueba de disco')))
    with pytest.raises(OSError):C.generate(d,tmp_path/'out',family='GRAVES',formats=('xlsx','docx'))
    assert list((tmp_path/'out').iterdir())==[] and p.read_bytes()==raw


def test_existing_output_not_overwritten_and_invalid_options_rejected(tmp_path):
    d=C.load([checkpoint(tmp_path,'uno',[call(1)])])
    a=C.generate(d,tmp_path/'out');before=Path(a['files']['xlsx']).read_bytes()
    b=C.generate(d,tmp_path/'out')
    assert a['directory']!=b['directory'] and Path(a['files']['xlsx']).read_bytes()==before
    with pytest.raises(ValueError):C.generate(d,tmp_path/'out',level='OTRO')
    with pytest.raises(ValueError):C.generate(d,tmp_path/'out',formats=('docx',))


def test_consolidation_and_word_generation_do_not_use_network(tmp_path,monkeypatch):
    import socket
    def forbidden(*a,**k):pytest.fail('Los reportes no deben usar internet')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    data=C.load([checkpoint(tmp_path,'uno',[call(1,grave=True)])])
    assert C.generate(data,tmp_path/'out',family='GRAVES',formats=('xlsx','docx'))['calls']==1
