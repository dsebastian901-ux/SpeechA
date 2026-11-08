"""Causas de revisión: conversación verificable y límites de cada corrección."""
import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.contact_dialogue_resolution import contact_dialogue_evidence,expanded_unknown_response
from app.services.conversation_evidence import holder_confirmation,assess_privacy
from app.services.arco_context_evidence import spoken_privacy_email
from app.services.payment_reference_validation import find_reference
from app.services.operational_script_evidence import receipt_request_evidence


def analyze(text,status='MENSAJE CON FAMILIAR'):
 return A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':130}),{'estatus_grabacion':status,'numero_de_tarjeta':'1234567890123456','asignacion':'C3'})

@pytest.mark.parametrize('reply',['Su hija.','Soy hija.','Suprimo.','Mi familia.','Su esposa.'])
def test_local_relationship_replies_are_understood_without_excel(reply):
 text='¿Qué parentesco tiene con ella? '+reply
 assert contact_dialogue_evidence(text)['family']
 assert not contact_dialogue_evidence(text.replace(reply,'Gestor: '+reply))['family']

@pytest.mark.parametrize('reply',['Un amigo.','Conocida.','Soy una vecina.'])
def test_third_party_relationship_answers(reply):
 assert contact_dialogue_evidence('¿Qué parentesco tiene con ella? '+reply)['third_party_relationships']

@pytest.mark.parametrize('text',[
 '¿Conocido o familiar de él? No, esto es que trabaja aquí.',
 '¿Conocida familiar? No, es mi hermana.',
 '¿Conocido familiar? Gestor: No.',
 'Diga que conocido familiar. No.',
])
def test_relation_lists_do_not_invent_unknown_person(text):
 assert not expanded_unknown_response(text)['confirmed']

@pytest.mark.parametrize('text',[
 '¿Algún amigo conocido familiar con este nombre? No.',
 'Conocida, familias, parentesco con usted, ¿verdad? No.',
 'Yo no tengo conocido esa persona.',
 'No soy la persona que buscan.',
])
def test_explicit_unknown_statements_are_evidence(text):
 assert expanded_unknown_response(text)['confirmed']

@pytest.mark.parametrize('answer',['Habló su esposo.','No, es su hermana.'])
def test_yes_to_nominal_question_does_not_override_proxy_identification(answer):
 text='¿Tengo el gusto con Ana López? Sí. '+answer+' Mi tarjeta la voy a pagar mañana.'
 assert not holder_confirmation(text)['confirmed']


def test_own_payment_after_named_request_resolves_holder_context():
 text='¿Me comunico con Ana López? ¿Quién me llama? Habla MRS. Ya realicé pago, yo no debo nada.'
 assert holder_confirmation(text)['confirmed']


def test_institutional_attribution_is_local_and_does_not_fake_acoustic_voice():
 text='Nos comunicamos de jurídico MRS por atraso de su tarjeta.'
 p=assess_privacy(text,third_party_confirmed=True)
 assert p['confirmed_disclosure']and not p['review_required']
 e=next(e for e in p['evidence']if e['confirmed']);assert not e['role_evidence']['human_verified']and not e['role_evidence']['acoustic_voice_identified']

@pytest.mark.parametrize('text',[
 'Me dijeron que nos comunicamos de jurídico MRS por atraso de su tarjeta.',
 'Tercero: Nos comunicamos de jurídico MRS por atraso de su tarjeta.',
 'Nos comunicamos de jurídico MRS. Ya pagué. Tiene una deuda de 500 pesos.',
 'Habla MRS. Soy su hermana. Tiene una deuda de 500 pesos.',
 'Nos comunicamos de jurídico MRS por saldo pendiente.',
 'Nos comunicamos de jurídico MRS por saldo vencido.',
])
def test_local_attribution_does_not_extend_to_quotes_turns_or_generic_balances(text):
 assert not assess_privacy(text,third_party_confirmed=True)['confirmed_disclosure']


def test_later_complete_email_is_considered_after_rejected_partial_attempt():
 text='Privacidad uno arroba roba bradesco punto mx. Le repito, privacidad uno a robabradesco.com.mx.'
 assert spoken_privacy_email(text)['detected']
 assert not spoken_privacy_email('Privacidad uno a robabradesco punto mx.')['detected']
 assert not spoken_privacy_email('Privacidad uno arroba otrobanco.com.mx.')['detected']


def test_callback_echo_is_not_declared_an_incomplete_card_reference():
 text='Le dejo un número de contacto para que me regale una llamada. Su tarjeta. 22, 25. 22, 25.'
 p=find_reference(text,'1234567890123456');assert not p['requires_review']and p['excluded_callback_numbers']
 assert find_reference(text.replace('Su tarjeta.','Referencia de pago:'),'1234567890123456')['requires_review']
 assert find_reference(text.replace('22, 25. 22, 25.','1234567890123457'),'1234567890123456')['requires_review']


def test_card_ending_is_never_a_balance_but_five_digits_remain_uncertain():
 a=analyze('Habla MRS. Soy su hermana. Le paso el recado. Dígale que se comunique al número de teléfono 5551234567. Su tarjeta termina 163.89.')
 assert a.metadata['negotiation_validation']['saldo_informado_detectado']is None
 assert a.metadata['card_validation']['result'].startswith('REVISAR')


def test_past_receipt_question_is_followup_not_an_uncertain_new_request():
 p=receipt_request_evidence('¿Mandó el comprobante a algún número de WhatsApp? Sí, uno que me dieron.')
 assert p['reported_sent']and not p['requested']and not p['review_required']
 assert not receipt_request_evidence('¿Mandó el comprobante a WhatsApp? No.')['reported_sent']
 assert not receipt_request_evidence('¿Mandó el comprobante a WhatsApp? Gestor: Sí.')['reported_sent']

@pytest.mark.parametrize('status',['MENSAJE CON FAMILIAR','CONVENIO','ACLARACION'])
def test_death_followup_preserves_original_status_only_with_complete_evidence(status):
 text=('Habla MRS. Mi mamá ya falleció. Va a mandar acta de defunción e INE del titular y de quien tramita. '
       'Le dejo el número de teléfono 5551234567. ¿Dónde anota? Aquí lo tengo. Gracias.')
 a=analyze(text,status);s=a.metadata['status_validation']
 assert a.metadata['death_followup_validation']['valid']and s['matches']and s['valid']and s['status_preserved_by_policy']
 unsafe=analyze(text+' Tiene una deuda de 1500 pesos.',status)
 assert not unsafe.metadata['shared_classification']['aprobado']
 assert not analyze(text.replace('ya falleció','vive todavía'),status).metadata['death_followup_validation']['valid']


def test_clear_service_complaint_closes_nonapproval_but_other_safety_uncertainty_remains():
 a=analyze('Habla MRS. Soy su hermana. En la llamada anterior me trataron mal.')
 assert a.metadata['shared_classification']['clasificacion']=='NO_APROBADO'
 b=analyze('Habla MRS. Soy su hermana. En la llamada anterior me trataron mal. Tiene una deuda de 1500 pesos.')
 assert b.metadata['shared_classification']['clasificacion']=='REVISAR'

@pytest.mark.parametrize('reply',['No se encuentra, ¿de parte de quién?','No está, dígame.','No se encuentra de parte de quién?'])
def test_absence_reply_to_named_request_is_a_third_party_even_with_followup_question(reply):
 from app.services.contact_dialogue_resolution import declared_intermediary
 assert declared_intermediary('¿Me puede comunicar con Ana López? '+reply)['confirmed']
 assert not declared_intermediary('¿Me puede comunicar con Ana López? Gestor: '+reply)['confirmed']


def test_absence_of_a_document_or_later_handoff_does_not_identify_third_party():
 from app.services.contact_dialogue_resolution import declared_intermediary
 assert not declared_intermediary('¿Se encuentra su saldo en la aplicación? No está.')['confirmed']
 assert not declared_intermediary('¿Me puede comunicar con Ana López? No se encuentra. Se lo comunico. Soy yo.')['confirmed']



def test_reports_count_only_real_review_per_agent_and_keep_technical_errors_separate(tmp_path):
 from copy import deepcopy
 from openpyxl import load_workbook
 from app.services.batch_report_service import BatchReportService
 categories=['APROBADO','REVISAR','NO_APROBADO','FALLA_GRAVE','ERROR']
 items=[]
 for n,c in enumerate(categories):
  items.append({'file_name':f'synthetic{n}.ogg','status':'error'if c=='ERROR'else'completado','message':'synthetic error'if c=='ERROR'else'',
      'relation':{'gestor':'Agente sintético','numero_de_tarjeta':'1234567890123456','estatus_grabacion':'MENSAJE CON TERCERO'},
      'classification':{'clasificacion':c,'aprobado':c=='APROBADO','cumple_puntaje':True},'analytics_metadata':{'final_result':c},'compliance_score':100})
 path=BatchReportService.generate_report(items,tmp_path/'project/02_Audios/Transcripciones')
 w=load_workbook(path,data_only=True)
 try:
  rows=list(w['RESULTADOS'].values);head=rows[0];idx=head.index('Clasificación física');assert [r[idx]for r in rows[1:]]==categories
  g=w['RESUMEN_GESTORES'];rows=list(g.values);d=dict(zip(rows[0],rows[1]));assert d['Revisar']==1 and d['No aprobados']==1 and d['Errores de procesamiento']==1
  assert 'REVISION_PENDIENTE'in w
 finally:w.close()



def test_sender_continuation_is_not_receiver_acknowledgement_but_receiver_same_number_is():
 from app.services.conversation_evidence import assess_recado
 from app.services.message_dialogue_evidence import existing_callback_confirmation
 text='Habla MRS. Dígale que se comunique. El número telefónico es 5551234567. Le digo, aquí sería importante que se comunique.'
 assert not assess_recado(text)['acceptance']
 text='Dígale que se comunique. Le dicto un número telefónico. El número telefónico es 5551234567. ¿Lo podría repetir? Sí, de hecho es el mismo número.'
 assert existing_callback_confirmation(text)
 assert not existing_callback_confirmation(text.replace('Sí, de hecho es el mismo número.','Gestor: Sí, de hecho es el mismo número.'))


def test_real_receiver_ready_and_hr_relay_survive_sender_ack_guard():
 from app.services.message_contact_evidence import message_contact_evidence
 text='Dígale que se comunique. ¿Le puedo dictar un número de llamada? Un número de llamada. Sí. Listo, dígame. El número es 5551234567.'
 assert any(e['method']=='RECEPTOR_LISTO_PARA_DICTADO_OFRECIDO'for e in message_contact_evidence(text)['acceptance'])
 assert not any(e['method']=='RECEPTOR_LISTO_PARA_DICTADO_OFRECIDO'for e in message_contact_evidence(text.replace('Listo, dígame.','Gestor: Listo, dígame.'))['acceptance'])
 text='Este teléfono es laboral. Dígale que se comunique al número telefónico 5551234567. Y ahorita lo paso le digo a Recursos Humanos para que actualicen.'
 evidence=message_contact_evidence(text)
 assert evidence['work_relationships']and evidence['acceptance']
 for variant in [text.replace('Y ahorita','No, ahorita'),text.replace('Y ahorita','Diga que ahorita'),text.replace('Y ahorita','Gestor: Y ahorita')]:
  assert not any(e['method']=='RECEPTOR_TRANSMITE_CONTACTO_A_RECURSOS_HUMANOS'for e in message_contact_evidence(variant)['acceptance'])


def test_no_writing_material_and_unresolved_service_complaint_cannot_approve():
 from app.services.definitive_rejection import explicit_message_refusal
 text='¿Le puedo dejar un recado? Sí. Dígale que se comunique. ¿Puede tomar nota del número? No traigo aquí en qué apuntar, señorita. Voy a contactar más tarde. Hasta luego.'
 assert explicit_message_refusal(text)['confirmed']
 assert not explicit_message_refusal(text.replace('Voy a contactar más tarde.','El número telefónico es 5551234567. Ya lo anoté.'))['confirmed']
 from app.services.treatment_evidence import mistreatment_reports
 text='Yo solicité la cancelación de mi tarjeta. Por esa incompetencia de tu equipo yo tengo que pagar. No tienen al personal capacitado para resolver las dudas.'
 assert mistreatment_reports(text,[],[])
 assert not mistreatment_reports('La tarjeta está activa. Gestor: Por esa incompetencia de tu equipo tengo que pagar.',[],[])
