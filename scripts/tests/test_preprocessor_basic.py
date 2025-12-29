"""Tests for `BasicPreprocessor` ensuring contract compliance."""
from __future__ import annotations

import pytest

from ipa_core.errors import ValidationError
from ipa_core.preprocessor_basic import BasicPreprocessor


def _build_audio(**overrides: object) -> dict[str, object]:
    """Helper to create minimal AudioInput dictionaries for tests."""
    audio: dict[str, object] = {"path": "tests/fixtures/sample.wav", "sample_rate": 16000, "channels": 1}
    audio.update(overrides)
    return audio


@pytest.mark.asyncio
async def test_process_audio_returns_valid_result() -> None:
    pre = BasicPreprocessor()
    audio = _build_audio()

    res = await pre.process_audio(audio) # type: ignore

    assert res["audio"] == audio
    assert res["meta"]["audio_valid"] is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("path", ""),
        ("sample_rate", 0),
        ("sample_rate", "16000"),
        ("channels", 0),
        ("channels", "1"),
    ],
)
@pytest.mark.asyncio
async def test_process_audio_rejects_invalid_types_or_values(field: str, value: object) -> None:
    pre = BasicPreprocessor()
    audio = _build_audio(**{field: value})

    with pytest.raises(ValidationError):
        await pre.process_audio(audio)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_process_audio_requires_all_keys() -> None:
    pre = BasicPreprocessor()
    audio = _build_audio()
    audio.pop("path")

    with pytest.raises(ValidationError):
        await pre.process_audio(audio)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_normalize_tokens_strips_lowercases_and_filters_empty() -> None:
    pre = BasicPreprocessor()

    res = await pre.normalize_tokens([" A ", "b", "  ", "C"])

    assert res["tokens"] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_normalize_tokens_is_idempotent() -> None:
    pre = BasicPreprocessor()
    tokens = ["a", "b", "c"]

    res1 = await pre.normalize_tokens([" A ", " b", "c "])
    first_pass = res1["tokens"]
    res2 = await pre.normalize_tokens(first_pass)
    second_pass = res2["tokens"]

    assert first_pass == second_pass == tokens