"""Tests para `TranscriptionService`."""
from __future__ import annotations

import pytest
from ipa_core.errors import NotReadyError
from ipa_core.services.transcription import TranscriptionService
from tests.utils.audio import write_sine_wave



@pytest.mark.asyncio
async def test_transcribe_file_with_stub(monkeypatch, tmp_path):
    monkeypatch.setenv("PRONUNCIAPA_ASR", "stub")
    wav_path = write_sine_wave(tmp_path / "service.wav")

    service = TranscriptionService(default_lang="es")
    payload = await service.transcribe_file(wav_path)

    assert payload.tokens == ["h", "o", "l", "a"]


@pytest.mark.asyncio
async def test_transcription_service_falls_back_to_espeak_when_epitran_missing(monkeypatch, tmp_path):
    wav_path = write_sine_wave(tmp_path / "service-espeak.wav")

    class RaisingEpitran:
        def __init__(self, *args, **kwargs) -> None:
            raise NotReadyError("epitran unavailable")

    class FakeEspeak:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def to_ipa(self, text: str, *, lang: str, **kw):
            return {"tokens": ["f", "a", "k", "e"]} # Must return dict, not list

    import ipa_core.textref.epitran as epitran_module
    import ipa_core.textref.espeak as espeak_module

    monkeypatch.setattr(epitran_module, "EpitranTextRef", RaisingEpitran)
    monkeypatch.setattr(espeak_module, "EspeakTextRef", FakeEspeak)

    class RawOnlyASR:
        async def setup(self): pass
        async def transcribe(self, audio, *, lang=None, **kw):
            return {"raw_text": "hola"}

    service = TranscriptionService(default_lang="es", asr=RawOnlyASR(), textref_name="epitran")
    payload = await service.transcribe_file(wav_path)

    assert payload.tokens == ["f", "a", "k", "e"]
