"""Tests para `run_pipeline`."""
from __future__ import annotations

import pytest
from ipa_core.errors import ValidationError
from ipa_core.pipeline.runner import run_pipeline

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
