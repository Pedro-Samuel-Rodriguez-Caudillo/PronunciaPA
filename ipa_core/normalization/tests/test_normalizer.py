"""Tests para el normalizador IPA configurable."""
from __future__ import annotations

import unicodedata
from pathlib import Path

from ipa_core.normalization import IPANormalizer

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "normalization.yaml"


def _normalizer() -> IPANormalizer:
    return IPANormalizer.from_config_file(CONFIG_PATH)


def test_unicode_normalization_applied() -> None:
    normalizer = _normalizer()
    text = "a\u0303"  # 'a' + tilde combinante
    result = normalizer.normalize(text)
    assert result == "ã"
    assert unicodedata.is_normalized("NFC", result)


def test_replacements_handle_diacritics_and_allophones() -> None:
    normalizer = _normalizer()
    text = "ɡato t͡ʃico d͡ʒugo"
    assert normalizer.normalize(text) == "gato tʃico dʒugo"


def test_filters_remove_non_ipa_characters() -> None:
    normalizer = _normalizer()
    text = "hola! mundo?"
    assert normalizer.normalize(text) == "hola mundo"


def test_whitespace_collapses_after_normalization() -> None:
    normalizer = _normalizer()
    text = "  ɡato\n\n grande  "
    assert normalizer.normalize(text) == "gato grande"
