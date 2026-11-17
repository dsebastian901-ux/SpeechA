"""El sujeto de la gestión y las peticiones completas prevalecen sobre palabras sueltas."""
import pytest
from app.services.management_subject_evidence import management_subject
from app.services.contact_dialogue_resolution import declared_intermediary
from app.services.operational_script_evidence import receipt_request_evidence
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A

OPEN='¿Se encuentra Paula Referente? ¿De dónde habla? Habla MRS. Sí, ella habla. '
MESSAGE=('Le dejo un recado para que se comunique con nosotros al número de contacto '
         '5512345678. Sí, le paso el recado.')


@pytest.mark.parametrize('purpose',[
    'El motivo de la llamada es simplemente confirmar si usted conoce a la señorita Luisa Deudora. ',
    'El fin de la llamada es confirmar si se encuentra la señorita Luisa Deudora. ',
    'Lo que pasa es que la señorita Luisa Deudora dejó su número como referencia. ',
    'Lo que pasa es que Luisa Deudora dejó un número como referencia. ',
    'Ella me deja este número como número de contacto. ',
    'Estoy tratando de localizar a la señorita Luisa Deudora. ',
])
def test_named_receiver_is_not_holder_of_another_persons_account(purpose):
    text=OPEN+purpose+MESSAGE
    assert management_subject(text)['confirmed']
    assert declared_intermediary(text)['confirmed']
    result=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'ejemplo.ogg',
        'texto':text,'duracion_segundos':130,'segmentos':[]}),{}).metadata
    assert result['quality_contact_type']=='TERCERO'
    assert not result['negotiation_validation']['missing_collection_attempt_penalty']


@pytest.mark.parametrize('text',[
    OPEN+'El fin de la llamada es confirmar si se encuentra Paula Referente. Mi tarjeta ya la pagué.',
    OPEN+'Usted dejó un número como referencia. Mi tarjeta ya la pagué.',
    OPEN+'Titular: La señorita Luisa Deudora dejó su número como referencia. '+MESSAGE,
    OPEN+'Diga que la señorita Luisa Deudora dejó su número como referencia. '+MESSAGE,
    OPEN+'La señorita Luisa Deudora no dejó su número como referencia. '+MESSAGE,
    OPEN+'La señorita Luisa Deudora dejó su número como referencia. Ya se lo paso. Soy yo, el titular.',
])
def test_own_account_quotes_denials_and_transfer_do_not_fix_entire_call_as_third_party(text):
    assert not management_subject(text)['confirmed']


def test_receiver_denial_of_knowing_target_is_not_a_contradiction_of_own_name():
    text=OPEN+'Lo que pasa es que Luisa Deudora dejó un número como referencia. ¿La conoce? No, no sé quién es.'
    m=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'ejemplo.ogg',
        'texto':text,'duracion_segundos':130,'segmentos':[]}),{}).metadata
    assert not m['contact_conflict_validation']['review_required']
    assert m['quality_contact_type']=='NO CONOCEN A DEUDOR'
    assert m['arco_validation']['applies']


@pytest.mark.parametrize('phrase',[
    'Reporte el comprobante al número de WhatsApp.',
    'Reporta el comprobante al número de validación por WhatsApp.',
    'Para que me pueda hacer llegar la foto de su pago al número de WhatsApp.',
])
def test_real_later_receipt_request_resolves_earlier_uncertain_mention(phrase):
    text='Comprobante de pago. Tiene WhatsApp. '+phrase
    result=receipt_request_evidence(text)
    assert result['requested'] and not result['review_required']


@pytest.mark.parametrize('phrase',[
    'No reporta el comprobante al WhatsApp.',
    'Titular: Reporta el comprobante al número de validación.',
    'Haga llegar la foto de su INE.',
    'Mande el comprobante de línea telefónica.',
])
def test_negative_or_other_document_does_not_satisfy_payment_receipt(phrase):
    assert not receipt_request_evidence(phrase)['requested']
