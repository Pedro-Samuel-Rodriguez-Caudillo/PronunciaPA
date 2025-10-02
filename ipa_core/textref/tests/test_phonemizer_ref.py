"""Tests for the Phonemizer-based TextRef implementation."""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from ipa_core.textref.phonemizer_ref import PhonemizerTextRef

SPANISH_IPA_RE = re.compile(r"ˈ?ola ˈ?mun\.?do")


@pytest.mark.parametrize(
    "text, pattern",
    [
        ("hola mundo", SPANISH_IPA_RE),
        ("¡Hola mundo!", SPANISH_IPA_RE),
    ],
)
def test_phonemizer_generates_spanish_ipa(text: str, pattern: re.Pattern[str]) -> None:
    textref = PhonemizerTextRef(language="es")
    ipa = textref.text_to_ipa(text)
    assert pattern.fullmatch(ipa), ipa
    assert unicodedata.is_normalized("NFC", ipa)


def test_language_override_and_config(tmp_path: Path) -> None:
    cfg_path = tmp_path / "phonemizer.yaml"
    cfg_path.write_text("language: en-us\n", encoding="utf-8")
    textref = PhonemizerTextRef(config_path=cfg_path)

    ipa_default = textref.text_to_ipa("taco")
    # En inglés la vocal tónica usa /æ/.
    assert "æ" in ipa_default

    ipa_spanish = textref.text_to_ipa("taco", lang="es")
    assert "æ" not in ipa_spanish
    assert ipa_spanish.startswith("ˈta")


def test_invalid_language_raises() -> None:
    textref = PhonemizerTextRef(language="es")
    with pytest.raises(ValueError):
        textref.text_to_ipa("hola", lang="")


def test_normalizer_applied_to_phonemizer_output(monkeypatch) -> None:
    def fake_phonemize(*args, **kwargs):
        return "t͡sa?!"

    monkeypatch.setattr("ipa_core.textref.phonemizer_ref.phonemize", fake_phonemize)

    textref = PhonemizerTextRef(language="es")
    assert textref.text_to_ipa("tza") == "tsa"
