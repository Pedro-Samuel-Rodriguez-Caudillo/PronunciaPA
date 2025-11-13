"""Tests para `EspeakTextRef`."""
from __future__ import annotations

import pytest

from ipa_core.errors import NotReadyError
from ipa_core.textref.espeak import EspeakTextRef


def test_espeak_produces_tokens_from_runner():
    captured_cmd = {}

    def fake_runner(cmd, text):
        captured_cmd["cmd"] = cmd
        captured_cmd["text"] = text
        return "h o l a"

    provider = EspeakTextRef(default_lang="es", binary="espeak", runner=fake_runner)

    tokens = provider.to_ipa(" hola ", lang="es")

    assert tokens == ["h", "o", "l", "a"]
    assert captured_cmd["cmd"][0] == "espeak"
    assert "--ipa=3" in captured_cmd["cmd"]
    assert captured_cmd["text"] == "hola"


def test_espeak_detects_binary_and_raises_when_missing(monkeypatch):
    monkeypatch.setenv("PRONUNCIAPA_ESPEAK_BIN", "")
    monkeypatch.setenv("ESPEAK_BIN", "")
    monkeypatch.setenv("PATH", "")
    with pytest.raises(NotReadyError):
        EspeakTextRef()
