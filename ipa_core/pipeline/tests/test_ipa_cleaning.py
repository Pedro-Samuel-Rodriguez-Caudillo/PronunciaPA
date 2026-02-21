"""Tests para ipa_cleaning: limpieza unificada de tokens IPA."""
from __future__ import annotations

import pytest

from ipa_core.pipeline.ipa_cleaning import clean_asr_tokens, clean_textref_tokens


class TestCleanASRTokens:
    def test_removes_silence_markers(self):
        tokens = ["sil", "a", "b", "SIL", "c", "<sil>"]
        result = clean_asr_tokens(tokens)
        assert result == ["a", "b", "c"]

    def test_applies_lang_fixes_es(self):
        # r → ɾ en español
        tokens = ["r", "a"]
        result = clean_asr_tokens(tokens, lang="es")
        assert "ɾ" in result

    def test_r_in_english_becomes_approximant_not_tap(self):
        """r ASR en inglés debe producir /ɹ/, NO /ɾ/.

        Regresión: _ALLOSAURUS_FIXES solía hacer r→ɾ globalmente antes de que
        _LANG_FIXES pudiera actuar, convirtiendo inütilmente toda /r/ inglesa
        en la vibrante simple española.
        """
        result = clean_asr_tokens(["r", "ʌ", "n"], lang="en")
        assert "ɹ" in result, f"Esperaba ɹ en el resultado, obtenido: {result}"
        assert "ɾ" not in result, f"No se esperaba ɾ en resultado inglés: {result}"

    def test_collapses_duplicates(self):
        tokens = ["a", "a", "b", "b", "b", "c"]
        result = clean_asr_tokens(tokens)
        assert result == ["a", "b", "c"]

    def test_strips_non_ipa_artifacts(self):
        tokens = ["a", "123", "b", "[noise]"]
        result = clean_asr_tokens(tokens)
        assert "123" not in result
        # noise se filtra por ser artefacto con brackets
        assert all(t.isalpha() or ord(t[0]) > 127 for t in result)

    def test_empty_tokens_returns_empty(self):
        assert clean_asr_tokens([]) == []

    def test_all_silence_returns_empty(self):
        assert clean_asr_tokens(["sil", "SIL", "<sil>"]) == []

    def test_preserves_valid_ipa(self):
        tokens = ["ə", "ʃ", "ɛ"]
        result = clean_asr_tokens(tokens)
        assert result == ["ə", "ʃ", "ɛ"]


class TestCleanTextrefTokens:
    def test_removes_silence_markers(self):
        tokens = ["sil", "a", "b"]
        result = clean_textref_tokens(tokens)
        assert result == ["a", "b"]

    def test_preserves_allophones_from_textref(self):
        """clean_textref preserva IPA fonético de espeak sin colapsar alófonos.

        β, ð, ɣ son alófonos válidos del español; las equivalencias
        (b↔β, d↔ð, g↔ɣ) se resuelven en acceptable_variants al puntuar.
        """
        tokens = ["β", "a", "ð", "e", "ɣ", "o"]
        result = clean_textref_tokens(tokens, lang="es")
        assert "β" in result, f"β debe preservarse (IPA puro); result={result}"
        assert "ð" in result, f"ð debe preservarse (IPA puro); result={result}"
        assert "ɣ" in result, f"ɣ debe preservarse (IPA puro); result={result}"
        assert "b" not in result
        assert "d" not in result

    def test_strips_stress_marks(self):
        """El acento ˈ de espeak es suprasegmental y debe eliminarse."""
        tokens = ["p", "ˈ", "e", "s", "o"]
        result = clean_textref_tokens(tokens, lang="es")
        assert "ˈ" not in result
        assert result == ["p", "e", "s", "o"]

    def test_r_preserved_from_textref(self):
        """espeak produce ɾ directamente para el español; clean_textref lo preserva."""
        tokens = ["ɾ", "a"]
        result = clean_textref_tokens(tokens, lang="es")
        assert "ɾ" in result, f"ɾ debe preservarse desde espeak; result={result}"

    def test_does_not_collapse_duplicates(self):
        # Duplicates in textref are legitimate (e.g. gemination)
        tokens = ["l", "l", "a"]
        result = clean_textref_tokens(tokens)
        assert result == ["l", "l", "a"]

    def test_strips_non_ipa_artifacts(self):
        tokens = ["a", "42", "b"]
        result = clean_textref_tokens(tokens)
        assert "42" not in result

    def test_empty_tokens_returns_empty(self):
        assert clean_textref_tokens([]) == []

    def test_preserves_valid_ipa(self):
        tokens = ["k", "a", "s", "a"]
        result = clean_textref_tokens(tokens)
        assert result == ["k", "a", "s", "a"]
