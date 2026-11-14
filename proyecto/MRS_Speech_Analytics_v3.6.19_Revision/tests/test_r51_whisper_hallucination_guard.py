"""Regression tests for targeted Whisper hallucination cleanup."""
from app.services.asr_postprocess import sanitize_asr_segments


def test_repeating_hola_after_call_is_collapsed():
    segments = [{'id': i+1, 'inicio': 73.56+i, 'fin': 74.56+i, 'texto': 'Hola.'}
                for i in range(20)]
    cleaned, diagnostic = sanitize_asr_segments(segments, 80.0)
    assert len(cleaned) == 2
    assert diagnostic['segments_removed'] == 18
    assert diagnostic['timestamp_warning']
    assert 'BUCLE_ASR_TERMINAL' in diagnostic['reasons']


def test_video_outro_after_call_is_removed():
    segments = [{'id': 1, 'inicio': 58.51, 'fin': 59.51, 'texto': 'No lo escucho'},
                {'id': 2, 'inicio': 59.51, 'fin': 61.51, 'texto': '¡Suscríbete!'}]
    cleaned, diagnostic = sanitize_asr_segments(segments, 59.66)
    assert len(cleaned) == 1
    assert cleaned[-1]['texto'] == 'No lo escucho'
    assert diagnostic['reasons'] == ['CIERRE_AJENO_AL_AUDIO']


def test_confrontational_closing_is_not_deleted_despite_bad_timestamps():
    segments = [{'inicio': 104.15, 'fin': 105.99, 'texto': 'y el que debe es usted'},
                {'inicio': 105.99, 'fin': 107.59, 'texto': 'el que quedó mal es usted no'},
                {'inicio': 107.59, 'fin': 107.99, 'texto': 'nosotros'}]
    cleaned, diagnostic = sanitize_asr_segments(segments, 105.92)
    assert cleaned == segments
    assert diagnostic['timestamp_warning']
    assert not diagnostic['changed']


def test_real_monetary_dialogue_is_not_modified():
    segments = [{'inicio': i, 'fin': i+1, 'texto': 'El mínimo son 3000 pesos'}
                for i in range(7)]
    segments.append({'inicio': 8, 'fin': 9, 'texto': 'Muy bien, gracias'})
    cleaned, diagnostic = sanitize_asr_segments(segments, 90.0)
    assert cleaned == segments
    assert not diagnostic['changed']


def test_isolated_subscription_word_not_filtered_without_audio_overrun():
    segments = [{'inicio': 1, 'fin': 2, 'texto': '¡Suscríbete!'}]
    cleaned, diagnostic = sanitize_asr_segments(segments, 50.0)
    assert cleaned == segments
    assert not diagnostic['changed']
