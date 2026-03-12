from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

import pytest

from ipa_core.errors import ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.pipeline.runner import execute_pipeline, run_pipeline_with_pack
from ipa_core.types import ASRResult, AudioInput, CompareResult, CompareWeights, PreprocessorResult, TextRefResult, TokenSeq


class StubPreprocessor(BasePlugin):
    def __init__(self, quality: Optional[dict[str, Any]] = None, temp_path: Optional[Path] = None) -> None:
        super().__init__()
        self._quality = quality or {"passed": True, "issues": []}
        self._temp_path = temp_path

    async def process_audio(self, audio: AudioInput, **kw: Any) -> PreprocessorResult:
        meta: dict[str, Any] = {"audio_quality": self._quality}
        if self._temp_path is not None:
            meta["ensure_wav"] = {"path": str(self._temp_path)}
        return {"audio": audio, "meta": meta}

    async def normalize_tokens(self, tokens: TokenSeq, **kw: Any) -> PreprocessorResult:
        return {"tokens": list(tokens)}


class StubASR(BasePlugin):
    output_type: Literal["ipa", "text", "none"] = "ipa"

    def __init__(self, tokens: Optional[list[str]]) -> None:
        super().__init__()
        self._tokens = tokens

    async def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw: Any) -> ASRResult:
        return {
            "tokens": self._tokens or [],
            "meta": {"lang": lang, "backend": "stub_asr", "model": "test-double"},
        }


class StubTextRef(BasePlugin):
    def __init__(self, tokens: Optional[list[str]] = None) -> None:
        super().__init__()
        self._tokens = tokens or ["p", "a", "t", "o"]

    async def to_ipa(self, text: str, *, lang: Optional[str] = None, **kw: Any) -> TextRefResult:
        return {"tokens": self._tokens, "meta": {"lang": lang}}


class StubComparator(BasePlugin):
    async def compare(self, ref: TokenSeq, hyp: TokenSeq, *, weights: Optional[CompareWeights] = None, **kw: Any) -> CompareResult:
        return {
            "per": 0.2,
            "ops": [
                {"op": "eq", "ref": "p", "hyp": "p"},
                {"op": "sub", "ref": "t", "hyp": "d"},
            ],
            "alignment": [("p", "p"), ("t", "d")],
            "meta": {"distance": 0.2},
        }


def _audio_input() -> AudioInput:
    return {"path": "sample.wav", "sample_rate": 16000, "channels": 1}


@pytest.mark.unit
@pytest.mark.functional
async def test_execute_pipeline_blocks_on_no_speech_quality_issue() -> None:
    """Contrato caso 1=A: quality gate bloqueante lanza ValidationError con user_feedback."""
    pre = StubPreprocessor(
        quality={
            "passed": False,
            "issues": ["no_speech"],
            "user_feedback": "Sin voz detectable",
            "error_code": "NO_SPEECH",
        }
    )

    with pytest.raises(ValidationError, match="Sin voz detectable"):
        await execute_pipeline(
            pre,
            StubASR(["p", "a"]),
            StubTextRef(["p", "a"]),
            StubComparator(),
            audio=_audio_input(),
            text="pa",
            lang="es",
        )


@pytest.mark.unit
@pytest.mark.functional
async def test_execute_pipeline_raises_when_asr_returns_no_tokens() -> None:
    """Contrato caso 2=A: ASR sin tokens debe lanzar ValidationError explícito."""
    pre = StubPreprocessor(quality={"passed": True, "issues": []})

    with pytest.raises(ValidationError, match="ASR no devolvió tokens IPA"):
        await execute_pipeline(
            pre,
            StubASR([]),
            StubTextRef(["p", "a"]),
            StubComparator(),
            audio=_audio_input(),
            text="pa",
            lang="es",
        )


@pytest.mark.unit
@pytest.mark.functional
async def test_run_pipeline_with_pack_requires_pack() -> None:
    """Contrato caso 3=A: run_pipeline_with_pack exige pack y falla explícitamente."""
    with pytest.raises(ValidationError, match="Language pack requerido para run_pipeline_with_pack"):
        await run_pipeline_with_pack(
            StubPreprocessor(),
            StubASR(["p", "a"]),
            StubTextRef(["p", "a"]),
            audio=_audio_input(),
            text="pa",
            pack=None,
            lang="es",
        )


@pytest.mark.integration
@pytest.mark.functional
async def test_execute_pipeline_uses_custom_comparator_and_scales_score_to_100() -> None:
    """Contrato caso 4=A: en path sin pack se usa comparador custom y score=80.0 para per=0.2."""
    result = await execute_pipeline(
        StubPreprocessor(),
        StubASR(["p", "a", "d", "o"]),
        StubTextRef(["p", "a", "t", "o"]),
        StubComparator(),
        audio=_audio_input(),
        text="pato",
        lang="es",
    )

    assert result.score == 80.0


@pytest.mark.integration
@pytest.mark.reliability
async def test_execute_pipeline_cleans_temp_files_even_when_exception_occurs(tmp_path: Path) -> None:
    """Contrato caso 5=A: cleanup de temporales se ejecuta aunque el pipeline falle."""
    temp_wav = tmp_path / "temp_normalized.wav"
    temp_wav.write_text("temporary", encoding="utf-8")

    pre = StubPreprocessor(
        quality={"passed": True, "issues": []},
        temp_path=temp_wav,
    )

    with pytest.raises(ValidationError):
        await execute_pipeline(
            pre,
            StubASR([]),  # fuerza error después de process_audio, activando finally
            StubTextRef(["p", "a"]),
            StubComparator(),
            audio=_audio_input(),
            text="pa",
            lang="es",
        )

    assert not temp_wav.exists()
