"""Tests para `TranscriptionService`."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock
from ipa_core.audio.markers import is_audio_preprocessed
from ipa_core.errors import NotReadyError
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.services.transcription import TranscriptionService
from tests.utils.audio import write_sine_wave



@pytest.mark.asyncio
async def test_transcribe_file_with_stub(monkeypatch, tmp_path):
    monkeypatch.setenv("PRONUNCIAPA_ASR", "stub")
    wav_path = write_sine_wave(tmp_path / "service.wav")

    service = TranscriptionService(default_lang="es")
    payload = await service.transcribe_file(wav_path)

    # StubASR devuelve tokens deterministas pero no predecibles desde fuera;
    # lo que importa es que el pipeline retorna una lista de strings no vacía.
    assert isinstance(payload.tokens, list)
    assert len(payload.tokens) > 0
    assert all(isinstance(t, str) for t in payload.tokens)


@pytest.mark.asyncio
async def test_transcription_service_falls_back_when_epitran_missing(monkeypatch, tmp_path):
    """Cuando epitran no está disponible, TranscriptionService usa el fallback
    del registry (grapheme u otro disponible) sin lanzar excepción."""
    wav_path = write_sine_wave(tmp_path / "service-espeak.wav")

    from ipa_core.plugins import registry

    # Capturar original ANTES del monkeypatch para evitar recursión infinita
    _original_resolve = registry.resolve

    def mock_resolve(category, name, params=None, **kwargs):
        if category == "textref" and name == "epitran":
            raise NotReadyError("epitran unavailable")
        return _original_resolve(category, name, params, **kwargs)

    monkeypatch.setattr(registry, "resolve", mock_resolve)

    from ipa_core.ports.asr import ASRBackend

    class TokenASR(ASRBackend):
        output_type = "ipa"
        async def setup(self): pass
        async def teardown(self): pass
        async def transcribe(self, audio, *, lang=None, **kw):
            return {"tokens": ["m", "a", "l"]}

    # El servicio debe inicializarse aunque epitran falle (usa fallback del registry)
    service = TranscriptionService(default_lang="es", asr=TokenASR(), textref_name="epitran")
    payload = await service.transcribe_file(wav_path)

    # El pipeline funciona y retorna tokens válidos
    assert isinstance(payload.tokens, list)
    assert len(payload.tokens) > 0


@pytest.mark.asyncio
async def test_transcription_service_rejects_raw_text_without_ipa_tokens(tmp_path):
    wav_path = write_sine_wave(tmp_path / "service-raw.wav")

    from ipa_core.ports.asr import ASRBackend
    from ipa_core.ports.textref import TextRefProvider
    from ipa_core.errors import ValidationError

    class RawTextASR(ASRBackend):
        async def setup(self): pass
        async def teardown(self): pass
        async def transcribe(self, audio, *, lang=None, **kw):
            return {"raw_text": "hola"}

    class FakeTextRef(TextRefProvider):
        async def setup(self): pass
        async def teardown(self): pass
        async def to_ipa(self, text: str, *, lang: str, **kw):
            return {"tokens": ["h", "o", "l", "a"]}

    service = TranscriptionService(default_lang="es", asr=RawTextASR(), textref=FakeTextRef())
    with pytest.raises(ValidationError):
        await service.transcribe_file(wav_path)


@pytest.mark.asyncio
async def test_transcription_service_marks_audio_as_already_wav(tmp_path):
    wav_path = write_sine_wave(tmp_path / "service-pre.wav")

    from ipa_core.ports.asr import ASRBackend

    class TokenASR(ASRBackend):
        async def setup(self): pass
        async def teardown(self): pass
        async def transcribe(self, audio, *, lang=None, **kw):
            return {"tokens": ["m", "a", "l"]}

    pre = BasicPreprocessor()
    pre.process_audio = AsyncMock(return_value={
        "audio": {"path": wav_path, "sample_rate": 16000, "channels": 1},
        "meta": {},
    })

    service = TranscriptionService(default_lang="es", preprocessor=pre, asr=TokenASR())
    await service.transcribe_file(wav_path)

    called_audio = pre.process_audio.await_args.args[0]
    assert is_audio_preprocessed(called_audio)
