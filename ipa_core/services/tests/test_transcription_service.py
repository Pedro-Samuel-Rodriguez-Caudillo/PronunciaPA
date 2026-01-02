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

    from ipa_core.plugins import registry

    def mock_resolve(category, name, params=None):
        if category == "textref":
            if name == "epitran":
                raise NotReadyError("epitran unavailable")
            if name == "espeak":
                class FakeEspeak:
                    async def setup(self): pass
                    async def teardown(self): pass
                    async def to_ipa(self, text: str, *, lang: str, **kw):      
                        return {"tokens": ["f", "a", "k", "e"]}
                return FakeEspeak()
        return registry.resolve(category, name, params)

    monkeypatch.setattr(registry, "resolve", mock_resolve)

    class TokenASR:
        async def setup(self): pass
        async def teardown(self): pass
        async def transcribe(self, audio, *, lang=None, **kw):
            return {"tokens": ["h", "o", "l", "a"]}

    service = TranscriptionService(default_lang="es", asr=TokenASR(), textref_name="epitran")
    assert service.textref.__class__.__name__ == "FakeEspeak"
    payload = await service.transcribe_file(wav_path)

    assert payload.tokens == ["h", "o", "l", "a"]
