import pytest
from copy import deepcopy
from app.services.status_message_evidence import return_purpose,extra_message_receipt
from app.services.conversation_evidence import assess_recado,payment_commitment
from app.services.dialogue_evaluation import full_payment_refusal
from app.services.status_output_label import corrected_status_label
from app.services.analytics_service import AnalyticsService
from app.models.transcriptions import TranscriptionModel

@pytest.mark.parametrize('reply',['Sí.','Claro.','Ajá.','Sí, dígame.'])
def test_note_receipt_with_actual_return_and_complete_contact(reply):
 text='Soy su hermana. ¿Tiene con qué anotar un número? '+reply+' El número telefónico es 5551234567. Es importante que se comunique con nosotros.'
 assert extra_message_receipt(text)
 assert not extra_message_receipt(text.replace(reply,'Gestor: '+reply))
 assert not extra_message_receipt(text.replace('5551234567','555'))

@pytest.mark.parametrize('bad',[
 '¿Tiene con qué anotar un número? No puedo. El número telefónico es 5551234567.',
 'Diga que tiene con qué anotar un número. Sí. El número telefónico es 5551234567.',
 '¿Tiene con qué anotar un número? Sí, pero no le voy a dar el recado. El número telefónico es 5551234567.',
 '¿Tiene con qué anotar un número? Sí? El número telefónico es 5551234567.',
])
def test_negated_quoted_and_question_receipts_are_not_accepted(bad):
 assert not extra_message_receipt(bad+' Es importante que se comunique con nosotros.')


def test_actual_contact_and_acceptance_complete_return_message_without_literal_recado():
 text=('Habla MRS. Soy su mamá. ¿Podría anotar un número telefónico para que posteriormente el señor Pedro se pueda comunicar con nosotros? '
       'Sí. Le confirmo el número telefónico 5551234567. Ok. El señor Pedro puede comunicarse de ocho a nueve para su tarjeta.')
 model=TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':125})
 a=AnalyticsService.analyze_transcription(model,{'estatus_grabacion':'MENSAJE CON FAMILIAR','asignacion':'C3','numero_de_tarjeta':'1234567890123456'})
 assert a.metadata['status_validation']['detected_status']=='MENSAJE CON FAMILIAR'
 assert a.metadata['status_validation']['valid']


def test_affirmative_bridge_does_not_turn_unconditional_refusal_into_hypothesis():
 c=payment_commitment('Claro, sí, pero no lo voy a pagar, imagínese lo que debía.')
 assert c['declined']and full_payment_refusal(c)
 assert not full_payment_refusal(dict(c,evidence='Si cambian los intereses no lo voy a pagar.'))
 assert not full_payment_refusal(dict(c,evidence='No lo voy a pagar, esos intereses.'))
 assert not full_payment_refusal(dict(c,evidence='Diga que no lo voy a pagar.'))


def test_high_confidence_without_trace_is_still_not_retaggable():
 m={'status_validation':{'matches':False,'detection_confidence':'ALTA','review_required':False,'detected_status':'ACLARACION',
    'excel_status':'NO CONOCEN A DEUDOR','evidence_method':'SEGUIMIENTO_DE_PAGO_REPORTADO_SIN_ACREDITACION_BANCARIA','evidence':''},
    'operational_context':{'numero_de_tarjeta':'1234567890123456','nombre_final':'0001234567890123456_C3_300_NC_AGENTE_MRS_20261108'}}
 assert not corrected_status_label(m)['valid']
 m['status_validation']['evidence']='Ya realicé mi pago ayer, solicitan el comprobante.'
 label=corrected_status_label(m);assert label['valid']and label['corrected_name']=='0001234567890123456_C3_300_ACLARA_AGENTE_MRS_20261108'


def test_reported_payment_status_carries_original_evidence_for_output_correction():
 text=('Habla MRS. ¿Me puede comunicar con Ana López? Sí, soy yo. Mi tarjeta ya la pagué ayer. '
       '¿Mandó el comprobante a algún número de WhatsApp? Sí, ya lo mandé. Estamos esperando que se actualice el pago.')
 a=AnalyticsService.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':130}),
   {'estatus_grabacion':'NO CONOCEN A DEUDOR','numero_de_tarjeta':'1234567890123456','asignacion':'C3',
    'nombre_final':'0001234567890123456_C3_300_NC_AGENTE_MRS_20261108'})
 s=a.metadata['status_validation'];assert s['detected_status']=='ACLARACION'and s['evidence']
 assert a.metadata['shared_classification']['output_label_correction']['valid']
 assert a.metadata['shared_classification']['clasificacion']=='APROBADO_ETIQUETA_CORREGIDA'
 unsafe=AnalyticsService.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text+' En la llamada anterior me trataron mal.','duracion_segundos':130}),
   {'estatus_grabacion':'NO CONOCEN A DEUDOR','numero_de_tarjeta':'1234567890123456','asignacion':'C3','nombre_final':'0001234567890123456_C3_300_NC_AGENTE_MRS_20261108'})
 assert not unsafe.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('phrase',['Le corroboro','Le corroporo'])
def test_contact_confirmation_is_local_and_keeps_role_and_digit_limits(phrase):
 text='Dígale que se comunique con nosotros. El número de teléfono es 5551234567, '+phrase+' 55, 51, ¿correcto? Sí.'
 assert extra_message_receipt(text)
 assert not extra_message_receipt(text.replace('Sí.','Gestor: Sí.'))
 assert not extra_message_receipt(text.replace('Sí.','No.'))


def test_phone_relay_and_retagging_do_not_approve_a_refused_message():
 text='Habla MRS. Soy su hermana. ¿Tiene con qué anotar un número? Sí. El teléfono es 5551234567. Es importante que se comunique con nosotros. No quiero pasar el recado.'
 a=AnalyticsService.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.ogg','texto':text,'duracion_segundos':130}),
    {'estatus_grabacion':'MENSAJE EN TRABAJO','asignacion':'C3','numero_de_tarjeta':'1234567890123456','nombre_final':'0001234567890123456_C3_300_3EROS_AGENTE_MRS_20261108'})
 assert not a.metadata['shared_classification']['aprobado']


def test_previous_desk_invalidated_payment_is_a_complaint_not_clean_followup():
 from app.services.treatment_evidence import mistreatment_reports
 text='Yo ya pagué. Le mandé el recibo al corporativo y no me hicieron válido el pago.'
 assert mistreatment_reports(text,[],[])
 assert not mistreatment_reports('Yo ya pagué. Habla el corporativo. Falta esperar la actualización del pago.',[],[])
 assert not mistreatment_reports('Yo ya pagué. Habla el corporativo. Gestor: No me hicieron válido el pago.',[],[])
