import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A


def analyze(tail):
    return A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo':'sample.wav', 'texto':'Habla MRS. Soy yo. Ya pagué 900 pesos. '
        'Envíe comprobante por WhatsApp. '+tail, 'duracion_segundos':120}),
        {'estatus_grabacion':'CONVENIO','pago_minimo':'700'})


@pytest.mark.parametrize('complaint',[
    'Una de tus compañeras me contestaron muy mal.',
    'Su compañera me contestó mal.', 'Ayer me contestaron muy mal.',
    'Una me amenazó, me dijo atente las consecuencias.',
])
def test_prior_mistreatment_blocks_paid_followup(complaint):
    a=analyze(complaint)
    assert a.metadata['quality_checks']['queja_maltrato_detectada']
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'
    assert 'PEN_QUEJA_MALTRATO' in {p['id'] for p in a.metadata['penalties']}
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('text',[
    'Nunca me contestaron muy mal.', 'No me contestó mal.',
    'Gestor: ¿Me contestaron muy mal?', 'Gestor: Me contestaron mal.',
])
def test_negation_and_agent_words_do_not_invent_customer_complaint(text):
    assert not analyze(text).metadata['quality_checks']['queja_maltrato_detectada']


@pytest.mark.parametrize('label',['','Gestor: '])
def test_dismissive_chisme_comment_has_explicit_review_reason(label):
    a=analyze(label+'Entonces para qué le dejo mensaje, nada más sería como chisme.')
    assert a.metadata['treatment_validation']['dismissive_evidence']
    assert not a.metadata['shared_classification']['aprobado']
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'
    assert 'PEN_TRATO_DESPECTIVO_REV' in {p['id'] for p in a.metadata['penalties']}


@pytest.mark.parametrize('text',[
    'Tercero: Nada más sería como chisme.',
    'Gestor: No es un chisme.', 'Gestor: No solo sería como chisme.',
    'Titular: Me dijeron que solo sería como chisme.',
])
def test_customer_quote_or_negation_does_not_invent_agent_dismissal(text):
    assert not analyze(text).metadata['treatment_validation']['dismissive_evidence']


@pytest.mark.parametrize('text',[
    'Nada más están chinguy chinguy.', 'Están chingue y chingue.',
    'Con una chingada.', 'Con unachingada.', 'Titular: Con una chingada.',
])
def test_offensive_closing_never_silently_approves(text):
    a=analyze('Gracias. Hasta luego. '+text)
    assert a.metadata['quality_checks']['groseria_bloquea_aprobacion']
    assert not a.metadata['shared_classification']['aprobado']


def test_corrupted_card_word_does_not_invent_profanity():
    assert not analyze('Su tarjetaunching ahí departamental.').metadata['quality_checks']['groseria_bloquea_aprobacion']
