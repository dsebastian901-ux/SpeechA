from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.quality_decision import evaluate_quality
from app.services.status_output_label import corrected_status_label,audio_output_filename,STATUS_LABEL_POLICY
from app.services.corrected_label_export import export_corrected_labels
from app.services.batch_report_service import BatchReportService
from app.services.retagging_report import add_retagging_sheets,record_label_export
from openpyxl import Workbook,load_workbook

CARD='0000111122223333'
NAME=CARD+'_1PV_352_PP_AGENT E._MRS_20261105'


def metadata():
    return {'quality_contact_type':'TITULAR','quality_checks':{},'penalties':[],
        'critical_failures':[],'privacy_validation':{},'negotiation_validation':{'valid':True},
        'status_validation':{'excel_status':'CONVENIO','detected_status':'NO DEFINE FECHA DE PAGO',
            'valid':False,'matches':False,'review_required':False,'detection_confidence':'ALTA',
            'evidence_method':'PENDING_DECISION','evidence':'No tengo esa cantidad.',
            'reasons':['Estatus distinto con evidencia alta.']},
        'operational_context':{'nombre_final':NAME,'numero_de_tarjeta':CARD}}


def item():
    text=('Habla MRS. Soy yo. Puede realizar un pago de 1000 pesos mañana. '
          'Puede pagar en Farmacias del Ahorro y 7-Eleven. '
          'Envíe su comprobante por WhatsApp. No tengo esa cantidad.')
    raw={'archivo':'source.ogg','texto':text,'duracion_segundos':150}
    relation={'archivo_original':'source.ogg','nombre_final':NAME,'numero_de_tarjeta':CARD,
              'estatus_grabacion':'CONVENIO','asignacion':'1PV','fecha':'2026-11-05',
              'corte':'20','vencimiento':'2026-11-20','pago_minimo':1000,'saldo_total':3000}
    a=A.analyze_transcription(TranscriptionModel.from_dict(raw),relation)
    d=A.shared_quality_decision(a.metadata,a.compliance_score,80,150,{'estatus_autorizado':True,'tiene_nombre_final':True})
    assert d['clasificacion']=='APROBADO_ETIQUETA_CORREGIDA'
    return {'file_name':'source.ogg','result':raw,'relation':relation,'analytics_metadata':a.metadata,
            'analytics':a.to_dict(),'classification':d,'compliance_score':a.compliance_score,'status':'completado'}


@pytest.mark.parametrize('status,code',[
    ('MENSAJE CON TERCERO','3EROS'),('MENSAJE CON FAMILIAR','3EROS'),
    ('MENSAJE EN TRABAJO','3EROS'),('RECADO REF1','3EROS'),('ACLARACION','ACLARA'),
    ('NO CONOCEN A DEUDOR','NC'),('NEGATIVA DE PAGO','NP'),('CONVENIO','PP'),
    ('NO DEFINE FECHA DE PAGO','TH'),
])
def test_user_catalog_is_exact(status,code):
    assert STATUS_LABEL_POLICY['codes'][status]==code
    assert len(STATUS_LABEL_POLICY['codes'])==9


@pytest.mark.parametrize('score',[80,90,100])
def test_only_status_component_changes_in_the_separate_approved_category(score):
    m=metadata();original=deepcopy(m)
    d=evaluate_quality(m,score)
    assert d['clasificacion']=='APROBADO_ETIQUETA_CORREGIDA' and d['aprobado']
    label=d['output_label_correction']
    assert label['folder']=='APROBADOS_ETIQUETA_CORREGIDA'
    a=NAME.split('_');b=label['corrected_name'].split('_')
    assert [i for i,(x,y) in enumerate(zip(a,b)) if x!=y]==[3]
    assert b[3]=='TH' and a[3]=='PP'
    assert m==original


@pytest.mark.parametrize('field,value',[
    ('privacy_validation',{'review_required':True}),
    ('privacy_validation',{'confirmed_disclosure':True}),
    ('quality_contact_type','CONTACTO NO DETERMINADO'),
    ('card_validation',{'result':'TARJETA INCORRECTA'}),
    ('arco_validation',{'applies':True,'valid':False}),
    ('quality_checks',{'queja_maltrato_detectada':True}),
    ('quality_checks',{'groseria_bloquea_aprobacion':True}),
    ('wait_validation',{'review_required':True}),
    ('home_recovery_warning',{'review_required':True}),
    ('negotiation_validation',{'valid':False,'reasons':['Acuerdo no válido']}),
])
def test_status_correction_does_not_waive_any_safety_or_financial_block(field,value):
    m=metadata();m[field]=value
    assert not evaluate_quality(m,100)['clasificacion'].startswith('APROBADO')


@pytest.mark.parametrize('change',[
    {'detection_confidence':'MEDIA'},{'review_required':True},{'evidence':''},{'matches':None},
])
def test_ambiguous_status_or_missing_evidence_does_not_authorize_a_rename(change):
    m=metadata();m['status_validation'].update(change)
    assert not corrected_status_label(m)['valid']


@pytest.mark.parametrize('evidence',[
    'Yo solicito lo que es el pago de mil pesos, pero no lo confirmo a usted.',
    'Yo requiero el pago de mil pesos, no lo confirmo a usted.',
    'Yo le solicito su pago de mil pesos, no lo confirmo.',
    'Si se vuelve a hacer una compra, ya no voy a pagar nada.',
    'Si tuviera otra tarjeta, no voy a pagar esta.',
])
def test_payment_instruction_or_hypothetical_refusal_cannot_authorize_status_correction(evidence):
    m=metadata();m['status_validation'].update(evidence_method='SIN_COMPROMISO_FIRME_RESPUESTA_EXPLICITA',evidence=evidence)
    assert not corrected_status_label(m)['valid']
    assert evaluate_quality(m,100)['clasificacion']=='REVISAR'


@pytest.mark.parametrize('name',[
    '../'+NAME, 'C:\\outside\\'+NAME, CARD+'_PP',
    '9999999999999999_1PV_352_PP_AGENT_MRS_20261105',
    CARD+'_1PV_352_UNCONFIGURED_AGENT_MRS_20261105',
])
def test_unsafe_unknown_or_wrong_account_filename_is_not_relabelled(name):
    m=metadata();m['operational_context']['nombre_final']=name
    assert not corrected_status_label(m)['valid']


def test_abbreviated_agent_name_and_original_audio_extension_are_preserved():
    assert audio_output_filename(NAME,'.ogg')==NAME+'.ogg'
    assert audio_output_filename(NAME+'.wav','.ogg')==NAME+'.ogg'


def test_report_shows_both_original_and_actual_corrected_output():
    i=item();r=BatchReportService._row_from_item(i)
    assert r['Estatus Excel']=='CONVENIO' and r['Estatus de salida']=='NO DEFINE FECHA DE PAGO'
    assert r['Nombre antes de reetiquetar']==NAME
    assert r['Nombre final']==NAME.replace('_PP_','_TH_')
    assert r['Validación Dictamen']=='CORREGIDO EN COPIA'


def test_export_rechecks_rules_copies_binary_bytes_and_preserves_sources(tmp_path):
    i=item();p=tmp_path/'checkpoint.json';p.write_text(json.dumps({'items':[i]}),encoding='utf-8');raw=p.read_bytes()
    audio=tmp_path/'originals';audio.mkdir();source=audio/'source.ogg';source.write_bytes(b'OggS\x00\x81\xff audio original')
    source_bytes=source.read_bytes()
    result=export_corrected_labels(p,audio,tmp_path/'copies')
    assert result['copied']==1 and not result['whisper_executed']
    files=list((tmp_path/'copies'/'APROBADOS_ETIQUETA_CORREGIDA').rglob('*.ogg'))
    assert len(files)==1 and files[0].name==NAME.replace('_PP_','_TH_')+'.ogg'
    assert files[0].read_bytes()==source_bytes==source.read_bytes()
    assert p.read_bytes()==raw
    m=json.loads(Path(result['manifest']).read_text())
    assert m['calls'][0]['audio_sha256']==hashlib.sha256(source_bytes).hexdigest()


def test_forged_saved_approval_cannot_copy_a_call_with_prior_mistreatment(tmp_path):
    i=item();i['result']['texto']+=' En la llamada anterior me trataron muy mal.'
    p=tmp_path/'checkpoint.json';p.write_text(json.dumps({'items':[i]}),encoding='utf-8')
    audio=tmp_path/'audio';audio.mkdir();(audio/'source.ogg').write_bytes(b'OggS')
    with pytest.raises(ValueError,match='ya no cumple'):
        export_corrected_labels(p,audio,tmp_path/'copies')
    assert not (tmp_path/'copies').exists()


def test_missing_or_duplicate_original_audio_never_selects_an_arbitrary_file(tmp_path):
    p=tmp_path/'checkpoint.json';p.write_text(json.dumps({'items':[item()]}),encoding='utf-8')
    root=tmp_path/'audio';root.mkdir()
    for name in ['one','two']:
        d=root/name;d.mkdir();(d/'source.ogg').write_bytes(b'OggS'+name.encode())
    with pytest.raises(ValueError,match='duplicado'):
        export_corrected_labels(p,root,tmp_path/'copies')
    assert not (tmp_path/'copies').exists()


def test_two_calls_with_same_output_keep_the_name_using_distinct_subdirectories(tmp_path):
    a=item();b=deepcopy(a);b['file_name']='second.ogg';b['result']['archivo']='second.ogg'
    p=tmp_path/'checkpoint.json';p.write_text(json.dumps({'items':[a,b]}),encoding='utf-8')
    root=tmp_path/'audio';root.mkdir()
    (root/'source.ogg').write_bytes(b'OggS1');(root/'second.ogg').write_bytes(b'OggS2')
    result=export_corrected_labels(p,root,tmp_path/'copies')
    files=list((tmp_path/'copies').rglob('*.ogg'))
    assert result['copied']==2 and len(files)==2
    assert files[0].name==files[1].name==NAME.replace('_PP_','_TH_')+'.ogg'
    assert {f.read_bytes() for f in files}=={b'OggS1',b'OggS2'}


def test_final_report_lists_accounts_and_actions_without_claiming_uncopied_audio(tmp_path):
    i=item();i['relation'].update(gestor='=AGENT',supervisor='Supervisor Ejemplo')
    w=Workbook();detail,summary=add_retagging_sheets(w,[i,{'classification':{'clasificacion':'REVISAR'}}])
    assert detail.max_row==2 and summary.max_row==2
    row=dict(zip([c.value for c in detail[1]],[c.value for c in detail[2]]))
    assert row['Cuenta / tarjeta']==CARD
    assert row['Estatus Excel anterior']=='CONVENIO' and row['Estatus correcto']=='NO DEFINE FECHA DE PAGO'
    assert 'Corregir estatus_grabacion' in row['Corrección a realizar por el gestor']
    assert row['Estado de copia']=='ETIQUETA CALCULADA; COPIA PENDIENTE' and not row['Ruta de copia']
    assert not any(c.data_type=='f' for ws in [detail,summary] for row in ws for c in row)
    w.close()


def test_report_marks_only_verified_completed_copies(tmp_path):
    i=item();p=tmp_path/'checkpoint.json';p.write_text(json.dumps({'items':[i]}),encoding='utf-8')
    audio=tmp_path/'audio';audio.mkdir();(audio/'source.ogg').write_bytes(b'OggS copied bytes')
    result=export_corrected_labels(p,audio,tmp_path/'copied')
    report=tmp_path/'report.xlsx';w=Workbook();add_retagging_sheets(w,[i]);w.save(report);w.close()
    record_label_export(report,result['manifest'])
    w=load_workbook(report,read_only=True);rows=list(w['CUENTAS_REETIQUETADAS'].values)
    assert rows[1][rows[0].index('Estado de copia')]=='COPIA GENERADA'
    assert Path(rows[1][rows[0].index('Ruta de copia')]).read_bytes()==b'OggS copied bytes'
    w.close()


@pytest.mark.parametrize('tamper',['incomplete','wrong_hash','missing_audio'])
def test_unfinished_or_changed_copy_does_not_modify_the_report(tmp_path,tamper):
    i=item();p=tmp_path/'checkpoint.json';p.write_text(json.dumps({'items':[i]}),encoding='utf-8')
    audio=tmp_path/'audio';audio.mkdir();(audio/'source.ogg').write_bytes(b'OggS copied bytes')
    copied=export_corrected_labels(p,audio,tmp_path/'copied');manifest=Path(copied['manifest'])
    data=json.loads(manifest.read_text());destination=Path(data['calls'][0]['destination'])
    if tamper=='incomplete':data['completed']=False
    elif tamper=='wrong_hash':data['calls'][0]['audio_sha256']='0'*64
    else:destination.unlink()
    manifest.write_text(json.dumps(data),encoding='utf-8')
    report=tmp_path/'report.xlsx';w=Workbook();add_retagging_sheets(w,[i]);w.save(report);w.close();before=report.read_bytes()
    with pytest.raises(ValueError):record_label_export(report,manifest)
    assert report.read_bytes()==before


def test_new_batch_copy_uses_the_corrected_folder_and_keeps_the_source(tmp_path):
    from app.services.batch_service import BatchService
    i=item();source=tmp_path/'source.ogg';source.write_bytes(b'OggS batch bytes');i['path']=str(source)
    batch=BatchService.__new__(BatchService)
    output=Path(batch._copy_classified_audio(i,None,i['classification'],tmp_path/'outputs'/'Transcripciones'))
    assert output.parent.name=='APROBADOS_ETIQUETA_CORREGIDA'
    assert output.name==NAME.replace('_PP_','_TH_')+'.ogg'
    assert output.read_bytes()==source.read_bytes()==b'OggS batch bytes'


@pytest.mark.parametrize('original_status',['CONVENIO','NO DEFINE FECHA DE PAGO'])
def test_unaccepted_proposal_uses_actual_scenario_for_script_scoring(original_status):
    i=item();relation=dict(i['relation'],estatus_grabacion=original_status)
    text='Habla MRS. Soy yo. Puede realizar un pago de 1000 pesos mañana. No tengo esa cantidad.'
    a=A.analyze_transcription(TranscriptionModel.from_dict(dict(i['result'],texto=text)),relation)
    assert not a.metadata['convenio_payment_validation']['applies']
    assert not {'PEN_CONV_LUGARES','PEN_CONV_WHATSAPP'} & {p['id'] for p in a.metadata['penalties']}
    assert a.compliance_score==100


def test_rejecting_charges_is_not_a_global_refusal_but_final_full_refusal_is():
    from app.services.dialogue_evaluation import full_payment_refusal,pending_status,scan_dialogue
    assert not full_payment_refusal({'declined':True,'accepted':False,'evidence':'No voy a pagar esos intereses.'})
    refusal={'declined':True,'accepted':False,'evidence':'No voy a pagar.'}
    assert full_payment_refusal(refusal)
    assert pending_status(scan_dialogue('No tengo esa cantidad. No voy a pagar.'),refusal) is None


def test_catalog_accepts_the_two_column_header_shown_by_the_user(tmp_path):
    from app.services.relation_service import RelationService
    p=tmp_path/'accounts.xlsx';w=Workbook();r=w.active;r.title='Relacion_Audios'
    r.append(['archivo_original','gestor','estatus_grabacion','nombre_final'])
    r.append(['source.ogg','Agente','CONVENIO',NAME])
    c=w.create_sheet('Catalogos');c.append(['estatus_grabacion','ESTATUS EETIQUETA'])
    for status,code in STATUS_LABEL_POLICY['codes'].items():c.append([status,code])
    w.save(p);w.close();raw=p.read_bytes()
    service=RelationService();summary=service.load_excel(p)
    assert len(summary['estatus_autorizados'])==9
    assert all(service.is_status_authorized(s) for s in STATUS_LABEL_POLICY['codes'])
    assert not service.is_status_authorized('BUZON')
    assert p.read_bytes()==raw


def test_explicitly_disabled_catalog_does_not_reauthorize_statuses_from_rows(tmp_path):
    from app.services.relation_service import RelationService
    p=tmp_path/'accounts.xlsx';w=Workbook();r=w.active;r.title='Relacion_Audios'
    r.append(['archivo_original','gestor','estatus_grabacion','nombre_final'])
    r.append(['source.ogg','Agente','CONVENIO',NAME])
    c=w.create_sheet('Catalogos');c.append(['estatus_grabacion','activo']);c.append(['CONVENIO','NO'])
    w.save(p);w.close()
    service=RelationService();service.load_excel(p)
    assert not service.is_status_authorized('CONVENIO')


def test_non_catalog_status_is_never_authorized_by_a_nonempty_filename():
    from app.services.relation_service import RelationService
    service=RelationService();service.authorized_statuses=['BUZON','CONVENIO','RECADO_REF1']
    assert service.is_status_authorized('CONVENIO')
    assert service.is_status_authorized('RECADO REF1')
    assert not service.is_status_authorized('BUZON')


def test_windows_entry_point_performs_reanalysis_copy_and_final_account_report(tmp_path):
    import subprocess,sys
    i=item();p=tmp_path/'checkpoint.json';p.write_text(json.dumps({'items':[i]}),encoding='utf-8');before=p.read_bytes()
    audio=tmp_path/'audio';audio.mkdir();(audio/'source.ogg').write_bytes(b'OggS command bytes')
    app=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,str(app/'tools/reanalyze_checkpoint.py'),
        '--checkpoint',str(p),'--output-dir',str(tmp_path/'analysis'),
        '--copy-corrected-labels','--audio-dir',str(audio),'--labels-output-dir',str(tmp_path/'copies')],
        capture_output=True,text=True,cwd=app)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'CUENTAS_REETIQUETADAS' in result.stdout
    report=tmp_path/'analysis'/'04_Reportes'/'Reporte_Reanalisis_Reglas.xlsx'
    w=load_workbook(report,read_only=True)
    rows=list(w['CUENTAS_REETIQUETADAS'].values)
    assert rows[1][rows[0].index('Estado de copia')]=='COPIA GENERADA'
    assert rows[1][rows[0].index('Cuenta / tarjeta')]==CARD
    assert w['MOTIVOS_NO_PAGO']['B2'].value=='GENERADO'
    w.close();assert p.read_bytes()==before


def analyze_mistag(text,status,code):
    relation={'estatus_grabacion':status,'nombre_final':NAME.replace('_PP_','_'+code+'_'),
              'numero_de_tarjeta':CARD,'asignacion':'1PV','fecha':'2026-11-05','vencimiento':'2026-11-20',
              'corte':'20','pago_minimo':1000,'saldo_total':3000}
    return A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':150}),relation)


def test_confirmed_holder_mistagged_as_unknown_debtor_does_not_require_arco():
    a=analyze_mistag('Habla MRS. Soy yo. Esta es mi tarjeta. Puede realizar un pago de 1000 pesos mañana. No puedo confirmar una fecha de pago.',
                    'NO CONOCEN A DEUDOR','NC')
    assert not a.metadata['arco_validation']['applies']
    assert a.metadata['quality_contact_type']=='TITULAR'
    assert a.metadata['shared_classification']['clasificacion']=='APROBADO_ETIQUETA_CORREGIDA'
    assert a.metadata['shared_classification']['output_label_correction']['corrected_code']=='TH'


def test_complete_family_message_mistagged_as_agreement_uses_the_actual_script():
    text=('Gestor: Habla MRS. ¿Se encuentra el titular?\n'
          'Tercero: Soy su hija. No se encuentra.\n'
          'Gestor: ¿Puede tomar un recado y un número de contacto?\n'
          'Tercero: Sí, yo le paso el recado y tomo el número.\n'
          'Gestor: Dígale que se comunique al 55 12 34 56 78 con MRS.\n'
          'Tercero: Sí, ya lo anoté y se lo doy.')
    a=analyze_mistag(text,'CONVENIO','PP')
    assert a.metadata['status_validation']['recado_evidence']['confirmed_recado']
    assert a.metadata['status_validation']['matches'] is False
    assert not a.metadata['convenio_payment_validation']['applies']
    assert a.metadata['shared_classification']['clasificacion']=='APROBADO_ETIQUETA_CORREGIDA'
    assert a.metadata['shared_classification']['output_label_correction']['corrected_code']=='3EROS'


def test_complete_unknown_debtor_arco_mistagged_as_reference_does_not_require_a_family_message():
    text=('Gestor: Habla MRS. ¿Conoce al titular?\n'
          'Tercero: No lo conozco. Tengo dos años con esta línea.\n'
          'Gestor: Puede ejercer sus derechos ARCO. Envíe INE y comprobante de su línea '
          'a privacidad1@bradesco.com.mx.')
    a=analyze_mistag(text,'RECADO REF1','3EROS')
    assert a.metadata['arco_validation']['applies'] and a.metadata['arco_validation']['valid']
    assert not a.metadata['status_validation'].get('recado_evidence')
    assert a.metadata['shared_classification']['clasificacion']=='APROBADO_ETIQUETA_CORREGIDA'
    assert a.metadata['shared_classification']['output_label_correction']['corrected_code']=='NC'


def test_actual_owner_with_own_account_evidence_mistagged_as_reference_can_correct_the_status():
    a=analyze_mistag('Habla MRS. Soy yo. Esta es mi tarjeta. Puede realizar un pago de 1000 pesos mañana. No puedo confirmar una fecha de pago.',
                    'RECADO REF1','3EROS')
    assert a.metadata['quality_contact_type']=='TITULAR'
    assert not a.metadata['status_validation'].get('recado_evidence')
    assert a.metadata['shared_classification']['clasificacion']=='APROBADO_ETIQUETA_CORREGIDA'
