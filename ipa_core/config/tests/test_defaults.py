"""Tests para verificar los valores por defecto de la configuración."""
from __future__ import annotations
from ipa_core.config.schema import AppConfig

def test_app_config_empty_defaults(monkeypatch) -> None:
    """Verifica que AppConfig se puede instanciar con valores por defecto."""
    # Limpiar env vars que pydantic-settings leería automáticamente
    monkeypatch.delenv("PRONUNCIAPA_ASR", raising=False)
    monkeypatch.delenv("PRONUNCIAPA_BACKEND__NAME", raising=False)
    monkeypatch.delenv("PRONUNCIAPA_TEXTREF__NAME", raising=False)

    config = AppConfig()

    assert config.version == 1
    assert config.preprocessor.name == "basic"
    assert config.backend.name == "stub"
    assert config.textref.name == "auto"
    assert config.comparator.name == "levenshtein"
    assert config.tts.name == "default"
    assert config.llm.name == "rule_based"
    assert config.language_pack is None
    assert config.model_pack is None
