"""Mensaje directo de retorno y recepción humana: hechos separados."""
from copy import deepcopy
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import directed_callback_message
from app.services.recado_acceptance_review import make_recado_confirmation


def analyze(text, *, confirmed=True, segments=None):
    data = {'archivo': 'sample.ogg', 'texto': text, 'segmentos': segments or [], 'duracion_segundos': 120}
    relation = {'estatus_grabacion': 'MENSAJE CON FAMILIAR', 'numero_de_tarjeta': '1234567890123456',
                'asignacion': '1PV'}
    t = TranscriptionModel.from_dict(data)
    if confirmed:
        t.metadata['recado_acceptance_confirmation'] = make_recado_confirmation(data, relation, user_confirmed=True)
    original = deepcopy(data)
    result = A.analyze_transcription(t, relation)
    assert data == original
    return result


TEXT = ('Habla MRS. Es mi hermana. ¿Tendrá dónde anotar el número? '
        'Aquí está, 55, 51, 23, 45, 67. Así es, a ese número que se comunique con nosotros.')


def test_message_and_user_acceptance_resolve_the_recado_without_rewriting_asr():
    a = analyze(TEXT)
    assert a.metadata['final_result'] == 'APROBADO'
    r = a.metadata['status_validation']['recado_evidence']
    assert r['message_transmitted'] and r['confirmed_recado']
    assert r['evidence']['message'][0]['method'] == 'INSTRUCCION_DE_RETORNO_AL_CONTACTO_DADO'
    assert a.compliance_score == 100 and not a.metadata['penalties']


def test_the_instruction_itself_does_not_prove_acceptance():
    assert directed_callback_message(TEXT)
    assert analyze(TEXT, confirmed=False).metadata['final_result'] == 'REVISAR'


@pytest.mark.parametrize('text', [
    'No, a ese número que se comunique con nosotros.',
    'Dice que a ese número que se comunique con nosotros.',
    'Dijeron que a ese número que se comunique con nosotros.',
    'Diga que a ese número que se comunique con nosotros.',
    'Repita: a ese número que se comunique con nosotros.',
    'Si llama, a ese número que se comunique con nosotros.',
    'Cuando se pueda, a ese número que se comunique con nosotros.',
    '¿A ese número que se comunique con nosotros?',
    'Me dijo: «a ese número que se comunique con nosotros».',
    'A ese número que se comunique con nosotros es un ejemplo.',
    'A ese número que se comunique con nosotros, pero no es un mensaje.',
    'A ese número que pague 500 pesos.',
])
def test_quotation_question_hypothesis_negation_and_payment_are_not_delivered_messages(text):
    assert not directed_callback_message('El teléfono es 5551234567. '+text)


@pytest.mark.parametrize('role,expected', [('GESTOR', True), ('NO DETERMINADO', True),
    ('TITULAR', False), ('TERCERO', False), ('INTERLOCUTOR', False)])
def test_known_recipient_roles_cannot_be_used_as_agent_message(role, expected):
    text = 'A ese número que se comunique con nosotros.'
    number = 'El teléfono es 5551234567.'
    evidence = directed_callback_message(number+' '+text, [
        {'text': number, 'speaker_role': 'GESTOR', 'start': 10, 'end': 15},
        {'text': text, 'speaker_role': role, 'start': 20, 'end': 25}])
    assert bool(evidence) is expected
    if evidence:
        assert evidence[0]['start'] == 20 and evidence[0]['end'] == 25


@pytest.mark.parametrize('problem', [
    'No le voy a pasar el recado.', 'No lo conozco.', 'Me trataron mal.',
    'Tiene una deuda de 500 pesos.', 'Gestor: Tiene una deuda de 500 pesos.',
    'La tarjeta termina en 9999.', 'Gestor: Vamos a realizar una visita a su domicilio.',
    'Gestor: Qué poca madre.',
])
def test_direct_callback_does_not_waive_other_rules(problem):
    assert not analyze(TEXT+' '+problem).metadata['shared_classification']['aprobado']


def test_missing_family_is_not_filled_from_the_excel_label():
    assert not analyze(TEXT.replace('Es mi hermana. ', '')).metadata['shared_classification']['aprobado']


def test_human_acceptance_cannot_invent_a_missing_message():
    assert not analyze('Habla MRS. Es mi hermana. ¿Tendrá dónde anotar el número?').metadata['shared_classification']['aprobado']


def test_instruction_without_actual_dictation_cannot_invent_contact():
    assert not analyze('Habla MRS. Es mi hermana. A ese número que se comunique con nosotros.').metadata['shared_classification']['aprobado']


def test_a_number_dictated_by_the_third_party_is_not_agent_contact_information():
    number = 'El teléfono es 5551234567.'
    message = 'A ese número que se comunique con nosotros.'
    assert not directed_callback_message(number+' '+message, [
        {'text': number, 'speaker_role': 'TERCERO'}, {'text': message, 'speaker_role': 'GESTOR'}])
