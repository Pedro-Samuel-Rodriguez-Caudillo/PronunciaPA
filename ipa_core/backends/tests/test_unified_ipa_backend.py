"""Tests para UnifiedIPABackend."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ipa_core.backends.unified_ipa_backend import UnifiedIPABackend


@pytest.mark.asyncio
async def test_allosaurus_transcribe_uses_mapped_lang_positional() -> None:
    recognizer = MagicMock()
    recognizer.recognize.return_value = "t e s t"
    backend = UnifiedIPABackend(engine="allosaurus")
    backend._backend = recognizer
    backend._ready = True

    result = await backend.transcribe({"path": "clip.wav"}, lang="en")

    recognizer.recognize.assert_called_once_with("clip.wav", "eng")
    assert result["tokens"] == ["t", "e", "s", "t"]
    assert result["meta"]["lang"] == "en"
    assert result["meta"]["allosaurus_lang"] == "eng"


@pytest.mark.asyncio
async def test_allosaurus_transcribe_maps_regional_lang() -> None:
    recognizer = MagicMock()
    recognizer.recognize.return_value = "a b"
    backend = UnifiedIPABackend(engine="allosaurus")
    backend._backend = recognizer
    backend._ready = True

    result = await backend.transcribe({"path": "clip.wav"}, lang="EN_us")

    recognizer.recognize.assert_called_once_with("clip.wav", "eng")
    assert result["meta"]["lang"] == "en_us"
    assert result["meta"]["allosaurus_lang"] == "eng"


class _KeywordOnlyRecognizer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def recognize(self, path: str, *, lang_id: str) -> str:
        self.calls.append((path, lang_id))
        return "x y"


@pytest.mark.asyncio
async def test_allosaurus_transcribe_falls_back_to_lang_id_keyword() -> None:
    recognizer = _KeywordOnlyRecognizer()
    backend = UnifiedIPABackend(engine="allosaurus")
    backend._backend = recognizer
    backend._ready = True

    result = await backend.transcribe({"path": "clip.wav"}, lang="es-MX")

    assert recognizer.calls == [("clip.wav", "spa")]
    assert result["tokens"] == ["x", "y"]
    assert result["meta"]["lang"] == "es-mx"
    assert result["meta"]["allosaurus_lang"] == "spa"


@pytest.mark.asyncio
async def test_allosaurus_transcribe_uses_default_lang_when_request_missing() -> None:
    recognizer = MagicMock()
    recognizer.recognize.return_value = "o l a"
    backend = UnifiedIPABackend(engine="allosaurus", lang="pt-BR")
    backend._backend = recognizer
    backend._ready = True

    result = await backend.transcribe({"path": "clip.wav"})

    recognizer.recognize.assert_called_once_with("clip.wav", "por")
    assert result["meta"]["lang"] == "pt-br"
    assert result["meta"]["allosaurus_lang"] == "por"
