from copy import deepcopy
import math

import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.call_wait_evidence import assess_call_wait
from app.services.batch_report_service import BatchReportService as B


PAID = 'Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe comprobante por WhatsApp.'
RELATION = {'estatus_grabacion': 'CONVENIO', 'pago_minimo': '700'}


def analyze(text, segments=(), duration=180):
    return A.analyze_transcription(TranscriptionModel.from_dict({
        'archivo': 'sample.wav', 'texto': text, 'segmentos': list(segments),
        'duracion_segundos': duration}), RELATION)


@pytest.mark.parametrize('complaint', [
    'En la llamada anterior me atendieron de mala manera.',
    'La vez pasada recibí una mala atención.',
    'Su compañera fue muy agresiva.',
    'La persona que me llamó fue prepotente.',
    'Su gestor me estuvo gritando.',
    'La asesora que me atendió fue déspota.',
    'Ayer me humillaron.',
    'En la llamada pasada hubo agresiones.',
    'Su compañero se burló de mí.',
    'Me hablaron de forma grosera.',
    'Me atienden mal.',
    'Me trataron con malos modos.',
    'En la llamada anterior me faltó al respeto.',
    'Me quejo del mal servicio en la llamada anterior.',
    'Familiar: La vez pasada recibí una mala atención.',
    'En la llamada anterior. Recibí mala atención.',
    'Su compañera tuvo una actitud agresiva.',
    'Sí, me atendieron mal.',
    'Si, me atendieron mal.',
    'Sí me atendieron mal y quiero quejarme.',
    'Sí me atendieron mal, ¿puedo quejarme?',
    'Su compañera nos estuvo gritando.',
    'En la llamada anterior a mi esposa la trataron mal.',
    'En la llamada anterior fueron muy agresivos.',
    'Me atendieron pésimamente.',
])
def test_bad_attention_complaint_blocks_approval_above_80(complaint):
    result = analyze(PAID + ' ' + complaint)
    m = result.metadata
    assert result.compliance_score >= 80
    assert m['quality_checks']['queja_maltrato_detectada']
    assert m['treatment_validation']['mistreatment_report_evidence']
    assert m['final_result'] == 'NO_APROBADO'
    assert m['shared_classification']['clasificacion'] == 'NO_APROBADO'
    assert not m['shared_classification']['aprobado']
    assert not m['critical_failures'], 'Denuncia previa no prueba falta grave del gestor actual'


@pytest.mark.parametrize('statement', [
    'No me atendieron mal.', 'Nunca me humillaron.',
    'No es cierto que me atendieron mal.',
    'No dije que me atendieron mal.',
    'En la llamada anterior no hubo mala atención.',
    'La llamada anterior fue sin agresiones.',
    'Si me atendieron mal, puedo quejarme.',
    'Si me humillaron, podría quejarme.',
    'Gestor: ¿Me atendieron mal?',
    'Gestor: Si hubo mala atención en la llamada anterior puede quejarse.',
    'Gestor: Le atendieron de mala manera.',
    'Mi vecino me insultó.',
    'Mis compañeros de trabajo me atendieron mal.',
    'La vez pasada me atendieron muy bien.',
    '¿Me atendieron mal?',
])
def test_no_complaint_from_negation_hypothesis_other_context_or_agent(statement):
    assert not analyze(PAID + ' ' + statement).metadata['quality_checks']['queja_maltrato_detectada']


def segments_for_gap(seconds):
    return [
        {'inicio': 0, 'fin': 20, 'texto': PAID},
        {'inicio': 20, 'fin': 25, 'texto': 'Un momento, permítame revisar.', 'speaker_role': 'GESTOR'},
        {'inicio': 25 + seconds, 'fin': 35 + seconds,
         'texto': 'Gracias por esperar. Hasta luego.', 'speaker_role': 'GESTOR'},
    ]


@pytest.mark.parametrize('gap,blocked', [(64.999, False), (65, True), (65.001, True), (100, True)])
def test_wait_limit_inclusive_for_announced_wait_with_later_return(gap, blocked):
    segments = segments_for_gap(gap)
    text = ' '.join(s['texto'] for s in segments)
    original = deepcopy(segments)
    result = analyze(text, segments, duration=35 + gap)
    m = result.metadata
    assert result.compliance_score >= 80
    assert m['wait_validation']['threshold_seconds'] == 65
    assert m['wait_validation']['review_required'] == blocked
    assert ('PEN_ESPERA_PROLONGADA' in {p['id'] for p in m['penalties']}) == blocked
    assert m['shared_classification']['clasificacion'] == ('REVISAR' if blocked else 'APROBADO')
    assert not m['critical_failures']
    assert segments == original


def test_terminal_unreturned_wait_blocks_with_no_interlocutor_prompt():
    segments = segments_for_gap(65)[:2]
    result = analyze(' '.join(s['texto'] for s in segments), segments, 90)
    waiting = result.metadata['wait_validation']
    assert waiting['review_required']
    assert waiting['max_no_conversation_seconds'] == 65
    assert waiting['intervals'][0]['start'] == 25
    assert waiting['intervals'][0]['end'] == 90
    assert result.metadata['shared_classification']['clasificacion'] == 'REVISAR'


def test_long_internal_gap_without_announced_wait_also_blocks():
    segments = [{'inicio': 0, 'fin': 10, 'texto': 'Soy yo.'},
                {'inicio': 75, 'fin': 80, 'texto': 'Aquí sigo.'}]
    assert assess_call_wait('Soy yo. Aquí sigo.', segments, 80)['review_required']


def test_decimal_asr_timestamps_do_not_miss_exactly_65_seconds():
    units = [{'inicio': 60, 'fin': 63.003, 'texto': 'Un momento.'},
             {'inicio': 128.003, 'fin': 130, 'texto': 'Hasta luego.'}]
    result = assess_call_wait('Un momento. Hasta luego.', units, 130)
    assert result['review_required']
    assert result['intervals'][0]['seconds'] == 65


def test_money_display_normalization_does_not_discard_original_spoken_segment():
    from app.services.transcription_services import TranscriptionService
    original = 'Ya pagué 3.100 pesos.'
    text = 'Habla MRS. Soy yo. ' + original + ' Hasta luego.'
    units = [{'inicio': 0, 'fin': 5, 'texto': 'Habla MRS. Soy yo.'},
             {'inicio': 5, 'fin': 100, 'texto': original},
             {'inicio': 100, 'fin': 105, 'texto': 'Hasta luego.'}]
    model = TranscriptionModel.from_dict({'archivo': 'sample.wav', 'texto': text,
        'segmentos': units, 'duracion_segundos': 110})
    model.text = TranscriptionService._normalize_asr_money_display(model.text)
    assert model.text != text
    result = A.analyze_transcription(model, RELATION).metadata['wait_validation']
    assert result['usable_segments'] == 3
    assert result['invalid_segments'] == 0
    assert not result['review_required'], 'Una corrección visual de importe no es silencio'


@pytest.mark.parametrize('known_role', [True, False])
def test_customer_prompts_do_not_reset_an_announced_wait(known_role):
    units = [{'start': 0, 'end': 5, 'text': 'Un momento.', 'speaker_role': 'GESTOR'}]
    for time in [20, 40, 60]:
        units.append({'start': time, 'end': time + 1, 'text': '¿Bueno? ¿Me escucha?',
                      'speaker_role': 'TITULAR' if known_role else 'SPEAKER_01'})
    units.append({'start': 80, 'end': 85, 'text': 'Gracias por esperar.', 'speaker_role': 'GESTOR'})
    result = assess_call_wait(' '.join(u['text'] for u in units), units, 85)
    assert result['review_required']
    assert any(e['start'] == 5 and e['end'] == 80 for e in result['intervals'])


def test_agent_checkin_restarts_wait_before_limit():
    units = [{'start': 0, 'end': 5, 'text': 'Un momento.', 'speaker_role': 'GESTOR'},
             {'start': 60, 'end': 65, 'text': 'Sigo con usted, un momento.', 'speaker_role': 'GESTOR'},
             {'start': 120, 'end': 125, 'text': 'Gracias por esperar.', 'speaker_role': 'GESTOR'}]
    result = assess_call_wait(' '.join(u['text'] for u in units), units, 125)
    assert not result['review_required']
    assert result['max_no_conversation_seconds'] == 55


def test_initial_preroll_and_recording_tail_after_goodbye_are_not_wait():
    units = [{'start': 90, 'end': 100, 'text': 'Habla MRS.'},
             {'start': 100, 'end': 105, 'text': 'Gracias por su tiempo. Hasta luego.'}]
    assert not assess_call_wait(' '.join(u['text'] for u in units), units, 200)['review_required']


@pytest.mark.parametrize('closing', ['Buen día.', 'Buena tarde.', 'Que tenga excelente tarde.',
                                     'Que tenga una bonita noche.'])
def test_normal_farewell_does_not_make_recording_tail_a_failed_wait(closing):
    units = [{'start': 0, 'end': 50, 'text': PAID}, {'start': 50, 'end': 55, 'text': closing}]
    assert not assess_call_wait(PAID + ' ' + closing, units, 200)['review_required']


def test_greeting_alone_does_not_disguise_unanswered_call_as_normal_closure():
    assert assess_call_wait('Buen día.', [{'text': 'Buen día.', 'start': 0, 'end': 5}], 100)['review_required']


def test_nonverbal_music_does_not_count_as_resumed_conversation():
    units = [{'start': 0, 'end': 5, 'text': 'Un momento.'},
             {'start': 20, 'end': 70, 'text': '[Música]'},
             {'start': 70, 'end': 75, 'text': 'Gracias por esperar.'}]
    assert assess_call_wait(' '.join(u['text'] for u in units), units, 75)['review_required']


def test_overlapping_and_unsorted_segments_do_not_invent_wait():
    units = [{'start': 80, 'end': 90, 'text': 'Texto dos.'},
             {'start': 0, 'end': 100, 'text': 'Texto uno.'},
             {'start': 100, 'end': 105, 'text': 'Hasta luego.'}]
    assert not assess_call_wait('Texto uno. Texto dos. Hasta luego.', units, 105)['review_required']


@pytest.mark.parametrize('bad', [-1, 'not a number', math.nan, math.inf, True])
def test_invalid_times_never_become_a_fabricated_gap(bad):
    result = assess_call_wait('Hola.', [{'text': 'Hola.', 'start': bad, 'end': 10}], 200)
    assert not result['review_required']
    assert result['max_no_conversation_seconds'] is None
    assert result['result'].startswith('NO EVALUABLE')


def test_foreign_segment_and_missing_times_are_not_acoustic_evidence():
    assert not assess_call_wait('Hola.', [{'text': 'Other text.', 'start': 0, 'end': 5}], 200)['review_required']
    assert assess_call_wait('Hola.', [], 200)['result'].startswith('NO EVALUABLE')


def test_complete_word_times_detect_gap_inside_one_long_segment():
    unit = {'inicio': 0, 'fin': 100, 'texto': 'Hola. Hasta luego.', 'palabras': [
        {'palabra': 'Hola.', 'inicio': 0, 'fin': 2},
        {'palabra': 'Hasta', 'inicio': 80, 'fin': 90},
        {'palabra': 'luego.', 'inicio': 90, 'fin': 100}]}
    result = assess_call_wait(unit['texto'], [unit], 100)
    assert result['review_required']
    assert result['intervals'][0]['seconds'] == 78
    unit['palabras'].pop()
    assert not assess_call_wait(unit['texto'], [unit], 100)['review_required'], 'No usar palabras parciales como si cubrieran todo el texto'


@pytest.mark.parametrize('blocker', [
    {'wait_validation': {'review_required': True}},
    {'quality_checks': {'espera_prolongada_detectada': True}},
    {'treatment_validation': {'mistreatment_report_evidence': [{'text': 'mala atención'}]}},
])
@pytest.mark.parametrize('score', [80, 81, 100])
def test_shared_gate_blocks_all_approval_routes_including_hostility_exception(blocker, score):
    flags = {k: True for k in ['audio_verified', 'interlocutor_hostile_or_lascivious', 'prevented_script', 'agent_professional']}
    metadata = dict(blocker, hostile_interlocutor_exception=flags)
    for base in [None, {'estatus_autorizado': False}, {'estatus_autorizado': True, 'tiene_nombre_final': True}]:
        decision = A.shared_quality_decision(metadata, score, duration_seconds=120, base_classification=base)
        assert decision['clasificacion'] == 'REVISAR'
        assert not decision['aprobado']


def test_report_exposes_complaint_and_wait_windows_without_changing_existing_tail():
    units = segments_for_gap(65)
    text = ' '.join(u['texto'] for u in units) + ' En la llamada anterior me atendieron mal.'
    result = analyze(text, units, 100)
    row = B._row_from_item({'analytics_metadata': result.metadata})
    assert row['Queja de atención/maltrato'] == 'SI'
    assert 'me atendieron mal' in row['Evidencia queja atención/maltrato'].lower()
    assert row['Validación espera 65 s'].startswith('REVISAR')
    assert '25.00–90.00' in row['Intervalos espera 65 s']
    for headers in (B.HEADERS, B.MODE_B_HEADERS):
        assert headers[-5:] == B.ARCO_HEADERS
        assert len(headers) == len(set(headers))


@pytest.mark.parametrize('category', ['APROBADO', 'APROBADO_SIN_ETIQUETAR', 'APROBADO_CON_EXCEPCION'])
def test_regression_invariant_detects_wait_and_prior_complaint_in_every_approved_category(category):
    from tools.regression_checkpoints import invariants
    for blocker in [{'wait_validation': {'review_required': True}},
                    {'treatment_validation': {'mistreatment_report_evidence': [{'text': 'mala atención'}]}}]:
        m = {'final_result': category, **blocker}
        assert invariants({'metadata': m, 'shared_decision': {'aprobado': False}})
