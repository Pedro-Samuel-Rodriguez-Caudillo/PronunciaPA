"""Tests del CLI de transcripción."""
from __future__ import annotations

import pytest

from ipa_core.interfaces.cli import cli_transcribe
from tests.utils.audio import write_sine_wave


def test_cli_transcribe_stub(monkeypatch, tmp_path):
    monkeypatch.setenv("PRONUNCIAPA_ASR", "stub")
    wav_path = write_sine_wave(tmp_path / "clip.wav")

    tokens = cli_transcribe(wav_path, lang="es")

    assert tokens == ["h", "o", "l", "a"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__]))
