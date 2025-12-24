"""Pruebas de contrato para la configuración usando Pydantic."""
from __future__ import annotations
import pytest
from pydantic import ValidationError
from ipa_core.config import schema

def test_app_config_validation() -> None:
    """Verifica que AppConfig valida correctamente los datos."""
    valid_data = {
        "version": 1,
        "preprocessor": {"name": "basic", "params": {}},
        "backend": {"name": "mock", "params": {}},
        "textref": {"name": "mock", "params": {}},
        "comparator": {"name": "mock", "params": {}},
        "options": {"lang": "es", "output": "json"},
    }
    config = schema.AppConfig(**valid_data)
    assert config.version == 1
    assert config.backend.name == "mock"

def test_app_config_invalid_data() -> None:
    """Verifica que AppConfig falla con datos inválidos."""
    invalid_data = {
        "version": "not-a-number",
        "backend": {"name": "mock"},
    }
    with pytest.raises(ValidationError):
        schema.AppConfig(**invalid_data)

def test_plugin_cfg_defaults() -> None:
    """Verifica valores por defecto en PluginCfg."""
    cfg = schema.PluginCfg(name="test")
    assert cfg.name == "test"
    assert cfg.params == {}