"""Comprobar decodificación real sin presentar un tono como prueba de reconocimiento."""
import math
import struct
import wave

from faster_whisper.audio import decode_audio
from app.services.audio_service import AudioService
from app.services.whisper_service import WhisperService


def test_new_wav_is_discovered_validated_and_decoded(tmp_path):
    path = tmp_path/"synthetic-tone.wav"
    rate = 16000
    samples = [int(8000*math.sin(2*math.pi*440*n/rate)) for n in range(rate)]
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        stream.writeframes(struct.pack("<"+"h"*len(samples), *samples))
    assert AudioService.search_audio_files(tmp_path) == [path]
    WhisperService._validate_audio(path)
    decoded = decode_audio(str(path), sampling_rate=rate)
    assert decoded.shape == (rate,)
    assert abs(decoded).max() > .1
