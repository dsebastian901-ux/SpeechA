"""Regresiones de los criterios parciales: ejemplos sintéticos y fuentes separadas."""
from copy import deepcopy
import pytest
from app.services.conversation_evidence import sentence_evidence, assess_privacy, payment_places
from app.services.arco_validation import document_requests
from app.services.context_rules import prohibited_threat
from app.services.treatment_evidence import dismissive_message_evidence, offensive_asr_variants
from app.services.operational_script_evidence import receipt_request_evidence
from app.services.payment_lifecycle import payment_decision_events
from app.services.call_wait_evidence import assess_call_wait
from app.services.payment_reference_validation import callback_numbers


def test_inline_turns_do_not_transfer_financial_speech_to_the_customer():
    text='Tercero: Soy su madre Gestor: Tiene una deuda de 1500 pesos'
    rows=sentence_evidence(text)
    assert [r['speaker_role'] for r in rows]==['TERCERO','GESTOR']
    assert assess_privacy(text,third_party_confirmed=True)['confirmed_disclosure']


def test_semantic_segments_preserve_two_roles_inside_one_asr_sentence():
    text='Soy su madre tiene una deuda de 1500 pesos'
    segments=[{'text':'Soy su madre','speaker_role':'TERCERO','start':0,'end':2},
              {'text':'tiene una deuda de 1500 pesos','speaker_role':'GESTOR','start':3,'end':6}]
    assert assess_privacy(text,segments,third_party_confirmed=True)['confirmed_disclosure']


def test_conflicting_segment_and_text_roles_do_not_confirm_pen003():
    text='Gestor: Tiene una deuda de 1500 pesos.'
    segments=[{'text':text,'speaker_role':'TITULAR','start':0,'end':5}]
    result=assess_privacy(text,segments,third_party_confirmed=True)
    assert not result['confirmed_disclosure']
    assert result['review_required']


def test_prior_third_party_disclosure_survives_final_holder_transfer():
    text=('Tercero: Soy su madre. Gestor: Tiene una deuda de 1500 pesos. '
          'Titular: Ya estoy aquí. Gestor: Su deuda es de 1500 pesos.')
    result=assess_privacy(text,third_party_confirmed=False,titular=True)
    assert result['confirmed_disclosure']
    assert sum(bool(e['confirmed'])for e in result['evidence'])==1


@pytest.mark.parametrize('prefix',['No tiene comprobante; ','No tiene trabajo, pero ','En caso de duda llame al banco; '])
def test_unrelated_negation_does_not_hide_a_confirmed_disclosure(prefix):
    result=assess_privacy('Gestor: '+prefix+'su deuda es de 1500 pesos.',third_party_confirmed=True)
    assert result['confirmed_disclosure']


@pytest.mark.parametrize('text',['Gestor: Si tuviera una deuda de 1500 pesos, le explicaríamos.',
                                  'Gestor: No tiene una deuda de 1500 pesos.',
                                  'Tercero: Ya pagué su deuda de 1500 pesos.'])
def test_hypothesis_negation_or_third_party_report_is_not_confirmed_disclosure(text):
    assert not assess_privacy(text,third_party_confirmed=True)['confirmed_disclosure']


def test_current_payment_venues_are_not_hidden_by_an_old_report():
    catalog={'OXXO':['oxxo'],'KIOSKO':['kiosko'],'7 ELEVEN':['7 eleven']}
    text='Gestor: Me dijeron que pagara en Oxxo, pero ahora puede pagar en Kiosko y 7 Eleven.'
    assert {v['place'] for v in payment_places(text,[],catalog)}=={'KIOSKO','7 ELEVEN'}


def test_affirmative_venue_after_denial_keeps_its_own_scope():
    catalog={'OXXO':['oxxo'],'KIOSKO':['kiosko'],'7 ELEVEN':['7 eleven']}
    text='Gestor: No puede pagar en Oxxo; ahora puede realizar su pago en Kiosko y 7 Eleven.'
    assert {v['place'] for v in payment_places(text,[],catalog)}=={'KIOSKO','7 ELEVEN'}


@pytest.mark.parametrize('text',['Gestor: Si fuera cierto que le vamos a quitar su casa, debe denunciarlo.',
                                  'Gestor: No es cierto que le vamos a quitar su casa.',
                                  'Titular: Voy a vender mi casa para pagar.',
                                  'Titular: Me dijeron que le vamos a quitar su casa.'])
def test_negated_hypothetical_or_reported_asset_threat_is_not_direct_threat(text):
    assert not prohibited_threat(text,mora='1PV')


def test_direct_threat_after_reported_speech_is_still_found():
    text='Gestor: Me dijeron que no podían actuar, pero ahora le vamos a quitar su casa.'
    assert prohibited_threat(text,mora='1PV')


@pytest.mark.parametrize('text',['Gestor: Esto se interpreta como un chisme.',
                                  'Gestor: Se interpreta como chisme.',
                                  'Gestor: Su mensaje solo sería como un chisme.'])
def test_dismissive_interpretation_of_the_message_is_detected(text):
    assert dismissive_message_evidence(text)


@pytest.mark.parametrize('text',['Titular: Se interpreta como un chisme.',
                                  'Gestor: No se interpreta como un chisme.',
                                  'Gestor: Me dijo que se interpreta como un chisme.',
                                  'Gestor: ¿Se interpreta como un chisme?'])
def test_quoted_negated_or_question_chisme_is_not_direct_dismissal(text):
    assert not dismissive_message_evidence(text)


@pytest.mark.parametrize('text',['Conunachingada.','Con una chingada.','chinguy chinguy.'])
def test_bounded_offensive_asr_tail_variants(text):
    assert offensive_asr_variants(text)


def test_ordinary_truncated_word_does_not_become_an_insult():
    assert not offensive_asr_variants('Su tarjetaunching quedó pendiente.')


def test_arco_negated_line_proof_is_not_credited_to_an_earlier_ine_request():
    result=document_requests('Gestor: Debe enviar su INE y no le voy a pedir comprobante de titularidad de la línea.')
    assert result['ine_requested']
    assert not result['line_proof_requested']
    assert not result['both_documents_requested']


@pytest.mark.parametrize('document',['comprobante de titularidad de la línea','comprobante de propiedad de la línea',
                                      'comprobante de domicilio','recibo de la línea'])
def test_arco_documents_do_not_satisfy_payment_receipt(document):
    assert not receipt_request_evidence('Gestor: Envíe su '+document+' por WhatsApp.')['requested']


def test_final_explicit_receipt_waiver_cancels_prior_request():
    result=receipt_request_evidence('Gestor: Mande el ticket por WhatsApp. No hace falta enviar el comprobante de pago.')
    assert not result['requested']
    assert not result['review_required']


def test_new_receipt_request_after_waiver_is_valid():
    result=receipt_request_evidence('Gestor: No hace falta mandar el ticket anterior. Ahora envíe el comprobante de este pago por WhatsApp.')
    assert result['requested']


@pytest.mark.parametrize('text',['Titular: Me dijeron que voy a pagar mañana.',
                                  'Titular: Antes pensaba que voy a pagar mañana.',
                                  'Titular: Si fuera posible, voy a pagar mañana.'])
def test_reported_or_hypothetical_payment_is_not_a_new_acceptance(text):
    assert not any(e['accepted'] for e in payment_decision_events(text))


def test_new_direct_payment_decision_after_report_is_preserved():
    events=payment_decision_events('Titular: Me dijeron que no puedo pagar, pero ahora voy a pagar mañana.')
    assert events and max(events,key=lambda e:e['position'])['accepted']


def test_complete_phone_repeated_as_two_full_numbers_is_not_partial_echo():
    result=callback_numbers('Gestor: Le dejo el número 5551234567, 5551234567 para que se comunique.')
    assert result and result[0]['digits']=='5551234567'


@pytest.mark.parametrize('digits',['555 123 45, 555 123 45','55512345 67 67','5551234567 5551234568'])
def test_partial_echoes_and_conflicting_complete_phones_are_not_completed(digits):
    assert not callback_numbers('Gestor: Le dejo el número '+digits+' para que se comunique.')


def test_wait_segments_must_align_to_distinct_source_occurrences():
    text='Gestor: Buen día. Titular: Sí. Gestor: Continuamos.'
    segments=[{'text':'Buen día.','start':0,'end':2},
              {'text':'Sí.','start':3,'end':4},
              {'text':'Continuamos.','start':5,'end':6},
              {'text':'Sí.','start':80,'end':81}]
    result=assess_call_wait(text,segments,82)
    assert result['invalid_segments']==1
    assert result['usable_segments']==3


def test_failed_recovered_amount_attempt_cannot_be_used_even_if_it_contains_a_number():
    from test_asr_amount_recovery import audit,TEXT,SEGMENTS
    from app.services.asr_amount_recovery import validated_entries
    result=audit();result['entries'][0]['attempts'][1]['error']='RuntimeError'
    assert not validated_entries(TEXT,SEGMENTS,result)


def test_family_confirmation_is_invalidated_by_context_and_never_assigns_a_voice():
    from app.services.family_contact_review import make_family_confirmation,validate_family_confirmation
    item={'archivo':'synthetic.ogg','texto':'Me parece que tu hija.','segments':[],'duracion_segundos':90}
    relation={'numero_de_tarjeta':'1234567890123456','estatus_grabacion':'MENSAJE CON FAMILIAR'}
    confirmation=make_family_confirmation(item,relation,'HIJA',user_confirmed=True)
    result=validate_family_confirmation(item,relation,confirmation)
    assert result['valid'] and result['relationship']=='HIJA'
    assert 'speaker_role' not in confirmation
    other=deepcopy(item);other['texto']='Me parece que su hermana.'
    assert validate_family_confirmation(other,relation,confirmation)['review_required']


@pytest.mark.parametrize('status',['CONVENIO','NO DEFINE FECHA DE PAGO','MENSAJE CON FAMILIAR','NEGATIVA DE PAGO','ACLARACION'])
def test_excel_label_never_substitutes_for_missing_dialogue(status):
    from app.services.analytics_service import AnalyticsService
    result=AnalyticsService.calculate_basic_compliance('Buen día.',{'estatus_grabacion':status})
    assert result['final_result']!='APROBADO'
    assert result['contact_type']=='CONTACTO NO DETERMINADO'


def test_human_treatment_review_cannot_follow_replaced_audio_with_same_transcript(tmp_path):
    import json
    from app.services.review_service import ReviewService
    audio=tmp_path/'synthetic.wav';audio.write_bytes(b'primera grabacion sintetica')
    transcript=tmp_path/'synthetic.json';transcript.write_text(json.dumps({'audio_path':str(audio),'text':'Texto idéntico.'}))
    ReviewService.save(transcript,dict.fromkeys(ReviewService.FLAGS,True))
    assert ReviewService.load(transcript)['audio_verified']
    audio.write_bytes(b'grabacion reemplazada con el mismo texto')
    assert ReviewService.load(transcript)is None


def test_legacy_human_treatment_review_is_not_silently_rewritten(tmp_path):
    import hashlib,json
    from app.services.review_service import ReviewService
    transcript=tmp_path/'synthetic.json';transcript.write_text('{}')
    path=ReviewService._path(transcript);path.parent.mkdir()
    old={'transcript_sha256':hashlib.sha256(transcript.read_bytes()).hexdigest(),
         'hostile_interlocutor_exception':dict.fromkeys(ReviewService.FLAGS,True)}
    path.write_text(json.dumps(old));before=path.read_bytes()
    assert ReviewService.load(transcript)['audio_verified']
    assert path.read_bytes()==before


@pytest.mark.parametrize('phrase',['Conunachingada.','No mames.','Verga.','Quiero acostarme contigo.'])
def test_additional_asr_uses_same_offensive_tail_variants_without_inventing_speaker(phrase):
    from app.services.audio_block_evidence import validate_evidence,binding,record_digest
    result={'archivo':'synthetic.ogg','texto':'Habla MRS.','segmentos':[],'duracion_segundos':90}
    relation={'numero_de_tarjeta':'1234567890123456'}
    record={'schema':1,'kind':'AUTOMATED_ASR_ONLY','binding':binding(result,relation),
            'human_verified':False,'speaker_roles_confirmed':False,
            'segments':[{'text':phrase,'start':80,'end':81}],
            'tail_segments':[]}
    record['record_sha256']=record_digest(record)
    assessment=validate_evidence(record,result,relation,'TITULAR')
    assert assessment['valid']and assessment['review_required']
    assert any(r['type']=='EXPRESION_OFENSIVA_SIN_HABLANTE_CONFIRMADO'for r in assessment['risks'])
    assert not assessment['human_verified']
