"""Identificación por conversación propia; no depende de la etiqueta del Excel."""
import pytest
from app.services.conversation_evidence import holder_confirmation


@pytest.mark.parametrize('question,response',[
    ('¿Me puede comunicar con Persona Ejemplo? Sí.', 'Me dijeron que mi cuenta está cancelada.'),
    ('¿Me puede comunicar con Persona Ejemplo? Sí.', 'Me confirmaron que mi crédito ya fue cancelado.'),
    ('¿Me puede comunicar con Persona Ejemplo? Sí.', 'Yo iba a pagar ayer, pero no recibí el dinero.'),
    ('¿Me puede comunicar con Persona Ejemplo? Sí.', 'No sé por qué me están cobrando esa tarjeta.'),
    ('¿Me puede comunicar con Persona Ejemplo? Sí.', 'Yo no les debo nada.'),
    ('¿Me puede comunicar con Persona Ejemplo? Sí.', 'Yo estoy pagando la tarjeta por mensualidades.'),
    ('¿Cuál es el señor Persona Ejemplo? Sí, de parte de quién.', 'Yo ya pagué esa tarjeta.'),
    ('Encuentre el señor Persona Ejemplo. Sí, él habla.', ''),
    ('Tengo el gusto con... Persona Ejemplo. Sí, dígame.', ''),
    ('Tengo el gusto con... Persona Ejemplo. Sí.', 'Mi tarjeta está al corriente.'),
])
def test_nominal_context_and_own_financial_declaration_are_kept(question,response):
    assert holder_confirmation(question+' Habla MRS sobre su tarjeta. '+response)['confirmed']


@pytest.mark.parametrize('response',[
    'Soy su esposa. Me dijeron que mi cuenta está cancelada.',
    'Si yo tuviera mi cuenta, le diría.',
    'El cliente dice que mi crédito está cancelado.',
    'Diga que mi cuenta está cancelada.',
    'Gestor: Mi crédito está cancelado.',
    '¿Me están cobrando esa tarjeta?',
    'Yo estoy pagando por mi hermano.',
    'No se encuentra. Yo estoy pagando una tarjeta.',
    'No es mi cuenta. Yo iba a pagar por él.',
])
def test_new_identity_phrases_do_not_overrule_other_person_quotes_or_questions(response):
    assert not holder_confirmation('¿Me puede comunicar con Persona Ejemplo? Sí. '
                                   'Habla MRS sobre su tarjeta. '+response)['confirmed']


def test_a_question_about_a_staff_function_is_not_a_nominal_holder_request():
    assert not holder_confirmation('¿Cuál es el señor que me puede atender? Sí. '
                                   'Habla MRS. Ya pagué mi crédito.')['confirmed']
