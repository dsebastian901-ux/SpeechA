import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A


def analyze(text, **relation):
    return A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo':'sample.wav', 'texto':text, 'duracion_segundos':120}),
        {'asignacion':'1PV', **relation})


@pytest.mark.parametrize('phrase',[
    'Yo no sé quién es usted señorita.', 'Y no lo conozco su nombre.',
    'No sé quién es su propósito.', 'No conozco al gestor.',
])
def test_unknown_agent_is_not_unknown_debtor(phrase):
    a=analyze('Habla MRS. Soy yo. Ya pagué 900 pesos. '+phrase)
    assert a.metadata['quality_contact_type']!='NO CONOCEN A DEUDOR'
    assert not a.metadata['arco_validation']['unknown_recipient_confirmed']
    assert 'PEN_ARCO_OMISION' not in {p['id'] for p in a.metadata['penalties']}


@pytest.mark.parametrize('phrase',[
    'No lo conozco.', 'No sé quién es.', 'No conozco a ese señor.',
    'No conozco a Juan Pérez.', 'El número es equivocado.',
])
def test_true_unknown_debtor_keeps_full_arco_requirement(phrase):
    a=analyze('Habla MRS. '+phrase)
    assert a.metadata['quality_contact_type']=='NO CONOCEN A DEUDOR'
    assert 'PEN_ARCO_OMISION' in {p['id'] for p in a.metadata['penalties']}
    assert not a.metadata['shared_classification']['aprobado']


def test_agent_reference_does_not_hide_a_separate_real_unknown_debtor():
    a=analyze('No sé quién es usted. No conozco a ese señor.')
    assert a.metadata['arco_validation']['unknown_recipient_confirmed']


@pytest.mark.parametrize('text',[
    'Estoy un poquito retirado de mi casa.', 'Titular: Estoy retirado de mi casa.',
    'Gestor: No le vamos a quitar su casa.',
    'Titular: Le vamos a quitar su casa.',
    'Me dijeron que le vamos a quitar su casa.',
])
def test_distance_negation_and_customer_words_are_not_agent_threats(text):
    a=analyze('Habla MRS. Soy yo. '+text)
    assert 'PEN012' not in {p['id'] for p in a.metadata['penalties']}


@pytest.mark.parametrize('text',[
    'Le vamos a quitar su casa.', 'Vamos a retirar sus bienes.',
    'Gestor: Recogeremos sus muebles.', 'La vamos a demandar.',
])
def test_direct_asset_or_lawsuit_threat_remains_critical(text):
    a=analyze('Habla MRS. Soy yo. '+text)
    assert 'PEN012' in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['shared_classification']['clasificacion']=='FALLA_GRAVE'
