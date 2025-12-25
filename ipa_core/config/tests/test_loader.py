"""Pruebas para el cargador de configuración."""
from __future__ import annotations
import os
import pytest
from ipa_core.config import loader, schema

@pytest.fixture
def sample_yaml_file(tmp_path) -> str:
    """Crea un archivo YAML de prueba."""
    content = """
version: 1
preprocessor:
  name: basic
  params:
    threshold: 0.5
backend:
  name: whisper
textref:
  name: epitran
comparator:
  name: levenshtein
options:
  lang: es
"""
    d = tmp_path / "config"
    d.mkdir()
    f = d / "test_config.yaml"
    f.write_text(content)
    return str(f)

def test_load_config_from_yaml(sample_yaml_file) -> None:
    """Verifica la carga desde un archivo YAML."""
    config = loader.load_config(sample_yaml_file)
    assert isinstance(config, schema.AppConfig)
    assert config.version == 1
    assert config.preprocessor.name == "basic"
    assert config.preprocessor.params["threshold"] == 0.5
    assert config.options.lang == "es"

def test_load_config_with_env_overrides(sample_yaml_file) -> None:
    """Verifica que las variables de entorno sobrescriben la config."""
    os.environ["PRONUNCIAPA_OPTIONS_LANG"] = "en"
    try:
        config = loader.load_config(sample_yaml_file)
        assert config.options.lang == "en"
    finally:
        del os.environ["PRONUNCIAPA_OPTIONS_LANG"]

def test_load_config_with_env_new_section(tmp_path) -> None:
    """Verifica que las variables de entorno pueden crear secciones."""
    content = "version: 1\nbackend: {name: 'mock'}\ntextref: {name: 'mock'}\ncomparator: {name: 'mock'}\npreprocessor: {name: 'mock'}"
    f = tmp_path / "min_config.yaml"
    f.write_text(content)
    
    os.environ["PRONUNCIAPA_OPTIONS_LANG"] = "fr"
    try:
        config = loader.load_config(str(f))
        assert config.options.lang == "fr"
    finally:
        del os.environ["PRONUNCIAPA_OPTIONS_LANG"]

def test_load_config_file_not_found() -> None:
    """Verifica error si el archivo no existe."""
    with pytest.raises(FileNotFoundError):
        loader.load_config("non_existent.yaml")
