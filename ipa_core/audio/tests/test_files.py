"""Pruebas de utilidades de audio (AAA/FIST)."""
from __future__ import annotations

import os
import wave

import pytest

from ipa_core.audio import files
from ipa_core.errors import UnsupportedFormat


def _write_wav(path) -> str:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 10)
    return str(path)


def test_ensure_wav_returns_same_path_for_wav(tmp_path):
    source = tmp_path / "sample.wav"
    _write_wav(source)

    result, created = files.ensure_wav(str(source))

    assert result == str(source)
    assert created is False


def test_ensure_wav_rejects_unknown_extension(monkeypatch, tmp_path):
    source = tmp_path / "clip.aac"
    source.write_bytes(b"fake")
    monkeypatch.setattr(files, "AudioSegment", None)

    with pytest.raises(UnsupportedFormat):
        files.ensure_wav(str(source))


def test_persist_and_cleanup_temp_file():
    payload = b"hello"

    path = files.persist_bytes(payload, suffix=".bin")

    with open(path, "rb") as fh:
        assert fh.read() == payload

    files.cleanup_temp(path)

    assert not os.path.exists(path)
