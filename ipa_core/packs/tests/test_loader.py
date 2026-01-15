"""Tests for loading language packs."""
from __future__ import annotations

from ipa_core.packs.loader import load_language_pack


def test_load_language_pack_en_us() -> None:
    pack = load_language_pack("en-us")
    assert pack.id == "en-us"
    assert pack.language == "en"
    assert pack.inventory.path == "inventory.yaml"
    assert pack.lexicon.path == "lexicon.tsv"
    assert pack.tts is not None
    assert pack.tts.provider == "piper"
