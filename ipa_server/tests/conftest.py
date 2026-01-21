"""Configuración de tests para ipa_server."""
import os
import pytest
from pathlib import Path
import tempfile
import yaml


@pytest.fixture(scope="session", autouse=True)
def setup_test_config():
    """Crea un archivo de configuración temporal para tests."""
    test_config = {
        "version": 1,
        "language_pack": None,
        "model_pack": None,
        "backend": {"name": "stub"},
        "textref": {"name": "grapheme"},
        "preprocessor": {"name": "basic"},
        "comparator": {"name": "levenshtein"},
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        config_path = f.name
    
    # Configurar variable de entorno para usar este config
    os.environ["PRONUNCIAPA_CONFIG"] = config_path
    
    yield
    
    # Limpiar
    try:
        Path(config_path).unlink()
    except:
        pass
    if "PRONUNCIAPA_CONFIG" in os.environ:
        del os.environ["PRONUNCIAPA_CONFIG"]

