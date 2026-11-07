"""Aclaración del usuario: dos lugares restan 20, sin bloqueo adicional a 80."""
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A

TEXT=('Soy yo. Titular: Me comprometo a pagar 900 pesos el 6 de noviembre de 2026. '
      'Gestor: Confirma su convenio. Envíe su comprobante por WhatsApp.')
RELATION={'fecha':'2026-11-05','vencimiento':'2026-11-10','asignacion':'1PV',
          'pago_minimo':'900','saldo_total':'3000','corte':'20','estatus_grabacion':'CONVENIO'}

def analyze(text):
    return A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':100}),RELATION)

def test_missing_places_keeps_twenty_point_deduction_and_can_approve_at_eighty():
    a=analyze('Habla MRS. '+TEXT)
    p=next(p for p in a.metadata['penalties'] if p['id']=='PEN_CONV_LUGARES')
    assert p['points']==20 and not p['invalidates']
    assert not a.metadata['convenio_payment_validation']['minimum_places_met']
    assert a.compliance_score==80 and a.metadata['shared_classification']['clasificacion']=='APROBADO'

def test_another_ordinary_omission_still_fails_the_threshold():
    a=analyze(TEXT)
    assert a.compliance_score<80
    assert not a.metadata['shared_classification']['aprobado']

def test_sufficient_score_with_missing_places_does_not_waive_a_complaint():
    a=analyze('Habla MRS. '+TEXT+' Titular: Me trataron mal en la llamada anterior.')
    assert a.compliance_score==80
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'


def test_accusation_of_prior_insult_in_question_blocks_otherwise_eighty():
    a=analyze('Habla MRS. '+TEXT+' Titular: ¿Usted fue la que me insultó el otro día o no?')
    assert a.compliance_score==80
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'


def test_agent_question_is_not_customer_complaint():
    a=analyze('Habla MRS. '+TEXT+' Gestor: ¿Usted fue la que me insultó el otro día o no?')
    assert not a.metadata['quality_checks']['queja_maltrato_detectada']


def test_customer_denies_insult_instead_of_reporting_one():
    a=analyze('Habla MRS. '+TEXT+' Titular: Usted nunca me insultó. Gracias por su atención.')
    assert not a.metadata['quality_checks']['queja_maltrato_detectada']


def test_report_of_threatening_collection_blocks_otherwise_eighty():
    a=analyze('Habla MRS. '+TEXT+' Titular: Hasta parece que le están amenazando a uno. No me espantan, pero eso no es una forma de cobrar.')
    assert a.compliance_score==80
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'


def test_denial_of_threatening_service_is_not_a_report():
    a=analyze('Habla MRS. '+TEXT+' Titular: No parece que me están amenazando. Todo bien.')
    assert not a.metadata['quality_checks']['queja_maltrato_detectada']


def test_asr_realizarle_offer_counts_the_authorized_brands_in_its_list():
    a=analyze('Habla MRS. '+TEXT+' Gestor: Si le queda lejos la tienda, puede realizarle una tienda 3B, tiendas Neto, farmacias de la oro, Círculo-K, 7-11.')
    p=a.metadata['convenio_payment_validation']
    assert p['authorized_places_count']==5 and p['minimum_places_met']
    assert not any(p['id']=='PEN_CONV_LUGARES' for p in a.metadata['penalties'])


def test_negated_realizarle_offer_cannot_validate_a_payment_list():
    a=analyze('Habla MRS. '+TEXT+' Gestor: No puede realizarle una tienda 3B, tiendas Neto ni Círculo-K.')
    assert a.metadata['convenio_payment_validation']['authorized_places_count']==0
