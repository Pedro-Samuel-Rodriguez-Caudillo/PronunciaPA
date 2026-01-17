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

def test_load_config_file_not_found_explicit_path() -> None:
    """Verifica error si se pasa una ruta explícita que no existe."""
    with pytest.raises(FileNotFoundError):
        loader.load_config("non_existent.yaml")

def test_load_config_default_fallback(monkeypatch) -> None:
    """Verifica que si no hay archivos, retorna la config por defecto."""
    # Aseguramos que no hay variables de entorno ni archivos en el CWD
    monkeypatch.delenv("PRONUNCIAPA_CONFIG", raising=False)
    
    # Mock de existencia de archivos
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("pathlib.Path.exists", lambda _: False)
        config = loader.load_config()
        assert config.backend.name == "stub" # Default en schema.py

def test_load_config_env_path_priority(tmp_path, monkeypatch) -> None:
    """Verifica que PRONUNCIAPA_CONFIG tiene prioridad."""
    f = tmp_path / "env_config.yaml"
    f.write_text("version: 1\nbackend: {name: 'env-backend'}\ntextref: {name: 'mock'}\ncomparator: {name: 'mock'}\npreprocessor: {name: 'mock'}")
    
    monkeypatch.setenv("PRONUNCIAPA_CONFIG", str(f))
    
    config = loader.load_config()
    assert config.backend.name == "env-backend"

def test_load_config_cwd_fallback(tmp_path, monkeypatch) -> None:
    """Verifica que busca config.yaml en el CWD."""
    f = tmp_path / "config.yaml"
    f.write_text("version: 1\nbackend: {name: 'cwd-backend'}\ntextref: {name: 'mock'}\ncomparator: {name: 'mock'}\npreprocessor: {name: 'mock'}")
    
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PRONUNCIAPA_CONFIG", raising=False)
    
    config = loader.load_config()
    assert config.backend.name == "cwd-backend"

def test_load_config_maps_del_weight(tmp_path) -> None:
    """Verifica que 'del' se mapea a 'del_' en params del comparador."""
    content = (
        "version: 1\n"
        "backend: {name: 'stub'}\n"
        "textref: {name: 'mock'}\n"
        "comparator:\n"
        "  name: levenshtein\n"
        "  params:\n"
        "    del: 2.0\n"
        "preprocessor: {name: 'mock'}\n"
    )
    f = tmp_path / "weights_config.yaml"
    f.write_text(content)
    config = loader.load_config(str(f))
    assert config.comparator.params["del_"] == 2.0
    assert "del" not in config.comparator.params

def test_load_config_env_coercion(tmp_path, monkeypatch) -> None:
    """Verifica que las variables de entorno convierten números."""
    content = "version: 1\nbackend: {name: 'stub'}\ntextref: {name: 'mock'}\ncomparator: {name: 'mock'}\npreprocessor: {name: 'mock'}"
    f = tmp_path / "env_types.yaml"
    f.write_text(content)
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_PARAMS_CHUNK_SEC", "30.5")
    config = loader.load_config(str(f))
    assert config.backend.params["chunk_sec"] == 30.5

def test_load_config_env_aliases(tmp_path, monkeypatch) -> None:
    """Verifica que PRONUNCIAPA_ASR mapea a backend.name."""
    content = "version: 1\nbackend: {name: 'stub'}\ntextref: {name: 'mock'}\ncomparator: {name: 'mock'}\npreprocessor: {name: 'mock'}"
    f = tmp_path / "alias_config.yaml"
    f.write_text(content)
    monkeypatch.setenv("PRONUNCIAPA_ASR", "onnx")
    config = loader.load_config(str(f))
    assert config.backend.name == "onnx"
