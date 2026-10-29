"""Reglas del bloque y lectura ASR aislada con dobles explícitos del modelo."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.audio_block_review import review_audio_block,select_audio_matches
from app.services.conversation_evidence import assess_privacy,unknown_recipient_response
from app.services.payment_instruction_validation import only_negated_transfers,transfer_is_option_listing


def analyze(text,**context):
    return A.analyze_transcription(TranscriptionModel('synthetic.ogg','synthetic.ogg',text,duration_seconds=100),
        {'estatus_grabacion':'CONVENIO','fecha':'2026-10-22','asignacion':'1FLP','corte':'25',
         'vencimiento':'2026-10-25','pago_minimo':'1000','saldo_total':'5000',**context})


def test_listing_of_banks_does_not_make_other_authorized_options_unsafe():
    text=('Habla MRS. Soy yo. Puede pagar en Kiosko o en tiendas 3B, '
          'o mediante transferencia de BBVA, Citibanamex, Santander. '
          'Mañana hago el depósito. El pago es de 1200 pesos mañana. Envíe el comprobante por WhatsApp.')
    a=analyze(text);p=a.metadata['convenio_payment_validation']
    assert p['transfer_option_listing_only'] and not p['transfer_data_review']
    assert p['authorized_places_count']==2
    assert a.metadata['final_result']=='APROBADO'


@pytest.mark.parametrize('text,places',[
    ('Mediante transferencia de BBVA.', ['KIOSKO']),
    ('Puede realizar una transferencia de BBVA.', ['KIOSKO','3B']),
    ('¿Puedo hacer transferencia de BBVA?', ['KIOSKO','3B']),
    ('Mediante transferencia de BBVA. La CLABE es 123456789.', ['KIOSKO','3B']),
    ('Mediante transferencia de BBVA. El convenio numero 99999.', ['KIOSKO','3B']),
    ('Mediante transferencia a la cuenta personal.', ['KIOSKO','3B']),
    ('Mediante transferencia de BBVA desde su banca móvil.', ['KIOSKO','3B']),
])
def test_real_or_incomplete_transfer_instruction_does_not_get_listing_exception(text,places):
    assert not transfer_is_option_listing(text,(),places)


def test_listing_with_missing_cash_options_keeps_transfer_review():
    a=analyze('Habla MRS. Soy yo. Puede pagar en Kiosko, o mediante transferencia de BBVA. '
              'El pago es de 1200 pesos mañana. Voy a pagar mañana. Envíe comprobante por WhatsApp.')
    assert a.metadata['convenio_payment_validation']['transfer_data_review']
    assert a.metadata['final_result']=='REVISAR'


@pytest.mark.parametrize('text',[
    'Ya no se pueda hacer transferencia.', 'No se puede realizar una transferencia.',
    'No puede hacer transferencia.',
])
def test_negated_transfer_variants(text):
    assert only_negated_transfers(text)


def test_mixed_negative_and_positive_transfer_instructions_still_require_validation():
    assert not only_negated_transfers('No puede hacer transferencia hoy. Puede hacer transferencia mañana.')


def test_last_confirmed_day_is_not_replaced_by_earlier_notification():
    r=A._extract_payment_promise_date_details('Hoy me confirmaron su negativa. '
        'Entonces confirmo nuevamente 1200 el día 24. Que tenga buen día.','2026-10-22')
    assert r['date'].isoformat()=='2026-10-24'


def test_short_amount_answer_is_not_lost_without_pesos():
    a=analyze('Habla MRS. Soy yo. ¿Ya tendrá el pago para hoy? Sí. '
        '¿De qué cantidad? De mil quinientos. '
        'Puede pagar en Kiosko o en tiendas 3B. Envíe comprobante por WhatsApp.')
    assert a.metadata['negotiation_validation']['monto_detectado']==1500


@pytest.mark.parametrize('role',['','Gestor: ','Cliente: '])
def test_final_expletive_is_detected_without_inventing_speaker_role(role):
    a=analyze('Habla MRS. Soy yo. Ya pagué 1500 pesos. '
        'Envíe comprobante por WhatsApp. Hasta luego. '+role+'Qué poca madre.')
    assert a.metadata['quality_checks']['groseria_bloquea_aprobacion']
    assert a.metadata['final_result']==('FALLA_GRAVE' if role=='Gestor: ' else 'REVISAR')
    assert a.metadata['treatment_validation']['offensive_language_evidence']
    assert 'PEN003' not in {p['id'] for p in a.metadata['penalties']}


def test_privacy_phrase_split_between_acoustic_segments_is_preserved():
    text='Soy su amiga. Le informo que presenta una mensualidad vencida.'
    segments=[{'texto':'Soy su amiga. Le informo que presenta una','inicio':0,'fin':3},
              {'texto':'mensualidad vencida.','inicio':3,'fin':5}]
    p=assess_privacy(text,segments,third_party_confirmed=True)
    assert p['review_required'] and not p['confirmed_disclosure']
    assert p['evidence'][0]['start']==0 and p['evidence'][0]['end']==5


def test_known_agent_disclosure_split_between_segments_still_blocks():
    text='Le informo que presenta una mensualidad vencida.'
    segments=[{'texto':'Le informo que presenta una','inicio':0,'fin':3,'speaker_role':'GESTOR'},
              {'texto':'mensualidad vencida.','inicio':3,'fin':5,'speaker_role':'GESTOR'}]
    p=assess_privacy(text,segments,third_party_confirmed=True)
    assert p['confirmed_disclosure']


@pytest.mark.parametrize('text',[
    '¿No la conoce para nada? No, para nada, señorita.',
    '¿No lo conoces? No, jamás.',
])
def test_explicit_no_knowledge_answer(text):
    assert unknown_recipient_response(text)['confirmed']


@pytest.mark.parametrize('text',[
    '¿No la conoce? No.', '¿No la conoce? No, para nada. Sí la conozco.',
    '¿No la conoce? Gestor: No, para nada.',
])
def test_ambiguous_contradictory_or_agent_answer_does_not_confirm_unknown_recipient(text):
    assert not unknown_recipient_response(text)['confirmed']


def test_unspecific_years_with_number_are_a_qualitative_tenure_confirmation():
    a=analyze('Habla MRS. No la conozco. Yo tengo años con este número.',
              estatus_grabacion='NO CONOCEN A DEUDOR')
    assert a.metadata['quality_checks']['tiempo_con_linea']


@pytest.fixture
def example(tmp_path):
    audio=tmp_path/'audio';audio.mkdir();(audio/'synthetic.ogg').write_bytes(b'mocked_audio')
    source=tmp_path/'checkpoint.json'
    payload={'items':[{'file_name':'synthetic.ogg','result':{'archivo':'synthetic.ogg','texto':'Texto original.',
        'segmentos':[{'texto':'Texto original.','inicio':0,'fin':100}],'duracion_segundos':100,'modelo':'small'},
        'relation':{'nombre_final':'cuenta_ejemplo','numero_de_tarjeta':'1234567890123456'},
        'classification':{'clasificacion':'REVISAR','motivo':'Evidencia pendiente'},
        'financial_audio_review':{'example':'record must stay untouched'}}]}
    source.write_text(json.dumps(payload));return source,audio,payload


def reader_factory(*args):
    def reader(path,duration):
        return {'text':'Lectura alternativa.','segments':[{'start':0,'end':100,'text':'Lectura alternativa.'}],
                'tail_text':'Gracias.','tail_segments':[{'start':95,'end':100,'text':'Gracias.'}],
                'human_verified':True,'classification':{'aprobado':True}}
    return reader


def test_separate_audio_review_does_not_mutate_checkpoint_or_trust_reader_approval(example,tmp_path):
    source,audio,payload=example;raw=source.read_bytes();data=(audio/'synthetic.ogg').read_bytes()
    result=review_audio_block(source,audio,tmp_path/'output',reader_factory=reader_factory,duration_reader=lambda path:100)
    assert source.read_bytes()==raw and (audio/'synthetic.ogg').read_bytes()==data
    saved=json.loads(Path(result['evidence']).read_text());assert saved['completed_calls']==1 and saved['completed']
    assert saved['items'][0]['original_text']=='Texto original.'
    assert saved['items'][0]['original_segments']==payload['items'][0]['result']['segmentos']
    assert saved['items'][0]['human_verified'] is False and saved['speaker_roles_confirmed'] is False
    assert 'classification' not in saved['items'][0] and saved['checkpoint_modified'] is False
    assert Path(result['report']).is_file()


def test_unknown_audio_name_is_not_guessed_by_index(example):
    source,audio,payload=example;(audio/'synthetic.ogg').rename(audio/'different.ogg')
    with pytest.raises(ValueError,match='Ningún audio'):
        select_audio_matches(payload,audio)


def test_aliases_cannot_create_two_readings_for_same_call(example):
    source,audio,payload=example;(audio/'cuenta_ejemplo.ogg').write_bytes(b'mocked_audio')
    with pytest.raises(ValueError,match='dos archivos'):
        select_audio_matches(payload,audio)


def test_duration_mismatch_is_error_and_not_an_asr_success(example,tmp_path):
    source,audio,payload=example
    result=review_audio_block(source,audio,tmp_path/'output',reader_factory=reader_factory,duration_reader=lambda path:200)
    saved=json.loads(Path(result['evidence']).read_text())
    assert result['errors']==1 and result['completed_calls']==0
    assert saved['completed'] is False and saved['whisper_executed'] is False


def test_missing_cached_model_does_not_create_empty_successful_review(example,tmp_path):
    source,audio,payload=example
    def unavailable(*args):raise RuntimeError('Modelo local ausente')
    with pytest.raises(RuntimeError,match='local ausente'):
        review_audio_block(source,audio,tmp_path/'output',reader_factory=unavailable)
    assert not (tmp_path/'output').exists()


def test_empty_asr_does_not_count_as_complete(example,tmp_path):
    source,audio,payload=example
    result=review_audio_block(source,audio,tmp_path/'output',reader_factory=lambda *args:lambda *args:{'text':'','segments':[]},duration_reader=lambda path:100)
    saved=json.loads(Path(result['evidence']).read_text())
    assert saved['errors']==1 and not saved['completed']


def test_asr_evidence_cannot_import_a_speaker_role_from_reader(example,tmp_path):
    source,audio,payload=example
    def factory(*args):
        def reader(*args):return {'text':'Lectura.','segments':[{'start':0,'end':1,'text':'Lectura.','speaker_role':'GESTOR','human_verified':True}]}
        return reader
    result=review_audio_block(source,audio,tmp_path/'output',reader_factory=factory,duration_reader=lambda path:100)
    segment=json.loads(Path(result['evidence']).read_text())['items'][0]['segments'][0]
    assert 'speaker_role' not in segment and 'human_verified' not in segment


def test_empty_text_with_segments_is_not_success(example,tmp_path):
    source,audio,payload=example
    result=review_audio_block(source,audio,tmp_path/'output',reader_factory=lambda *args:lambda *args:{'text':' ', 'segments':[{'start':0,'end':1,'text':' '}]},duration_reader=lambda path:100)
    assert result['errors']==1 and result['completed_calls']==0


def test_interrupted_customer_transfer_question_is_not_waived():
    a=analyze('Titular: Ya pagué 1200 pesos. ¿Puedo hacer, es una transferencia?\n'
              'Gestor: Correcto, desde su banco.')
    assert a.metadata['convenio_payment_validation']['transfer_data_review']


def test_place_enumeration_can_answer_customer_question_about_where_to_cover_payment():
    from app.services.conversation_evidence import payment_places
    catalog={'KIOSKO':['kiosko'],'3B':['tiendas 3b']}
    evidence=payment_places('Titular: ¿Tengo que cubrir en la tienda?\nGestor: En Kiosko o tiendas 3B.',(),catalog)
    assert {e['place'] for e in evidence}=={'KIOSKO','3B'}


def test_customer_listing_alone_does_not_supply_two_agent_payment_places():
    from app.services.conversation_evidence import payment_places
    assert not payment_places('Titular: ¿Puedo pagar en Kiosko o tiendas 3B?',(),{'KIOSKO':['kiosko'],'3B':['tiendas 3b']})


def test_larger_folder_is_rejected_before_loading_model(example,tmp_path):
    source,audio,payload=example
    original=payload['items'][0];payload['items']=[]
    for n in range(11):
        item=deepcopy(original);item['file_name']=f'call-{n}.ogg';item['result']['archivo']=item['file_name']
        payload['items'].append(item);(audio/item['file_name']).write_bytes(b'mocked_audio')
    (audio/'synthetic.ogg').unlink();source.write_text(json.dumps(payload))
    def no_load(*args):raise AssertionError('model should not load')
    with pytest.raises(ValueError,match='más de 10'):
        review_audio_block(source,audio,tmp_path/'output',reader_factory=no_load)
    assert not (tmp_path/'output').exists()


def test_asr_evidence_file_is_not_accepted_as_a_batch_checkpoint(example,tmp_path):
    source,audio,payload=example;payload['items'][0].pop('result');source.write_text(json.dumps(payload))
    def no_load(*args):raise AssertionError('model should not load')
    with pytest.raises(ValueError,match='checkpoint del lote'):
        review_audio_block(source,audio,tmp_path/'output',reader_factory=no_load)
    assert not (tmp_path/'output').exists()


@pytest.mark.parametrize('answer',['16 dígitos de la tarjeta','24 de octubre'])
def test_quantity_question_does_not_turn_identifier_length_or_date_into_money(answer):
    a=analyze('Habla MRS. Soy yo. ¿De qué cantidad? De '+answer+'.')
    assert a.metadata['negotiation_validation']['monto_detectado'] is None


def test_later_explicit_knowledge_does_not_get_ignored_after_a_short_answer():
    text='¿No la conoce? No, para nada. '+('Se verifica la información. '*12)+'Sí la conozco.'
    assert not unknown_recipient_response(text)['confirmed']
