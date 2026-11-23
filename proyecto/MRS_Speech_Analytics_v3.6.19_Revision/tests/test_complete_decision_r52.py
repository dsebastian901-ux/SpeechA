"""Contratos de conversación y cola; únicamente ejemplos sintéticos."""
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.services.conversation_evidence import payment_commitment, recipient_statement, holder_confirmation, assess_privacy
from app.services.batch_report_service import BatchReportService
from app.services.checkpoint_reanalysis import reanalyze_checkpoint
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel


@pytest.mark.parametrize('text',[
    '¿En qué puedo ayudar? Yo voy a pagar mañana.',
    '¿En qué puedo ayudar?Yo voy a pagar mañana.',
    'Qué quiere? Yo voy a pagar mañana.',
    'Yo voy a pagar mañana, ¿me envía los datos?',
])
def test_a_question_does_not_erase_an_independent_payment_statement(text):
    assert payment_commitment(text)['accepted']


@pytest.mark.parametrize('text',[
    '¿Yo voy a pagar mañana?',
    'Yo voy a pagar mañana?',
    '¿Puede repetir que yo voy a pagar mañana?',
    'Usted dice que yo voy a pagar mañana.',
    'Si tuviera dinero, yo voy a pagar mañana.',
    'Gestor: Yo voy a pagar mañana.',
])
def test_a_question_quote_condition_or_agent_cannot_supply_acceptance(text):
    assert not payment_commitment(text)['accepted']


def test_family_statement_survives_following_question_without_changing_voice():
    assert recipient_statement('Soy su hermano, ¿quién habla?',[],r'\bsoy su hermano\b')
    assert not recipient_statement('¿Soy su hermano?',[],r'\bsoy su hermano\b')
    assert not recipient_statement('Gestor: Soy su hermano, ¿quién habla?',[],r'\bsoy su hermano\b')


def test_nominal_company_introduction_requires_own_account_context():
    prompt='Me comunico con Persona Ejemplo, le marcamos de MRS sobre su tarjeta. '
    assert holder_confirmation(prompt+'Yo tenía que pagar el viernes.')['confirmed']
    assert not holder_confirmation(prompt+'Gracias.')['confirmed']
    assert not holder_confirmation(prompt+'Soy su hermana. Yo tenía que pagar el viernes.')['confirmed']


@pytest.mark.parametrize('reply,accepted',[
    ('Ah, bueno sí.',True),('Sí, si consigo dinero.',False),
    ('Sí, pero no puedo.',False),('¿Sí?',False),
])
def test_amount_and_date_offer_needs_firm_local_acceptance(reply,accepted):
    text='Su pago sería para el miércoles por la cantidad de mil cien pesos. '+reply
    assert payment_commitment(text)['accepted'] is accepted


def test_current_accepted_date_replaces_old_unfulfilled_promise():
    text=('¿Me puede comunicar con Persona Ejemplo? Soy yo. Habla MRS. '
          'Me comprometí a pagarlo el viernes, pero no pude. '
          'Hoy me comprometo a pagarlo y lo voy a pagar en una farmacia. '
          'El pago es de 1000 pesos. Solicito comprobante. Gracias.')
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':90}),
        {'fecha':'2026-11-09','estatus_grabacion':'CONVENIO','asignacion':'1PV','pago_minimo':'1000','saldo_total':'3000'})
    assert a.metadata['negotiation_validation']['promise_date']=='2026-11-09'


def test_rejected_agent_date_does_not_turn_a_conditional_reply_into_convenio():
    text=('¿Me puede comunicar con Persona Ejemplo? Soy yo. Habla MRS. '
          '¿Podemos contar con su pago de 1000 pesos para mañana? '
          'No puedo confirmar, estoy esperando un dinero. Gracias.')
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':90}),
        {'fecha':'2026-11-09','estatus_grabacion':'CONVENIO','asignacion':'1PV','pago_minimo':'1000','saldo_total':'3000'})
    assert a.metadata['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'


def test_financial_statement_and_following_question_still_block_third_party_disclosure():
    r=assess_privacy('Gestor: Su saldo es de 1000 pesos, ¿me escucha?',third_party_confirmed=True)
    assert r['confirmed_disclosure']


def test_partial_checkpoint_preserves_queue_and_separates_missing_excel(tmp_path):
    source=tmp_path/'source.json'
    pending={'file_name':'pending.ogg','path':'absent/pending.ogg','status':'pendiente','result':None,
             'classification':None,'relation_status':'sin_relacion'}
    done={'file_name':'done.ogg','path':'absent/done.ogg','status':'completado','relation_status':'sin_relacion',
          'result':{'archivo':'done.ogg','duracion_segundos':90,'texto':'Habla MRS. Soy yo. No puedo pagar ahorita.'}}
    payload={'mode':'A','completed':False,'items':[done,pending]}
    source.write_text(json.dumps(payload),encoding='utf-8');original=source.read_bytes()
    result=reanalyze_checkpoint(source,tmp_path/'out')
    saved=json.loads(Path(result['checkpoint']).read_text())
    assert result['evaluations']==1 and result['pending_preserved']==1
    assert saved['items'][1]==pending and not saved['completed']
    assert saved['items'][0]['classification']['clasificacion']=='SIN_RELACION_EXCEL'
    assert source.read_bytes()==original
    book=load_workbook(result['report'],read_only=True,data_only=True)
    try:
        rows=list(book['RESULTADOS'].values);head=rows[0]
        assert rows[2][head.index('Resultado Final Operativo')]=='PENDIENTE DE PROCESAMIENTO'
        assert rows[1][head.index('Resultado Final Operativo')]=='CORREGIR RELACIÓN CON EXCEL'
        summary=dict(book['RESUMEN'].values)
        assert summary['Audios procesados']==1 and summary['Pendientes de procesamiento']==1
        assert book['RELACION_DATOS_ORIGEN'].max_row==3
    finally:book.close()


def test_approval_percentage_does_not_count_unprocessed_calls(tmp_path):
    items=[{'status':'completado','file_name':'approved.ogg','classification':{'clasificacion':'APROBADO','aprobado':True},'compliance_score':100},
           {'status':'pendiente','file_name':'pending.ogg'}]
    result=BatchReportService.generate_report(items,tmp_path/'project/02_Audios/Transcripciones')
    book=load_workbook(result,read_only=True,data_only=True)
    try:assert dict(book['RESUMEN'].values)['% aprobación']==100
    finally:book.close()


def test_caching_never_shares_mutable_evidence_or_survives_an_evaluation():
    from app.services.conversation_cache import evaluation_cache,current_cache
    from app.services.conversation_evidence import sentence_evidence
    @evaluation_cache
    def evaluate():
        text='Soy su hermano.'
        segments=[{'text':text,'speaker_role':'TERCERO','start':0,'end':2}]
        first=sentence_evidence(text,segments)
        first[0]['speaker_role']='GESTOR'
        assert sentence_evidence(text,segments)[0]['speaker_role']=='TERCERO'
        assert current_cache() is not None
    evaluate()
    assert current_cache() is None


def test_rejected_offer_is_th_and_a_later_firm_acceptance_supersedes_it():
    declined='¿Podemos disponer de ese pago el día de hoy? No.'
    assert payment_commitment(declined)['declined']
    assert not payment_commitment(declined)['accepted']
    assert payment_commitment(declined+' Mañana voy a pagar.')['accepted']
    assert not payment_commitment('Gestor: '+declined)['declined']


def test_generic_balance_and_account_count_are_not_a_financial_amount():
    assert not assess_privacy('Gestor: Tiene saldo pendiente de una tarjeta.',third_party_confirmed=True)['confirmed_disclosure']
    assert not assess_privacy('Gestor: Saldo de tres cuentas.',third_party_confirmed=True)['confirmed_disclosure']
    assert assess_privacy('Gestor: Su saldo es de 1500.',third_party_confirmed=True)['confirmed_disclosure']


def test_factual_relay_and_receipt_are_combined_without_waiving_a_refusal():
    base=('Soy su hermano. Habla MRS. Le dejo un número para que se comunique con nosotros. '
          '¿Tiene dónde anotar? Sí, claro. El número es 5512345678. '
          'Es importante que se comunique. Gracias.')
    relation={'estatus_grabacion':'MENSAJE CON FAMILIAR'}
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':base,'duracion_segundos':90}),relation)
    assert a.metadata['status_validation']['detected_status']=='MENSAJE CON FAMILIAR'
    refused=base+' No le voy a pasar el recado.'
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':refused,'duracion_segundos':90}),relation)
    # 23/11: revocar recado cambia estatus, no acredita falta del gestor.
    assert a.metadata['status_validation']['detected_status']=='SE NIEGAN A TOMAR RECADO'
    assert not a.metadata['message_workflow_validation']['complete']
    assert a.metadata['shared_classification']['clasificacion']=='APROBADO_SIN_ETIQUETAR'


def test_accusation_of_mockery_does_not_become_an_approved_status_retag():
    text='Habla MRS. Soy yo. ¿Se está burlando de mí? Ahorita no puedo pagar.'
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':90}),
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO'})
    assert a.metadata['treatment_validation']['mistreatment_report_evidence']
    assert not a.metadata['shared_classification']['calidad_aprobada']


@pytest.mark.parametrize('word',['chingarazo','chingadazo'])
def test_compound_profanity_is_not_silently_approved(word):
    text='Habla MRS. Soy yo. No puedo pagar ahorita. '+word
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':90}),
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO'})
    assert a.metadata['quality_checks']['groseria_bloquea_aprobacion']
    assert not a.metadata['shared_classification']['calidad_aprobada']


def test_damaged_mora_word_requires_evidence_without_inventing_a_critical_failure():
    r=assess_privacy('Presenta tres nacionalidades vencidas de su tarjeta.',third_party_confirmed=True)
    assert r['review_required'] and not r['confirmed_disclosure']


def test_asset_collection_threat_is_not_just_a_valid_monthly_offer():
    from app.services.context_rules import prohibited_threat
    text='Se hará cobrar en el domicilio fiscal el monto total de los 15.575 en bienes y muebles.'
    assert prohibited_threat(text,mora='B')
    assert not prohibited_threat('Titular: '+text,mora='B')
    assert not prohibited_threat('No se hará cobrar en bienes y muebles.',mora='B')


def test_remainder_date_alternatives_are_not_silently_replaced_with_the_first_date():
    from app.services.accepted_schedule_evidence import unresolved_remainder_dates
    text='No, pues los 500 pesos y ya los otros, el 15 o el 16.'
    assert unresolved_remainder_dates(text)
    assert not unresolved_remainder_dates('Gestor: '+text)
    assert not unresolved_remainder_dates('Dice que '+text)


def test_reported_conflicting_prior_service_blocks_approval():
    text=('Habla MRS. Soy yo. Me acaban de hablar y una persona me dice una cosa y otra persona otra cosa. '
          'No puedo pagar ahorita.')
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':90}),
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO'})
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert not a.metadata['shared_classification']['calidad_aprobada']
