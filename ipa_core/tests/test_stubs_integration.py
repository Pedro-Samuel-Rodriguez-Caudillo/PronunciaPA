"""Pruebas de integración para las implementaciones stub."""
from __future__ import annotations
import pytest
from ipa_core.plugins import registry
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.textref import TextRefProvider
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor

@pytest.mark.asyncio

async def test_resolve_stub_asr() -> None:

    """Verifica que se puede resolver el ASR stub."""

    obj = registry.resolve("asr", "stub")

    assert isinstance(obj, ASRBackend)

    result = await obj.transcribe({"path": "test.wav", "sample_rate": 16000, "channels": 1}, lang="es")

    assert "tokens" in result





@pytest.mark.asyncio

async def test_resolve_simple_textref() -> None:

    """Verifica que se puede resolver el TextRef simple."""

    obj = registry.resolve("textref", "grapheme")

    assert isinstance(obj, TextRefProvider)

    res = await obj.to_ipa("hola", lang="es")

    assert res["tokens"] == ["h", "o", "l", "a"]





@pytest.mark.asyncio

async def test_resolve_noop_comparator() -> None:

    """Verifica que se puede resolver el comparador noop."""

    obj = registry.resolve("comparator", "noop")

    assert isinstance(obj, Comparator)

    result = await obj.compare(["a"], ["a"])

    assert result["per"] == 0.0





@pytest.mark.asyncio

async def test_resolve_basic_preprocessor() -> None:

    """Verifica que se puede resolver el preprocesador básico."""

    obj = registry.resolve("preprocessor", "basic")

    assert isinstance(obj, Preprocessor)

    res = await obj.normalize_tokens([" A ", "b"])

    assert res["tokens"] == ["A", "b"]

