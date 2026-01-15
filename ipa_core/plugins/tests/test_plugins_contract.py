"""Pruebas para el registro y resolución de plugins."""
from __future__ import annotations
import pytest
from ipa_core.plugins import registry


def test_register_and_resolve_plugin() -> None:
    """Verifica que se pueden registrar y resolver plugins."""
    def mock_plugin(params):
        return f"plugin-with-{params}"
    
    registry.register("asr", "mock", mock_plugin)
    
    resolved = registry.resolve("asr", "mock", {"p": 1})
    assert resolved == "plugin-with-{'p': 1}"


def test_resolve_unregistered_plugin() -> None:
    """Verifica error al resolver un plugin no registrado."""
    with pytest.raises(KeyError):
        registry.resolve("asr", "non-existent", {})


def test_invalid_category() -> None:
    """Verifica error con categorías inválidas."""
    with pytest.raises(ValueError):
        registry.register("invalid", "test", lambda x: x)


def test_specific_resolvers() -> None:
    """Verifica los resolutores específicos por conveniencia."""
    registry.register("asr", "asr1", lambda x: "ok")
    assert registry.resolve_asr("asr1") == "ok"

    registry.register("textref", "tr1", lambda x: "ok")
    assert registry.resolve_textref("tr1") == "ok"

    registry.register("comparator", "cmp1", lambda x: "ok")
    assert registry.resolve_comparator("cmp1") == "ok"

    registry.register("preprocessor", "pp1", lambda x: "ok")
    assert registry.resolve_preprocessor("pp1") == "ok"


def test_resolve_default_plugin() -> None:
    """Verifica que se pueden resolver plugins por defecto (lazy load)."""
    # Limpiar registro para forzar carga de defaults
    registry._REGISTRY["asr"] = {}

    # Esto debería disparar _register_defaults
    stub = registry.resolve("asr", "stub")

    from ipa_core.backends.asr_stub import StubASR

    assert isinstance(stub, StubASR)
