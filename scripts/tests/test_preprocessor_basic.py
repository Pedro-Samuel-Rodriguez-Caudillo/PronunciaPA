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


def test_process_audio_returns_same_instance() -> None:
    pre = BasicPreprocessor()
    audio = _build_audio()

    processed = pre.process_audio(audio)

    assert processed is audio


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
def test_process_audio_rejects_invalid_types_or_values(field: str, value: object) -> None:
    pre = BasicPreprocessor()
    audio = _build_audio(**{field: value})

    with pytest.raises(ValidationError):
        pre.process_audio(audio)  # type: ignore[arg-type]


def test_process_audio_requires_all_keys() -> None:
    pre = BasicPreprocessor()
    audio = _build_audio()
    audio.pop("path")

    with pytest.raises(ValidationError):
        pre.process_audio(audio)  # type: ignore[arg-type]


def test_normalize_tokens_strips_lowercases_and_filters_empty() -> None:
    pre = BasicPreprocessor()

    tokens = pre.normalize_tokens([" A ", "b", "  ", "C"])

    assert tokens == ["a", "b", "c"]


def test_normalize_tokens_is_idempotent() -> None:
    pre = BasicPreprocessor()
    tokens = ["a", "b", "c"]

    first_pass = pre.normalize_tokens([" A ", " b", "c "])
    second_pass = pre.normalize_tokens(first_pass)

    assert first_pass == second_pass == tokens
