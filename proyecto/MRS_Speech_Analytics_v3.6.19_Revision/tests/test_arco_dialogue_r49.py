import pytest
from app.services.arco_dialogue_evidence import clarified_line_tenure,listed_knowledge_denial
from app.services.conversation_evidence import dictated_privacy_email

@pytest.mark.parametrize('text',[
 '¿Cuánto tiempo lleva con esta línea? Ya tengo rato. ¿Aproximadamente, qué tiempo? Ay, no sé, unos cinco años, yo creo.',
 '¿Qué tiempo tiene con su línea telefónica? Como de semana. No la entiendo, señorita. Dos semanas.',
 'Yo acabo de comprar este celular.',
])
def test_line_tenure_can_be_clarified_or_reported_qualitatively(text):
    r=clarified_line_tenure(text);assert r['confirmed']and r['numeric_years']is None

@pytest.mark.parametrize('text',[
 '¿Cuánto tiempo lleva con esta línea? ¿Cinco años?',
 '¿Cuánto tiempo lleva recibiendo llamadas en esta línea? Cinco meses.',
 '¿Cuánto tiempo lleva con esta línea? Si tuviera cinco años, podría hacerlo.',
 'Gestor: Yo acabo de comprar este celular.',
 'No acabo de comprar este celular.',
])
def test_no_line_tenure_from_question_calls_duration_hypothesis_or_agent(text):
    assert not clarified_line_tenure(text)['confirmed']


def test_denial_of_known_and_family_is_not_denial_of_family_alone():
    assert listed_knowledge_denial('¿Conocido, familiar, parentesco con usted? No, la verdad es que no.')['confirmed']
    assert not listed_knowledge_denial('¿Es familiar? No.')['confirmed']
    assert not listed_knowledge_denial('¿Conocido, familiar? Gestor: No.')['confirmed']
    assert not listed_knowledge_denial('¿Conocido, familiar? No. Soy su hermana.')['confirmed']

@pytest.mark.parametrize('text',[
 'El correo es privacidad 1 a robabradesco.com.mx.',
 'El correo es privacidad1arrobabradesco.com.mx.',
])
def test_spoken_at_marker_fused_to_literal_domain_is_not_an_invented_domain(text):
    assert dictated_privacy_email(text)['address']=='privacidad1@bradesco.com.mx'

@pytest.mark.parametrize('text',[
 'El correo es privacidad 1 a robabradescard.com.mx.',
 'El correo es privacidad1arrobabradesco.mx.',
 'El correo es privacidad1arrobagmail.com.mx.',
 'El correo es privacidad1arrobabradesco.com.mx.estafa.',
])
def test_bad_or_incomplete_domain_remains_unconfirmed(text):
    assert not dictated_privacy_email(text)['detected']


def test_wrong_number_repeated_call_complaint_is_not_waived_by_full_arco():
    from app.services.treatment_evidence import mistreatment_reports
    text='No sé quién es esa persona. Ya estoy harta de que me estén a pregunta y pregunte por esa persona. Ya me canso de decirles que acabo de comprar este celular.'
    assert mistreatment_reports(text,[],[])
    assert not mistreatment_reports('Gestor: '+text,[],[])
