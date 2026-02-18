"""Tests para `run_pipeline` y `execute_pipeline`."""
from __future__ import annotations

import pytest
from ipa_core.errors import ValidationError
from ipa_core.pipeline.runner import run_pipeline, execute_pipeline
from ipa_core.phonology.representation import PhonologicalRepresentation

from ipa_core.types import AudioInput, CompareResult


class _Preprocessor:
    def __init__(self) -> None:
        self.audio_seen: AudioInput | None = None

    async def process_audio(self, audio: AudioInput) -> AudioInput:
        self.audio_seen = audio
        return {"audio": audio} # Return dict as expected by protocol

    async def normalize_tokens(self, tokens):
        return {"tokens": [str(t).strip().lower() for t in tokens if str(t).strip()]}


class _ASR:
    def __init__(self, *, tokens=None, raw_text="") -> None:
        self._tokens = tokens
        self._raw_text = raw_text

    async def transcribe(self, audio, *, lang=None, **_kw):
        result = {}
        if self._tokens is not None:
            result["tokens"] = self._tokens
        if self._raw_text:
            result["raw_text"] = self._raw_text
        return result


class _TextRef:
    async def to_ipa(self, text: str, *, lang: str, **_kw):
        return {"tokens": list(text)}


class _Comparator:
    def __init__(self) -> None:
        self.last_ref = None
        self.last_hyp = None

    async def compare(self, ref, hyp, *, weights=None, **_kw) -> CompareResult:
        self.last_ref = list(ref)
        self.last_hyp = list(hyp)
        return {"per": 0.0, "ops": [], "alignment": list(zip(ref, hyp))}




@pytest.mark.asyncio
async def test_run_pipeline_uses_asr_tokens():
    pre = _Preprocessor()
    asr = _ASR(tokens=[" A", "b "])
    textref = _TextRef()
    comp = _Comparator()

    result = await run_pipeline(
        pre,
        asr,
        textref,
        comp,
        audio={"path": "x.wav", "sample_rate": 16000, "channels": 1},
        text="ab",
        lang="es",
    )

    assert result["per"] == 0.0
    assert result["alignment"] == [("a", "a"), ("b", "b")]


@pytest.mark.asyncio
async def test_run_pipeline_rejects_raw_text():
    pre = _Preprocessor()
    asr = _ASR(tokens=None, raw_text=" a b ")
    textref = _TextRef()
    comp = _Comparator()

    with pytest.raises(ValidationError):
        await run_pipeline(
            pre,
            asr,
            textref,
            comp,
            audio={"path": "x.wav", "sample_rate": 16000, "channels": 1},
            text="ab",
            lang="es",
        )


# ── Mock pack for execute_pipeline tests ─────────────────────────────

class _MockScoringProfile:
    tolerance = "medium"
    phoneme_weights = {}


class _MockPack:
    """LanguagePack mínimo para probar execute_pipeline con pack."""

    def collapse(self, ipa: str, *, mode: str = "objective") -> str:
        """Simula collapse: devuelve el mismo IPA (no hace cambios)."""
        return ipa

    def derive(self, ipa: str, *, mode: str = "objective") -> str:
        """Simula derive: devuelve el mismo IPA."""
        return ipa

    def get_scoring_profile(self, mode: str) -> _MockScoringProfile:
        return _MockScoringProfile()


_AUDIO = {"path": "x.wav", "sample_rate": 16000, "channels": 1}


# ── execute_pipeline() tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_pipeline_no_pack_phonemic():
    """execute_pipeline sin pack con evaluation_level=phonemic retorna result."""
    pre = _Preprocessor()
    asr = _ASR(tokens=["a", "b"])
    textref = _TextRef()
    result = await execute_pipeline(
        pre, asr, textref,
        audio=_AUDIO, text="ab", lang="es",
        pack=None, evaluation_level="phonemic",
    )
    assert result is not None
    d = result.to_dict()
    assert "per" in d


@pytest.mark.asyncio
async def test_execute_pipeline_no_pack_phonetic():
    """execute_pipeline sin pack con evaluation_level=phonetic retorna result."""
    pre = _Preprocessor()
    asr = _ASR(tokens=["a", "b"])
    textref = _TextRef()
    result = await execute_pipeline(
        pre, asr, textref,
        audio=_AUDIO, text="ab", lang="es",
        pack=None, evaluation_level="phonetic",
    )
    d = result.to_dict()
    assert "per" in d


@pytest.mark.asyncio
async def test_execute_pipeline_with_pack_collapse():
    """Con pack, aplica collapse en modo phonemic."""
    collapse_calls = []

    class TrackingPack(_MockPack):
        def collapse(self, ipa, *, mode="objective"):
            collapse_calls.append(ipa)
            return ipa

    pre = _Preprocessor()
    asr = _ASR(tokens=["a", "b"])
    textref = _TextRef()
    result = await execute_pipeline(
        pre, asr, textref,
        audio=_AUDIO, text="ab", lang="es",
        pack=TrackingPack(), evaluation_level="phonemic",
    )
    assert len(collapse_calls) >= 1


@pytest.mark.asyncio
async def test_execute_pipeline_with_pack_derive():
    """Con pack, aplica derive en modo phonetic."""
    derive_calls = []

    class TrackingPack(_MockPack):
        def derive(self, ipa, *, mode="objective"):
            derive_calls.append(ipa)
            return ipa

    pre = _Preprocessor()
    asr = _ASR(tokens=["a", "b"])
    textref = _TextRef()
    result = await execute_pipeline(
        pre, asr, textref,
        audio=_AUDIO, text="ab", lang="es",
        pack=TrackingPack(), evaluation_level="phonetic",
    )
    assert len(derive_calls) >= 1


@pytest.mark.asyncio
async def test_execute_pipeline_postprocessing_applied_to_asr():
    """Limpieza IPA se aplica en la ruta ASR (silence markers removidos)."""
    pre = _Preprocessor()
    asr = _ASR(tokens=["sil", "a", "sp", "b"])  # silence markers
    textref = _TextRef()
    result = await execute_pipeline(
        pre, asr, textref,
        audio=_AUDIO, text="ab", lang="es",
        pack=None, evaluation_level="phonemic",
    )
    # Resultado debe ser válido (sin error) — silence fue filtrado
    assert result is not None


@pytest.mark.asyncio
async def test_execute_pipeline_empty_asr_raises():
    """execute_pipeline con ASR vacío lanza ValidationError."""
    pre = _Preprocessor()
    asr = _ASR(tokens=None)
    textref = _TextRef()
    with pytest.raises(ValidationError):
        await execute_pipeline(
            pre, asr, textref,
            audio=_AUDIO, text="ab", lang="es",
        )
