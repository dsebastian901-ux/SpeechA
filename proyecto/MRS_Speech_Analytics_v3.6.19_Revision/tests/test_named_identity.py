"""Aperturas explícitas; nunca deducir identidad solo del estatus de Excel."""
import pytest

from app.services.conversation_evidence import holder_confirmation
from app.services.analytics_service import AnalyticsService as A


@pytest.mark.parametrize("opening", [
    "¿Tengo el gusto con Persona de Ejemplo? Sí.",
    "Tengo el gusto de hablar con Persona de Ejemplo. Sí, dígame.",
    "Hola, me comunico con Persona de Ejemplo. Ah, sí, dígame.",
    "Buen día con la señorita Persona de Ejemplo. Sí, díganme.",
    "Buenas tardes, con Persona de Ejemplo. Así es.",
    "¿Me puede comunicar de favor con Persona de Ejemplo? Ella habla.",
    "¿Me puede comunicar con Persona de Ejemplo? ¿De dónde habla? De MRS, para la titular. Sí, ella habla.",
    "Tengo el gusto con Persona de Ejemplo. Sí. ¿Qué tal? Me comunico de MRS.",
    "Buenas tardes. ¿Con la señorita Persona de Ejemplo? Sí, dígame.",
    "¿Con Persona de Ejemplo? Así es.",
])
def test_named_identity_with_affirmative_answer_is_holder(opening):
    evidence = holder_confirmation(opening)
    assert evidence["confirmed"] and evidence["evidence"]
    assert A.calculate_basic_compliance(opening)["contact_type"] == "TITULAR"


@pytest.mark.parametrize("answer", [
    "No, no la conozco.", "Sí, pero no está aquí.", "Sí, soy su esposa.",
    "Sí, espere, se lo comunico.", "Sí, lo busco.", "No soy esa persona.",
    "¿De dónde habla?", "Sí, pero soy su madre.",
])
def test_intermediary_or_unanswered_question_does_not_confirm_holder(answer):
    assert not holder_confirmation("¿Tengo el gusto con Persona de Ejemplo? "+answer)["confirmed"]


@pytest.mark.parametrize("question", [
    "¿Tengo el gusto con su esposa?", "¿Me comunico con el banco?", "¿Hablo con cobranza?",
    "¿Tengo el gusto con un familiar?", "¿Me comunico con ustedes?",
    "¿Con la tarjeta?", "¿Con el pago de hoy?",
])
@pytest.mark.parametrize("answer", ["Sí.", "Sí, dígame."])
def test_question_about_relative_or_organization_is_not_holder(question, answer):
    assert not holder_confirmation(question+" "+answer)["confirmed"]


def test_agent_answering_own_question_is_not_holder():
    assert not holder_confirmation("Gestor: ¿Tengo el gusto con Persona de Ejemplo? Sí.")["confirmed"]


def test_explicit_third_party_role_does_not_become_holder():
    text = "¿Tengo el gusto con Persona de Ejemplo? Sí."
    segments = [{"texto":text,"inicio":0,"fin":4,"speaker_role":"TERCERO"}]
    assert not holder_confirmation(text,segments)["confirmed"]


def test_delayed_identity_does_not_skip_a_negative_response():
    text = "¿Me comunica con Persona de Ejemplo? No soy esa persona. De MRS. Sí, ella habla."
    assert not holder_confirmation(text)["confirmed"]


def test_request_to_put_someone_on_the_phone_is_not_satisfied_by_bare_yes():
    assert not holder_confirmation("¿Me puede comunicar con Persona de Ejemplo? Sí.")["confirmed"]
