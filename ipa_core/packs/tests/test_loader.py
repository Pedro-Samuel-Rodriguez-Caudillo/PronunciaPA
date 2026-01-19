"""Tests for loading language packs with new structure."""
from __future__ import annotations

import pytest
from pathlib import Path

from ipa_core.packs.loader import load_language_pack, DEFAULT_PACKS_DIR


def test_default_packs_dir_is_plugins() -> None:
    """DEFAULT_PACKS_DIR points to plugins/language_packs/."""
    assert "plugins" in str(DEFAULT_PACKS_DIR)
    assert "language_packs" in str(DEFAULT_PACKS_DIR)


def test_load_language_pack_es_mx() -> None:
    """Load es-mx pack with new manifest structure."""
    pack = load_language_pack("es-mx")
    assert pack.id == "es-mx"
    assert pack.language == "es"


def test_load_language_pack_en_us() -> None:
    """Load en-us pack with new manifest structure."""
    pack = load_language_pack("en-us")
    assert pack.id == "en-us"
    assert pack.language == "en"


# Model pack tests removed - structure changed
