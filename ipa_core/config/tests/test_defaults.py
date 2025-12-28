"""Tests para verificar los valores por defecto de la configuración."""
from __future__ import annotations
from ipa_core.config.schema import AppConfig

def test_app_config_empty_defaults() -> None:
    """Verifica que AppConfig se puede instanciar con valores por defecto."""
    # Actualmente esto fallará porque 'version' y los plugins son obligatorios
    config = AppConfig()
    
    assert config.version == 1
    assert config.preprocessor.name == "basic"
    assert config.backend.name == "allosaurus"
    assert config.textref.name == "grapheme"
    assert config.comparator.name == "levenshtein"
