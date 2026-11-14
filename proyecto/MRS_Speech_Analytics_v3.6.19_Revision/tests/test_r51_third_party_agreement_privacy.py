"""Regresión real detectada en 207 audios: un recado no puede revelar convenio.

Se preserva la distinción entre mención genérica del banco y la existencia de
un acuerdo de pago sobre la tarjeta. Si no hay diarización se exige REVISAR,
no se inventa una falta crítica confirmada.
"""
from app.services.conversation_evidence import sensitive_financial_matches, assess_privacy
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService


def test_agreement_for_card_is_sensitive_not_generic_callback():
    message = "Para generar un acuerdo de pago sobre su tarjeta Bodega Visa."
    assert sensitive_financial_matches(message)
    privacy = assess_privacy(message, third_party_confirmed=True,
                             expected_third_party=True)
    assert privacy['review_required'] or privacy['confirmed_disclosure']


def test_generic_return_call_without_agreement_is_not_sensitive():
    message = "Indíquele que se comunique con nosotros de ocho a veinte horas."
    assert not sensitive_financial_matches(message)


def test_third_party_recado_with_payment_agreement_cannot_be_approved():
    text = (
        "Buen día, ¿me puede comunicar con Juan Carlos? No se encuentra. "
        "Me comunico de MRS en representación de Bradescard. "
        "¿Puedo dejar un recado con usted? Sí. ¿Qué parentesco tiene? Un amigo. "
        "Por favor, anote el número y pídale que se comunique con nosotros. "
        "Para generar un acuerdo de pago sobre su tarjeta Bodega Visa. "
        "Gracias, le doy el recado."
    )
    transcription = TranscriptionModel.from_dict(
        {'archivo': 'recado_tercero.ogg', 'texto': text, 'duracion_segundos': 95}
    )
    analysis = AnalyticsService.analyze_transcription(
        transcription,
        {'estatus_grabacion': 'MENSAJE CON TERCERO', 'asignacion': '1PV',
         'fecha': '2026-11-09', 'numero_de_tarjeta': '1234567890123456'}
    )
    assert not analysis.metadata['shared_classification']['aprobado']
    assert analysis.metadata['shared_classification']['clasificacion'] in {
        'REVISAR', 'FALLA_GRAVE'
    }
    assert (
        analysis.metadata['privacy_validation']['review_required']
        or analysis.metadata['privacy_validation']['confirmed_disclosure']
    )
