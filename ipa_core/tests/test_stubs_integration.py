"""Pruebas de integración para las implementaciones stub."""
from __future__ import annotations
import pytest
from ipa_core.plugins import registry
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.textref import TextRefProvider
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor

def test_resolve_stub_asr() -> None:
    """Verifica que se puede resolver el ASR stub."""
    obj = registry.resolve("asr", "stub")
    assert isinstance(obj, ASRBackend)
    result = obj.transcribe({"path": "test.wav", "sample_rate": 16000, "channels": 1}, lang="es")
    assert "tokens" in result

def test_resolve_simple_textref() -> None:
    """Verifica que se puede resolver el TextRef simple."""
    obj = registry.resolve("textref", "grapheme")
    assert isinstance(obj, TextRefProvider)
    tokens = obj.to_ipa("hola", lang="es")
    assert tokens == ["h", "o", "l", "a"]

def test_resolve_noop_comparator() -> None:
    """Verifica que se puede resolver el comparador noop."""
    obj = registry.resolve("comparator", "noop")
    assert isinstance(obj, Comparator)
    result = obj.compare(["a"], ["a"])
    assert result["per"] == 0.0

def test_resolve_basic_preprocessor() -> None:
    """Verifica que se puede resolver el preprocesador básico."""
    obj = registry.resolve("preprocessor", "basic")
    assert isinstance(obj, Preprocessor)
    tokens = obj.normalize_tokens([" A ", "b"])
    assert tokens == ["a", "b"]
