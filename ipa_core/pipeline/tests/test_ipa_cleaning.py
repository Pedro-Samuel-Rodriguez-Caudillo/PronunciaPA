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

    def test_does_not_apply_lang_fixes(self):
        # r should stay as r (textref is canonical)
        tokens = ["r", "a"]
        result = clean_textref_tokens(tokens, lang="es")
        # Should NOT apply the r→ɾ fix
        assert "r" in result

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
