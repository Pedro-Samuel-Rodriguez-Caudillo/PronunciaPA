"""Tests para LexiconTextRef — backend con léxico inline + fallback eSpeak."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from ipa_core.textref.lexicon import LexiconTextRef, normalize_word


_LEXICON = {
    "hola": "o l a",
    "mundo": "m u n d o",
    "casa": "k a s a",
    "perro": "p e r o",
}


def _run(coro):
    """Ejecutar una coroutine sincrónicamente (compatible con asyncio_mode=auto y sin él)."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestNormalizeWord:
    def test_lowercase(self):
        assert normalize_word("HOLA") == "hola"

    def test_removes_punctuation(self):
        assert normalize_word("hola,") == "hola"
        assert normalize_word("mundo") == "mundo"

    def test_nfd_normalization(self):
        result = normalize_word("café")
        assert result  # No vacío


class TestLexiconTextRefInit:
    def test_empty_lexicon(self):
        tr = LexiconTextRef()
        assert tr.lexicon_size == 0

    def test_lexicon_size(self):
        tr = LexiconTextRef(lexicon=_LEXICON)
        assert tr.lexicon_size == len(_LEXICON)


class TestLookup:
    def test_lookup_existing(self):
        tr = LexiconTextRef(lexicon=_LEXICON)
        result = tr.lookup("hola")
        assert result == "o l a"

    def test_lookup_missing(self):
        tr = LexiconTextRef(lexicon=_LEXICON)
        assert tr.lookup("inexistente") is None

    def test_contains(self):
        tr = LexiconTextRef(lexicon=_LEXICON)
        assert tr.contains("mundo")
        assert not tr.contains("inexistente")


class TestToIpa:
    def test_empty_text(self):
        tr = LexiconTextRef(lexicon=_LEXICON)
        result = _run(tr.to_ipa(""))
        assert result["tokens"] == []
        assert result["meta"]["empty"] is True

    def test_single_word_in_lexicon(self):
        tr = LexiconTextRef(lexicon=_LEXICON)
        result = _run(tr.to_ipa("hola"))
        assert result["tokens"] == ["o", "l", "a"]
        assert result["meta"]["lexicon_hits"] == 1
        assert result["meta"]["oov_count"] == 0

    def test_multiple_words_in_lexicon(self):
        tr = LexiconTextRef(lexicon=_LEXICON)
        result = _run(tr.to_ipa("hola mundo"))
        assert result["meta"]["lexicon_hits"] == 2
        assert result["meta"]["oov_count"] == 0
        tokens = result["tokens"]
        assert len(tokens) > 0

    def test_oov_with_espeak_fallback(self):
        """Palabras OOV deben pasarse a eSpeak una por una."""
        mock_espeak = MagicMock()
        mock_espeak.to_ipa = AsyncMock(
            return_value={"tokens": ["x", "i", "r", "o"], "meta": {}}
        )
        tr = LexiconTextRef(lexicon=_LEXICON, espeak_fallback=mock_espeak)
        result = _run(tr.to_ipa("hola extraño"))
        assert result["meta"]["oov_count"] == 1
        mock_espeak.to_ipa.assert_called_once()
        assert len(result["tokens"]) > 0

    def test_oov_without_fallback(self):
        """Sin fallback, palabras OOV producen tokens vacíos (pero no error)."""
        tr = LexiconTextRef(lexicon=_LEXICON, espeak_fallback=None)
        result = _run(tr.to_ipa("hola desconocida"))
        assert result["meta"]["oov_count"] == 1
        assert "o" in result["tokens"]  # tokens de 'hola' deben estar

    def test_espeak_failure_graceful(self):
        """Si eSpeak falla, la función no debe lanzar excepción."""
        mock_espeak = MagicMock()
        mock_espeak.to_ipa = AsyncMock(side_effect=Exception("espeak crashed"))
        tr = LexiconTextRef(lexicon=_LEXICON, espeak_fallback=mock_espeak)
        result = _run(tr.to_ipa("hola desconocida"))
        assert result is not None
        assert "tokens" in result

    def test_case_insensitive(self):
        """La búsqueda debe ser insensible a mayúsculas."""
        tr = LexiconTextRef(lexicon=_LEXICON)
        result = _run(tr.to_ipa("HOLA"))
        assert result["tokens"] == ["o", "l", "a"]

    def test_multiple_oov_words_separate_espeak_calls(self):
        """Cada palabra OOV tiene su propia llamada a eSpeak (Brecha 5 fix)."""
        call_count = 0

        async def fake_espeak(word, *, lang=None, **kw):
            nonlocal call_count
            call_count += 1
            return {"tokens": ["x"], "meta": {}}

        mock_espeak = MagicMock()
        mock_espeak.to_ipa = fake_espeak
        tr = LexiconTextRef(lexicon={}, espeak_fallback=mock_espeak)
        _run(tr.to_ipa("foo bar baz"))
        assert call_count == 3  # Una llamada por palabra OOV


class TestFromPackDict:
    def test_normalizes_keys(self):
        raw = {"HOLA": "o l a", "Mundo": "m u n d o"}
        tr = LexiconTextRef.from_pack_dict(raw)
        # Internamente las claves se normalizan a minúsculas
        assert tr.contains("hola")
        assert tr.contains("mundo")
        # contains() también normaliza la entrada, así que "HOLA" → "hola" → True
        assert tr.contains("HOLA")
        # Una clave que nunca existió
        assert not tr.contains("inexistente")

    def test_with_espeak_fallback(self):
        mock_espeak = MagicMock()
        tr = LexiconTextRef.from_pack_dict(
            {"hola": "o l a"},
            espeak_fallback=mock_espeak,
        )
        assert tr._espeak is mock_espeak
