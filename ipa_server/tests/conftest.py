"""Configuración de tests para ipa_server."""
import os
import pytest
from pathlib import Path
import tempfile
import yaml
from typing import Optional

from ipa_core.plugins import registry
from ipa_core.plugins.base import BasePlugin
from ipa_core.types import ASRResult, AudioInput
from ipa_server.routers import pipeline as pipeline_router


class TestIPAASR(BasePlugin):
    """ASR de pruebas estable que devuelve IPA fijo (no-stub)."""

    output_type = "ipa"

    async def transcribe(  # type: ignore[override]
        self,
        audio: AudioInput,
        *,
        lang: Optional[str] = None,
        **kw,
    ) -> ASRResult:
        return {
            "tokens": ["h", "o", "l", "a"],
            "meta": {"backend": "test_ipa", "lang": lang or "es"},
        }


@pytest.fixture(scope="session", autouse=True)
def setup_test_config():
    """Crea un archivo de configuración temporal para tests."""
    registry.register("asr", "test_ipa", lambda _params: TestIPAASR())

    test_config = {
        "version": 1,
        "language_pack": None,
        "model_pack": None,
        "backend": {"name": "test_ipa"},
        "textref": {"name": "grapheme"},
        "preprocessor": {"name": "basic"},
        "comparator": {"name": "levenshtein"},
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        config_path = f.name

    previous_asr = os.environ.get("PRONUNCIAPA_ASR")
    if "PRONUNCIAPA_ASR" in os.environ:
        del os.environ["PRONUNCIAPA_ASR"]
    
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
    if previous_asr is not None:
        os.environ["PRONUNCIAPA_ASR"] = previous_asr


@pytest.fixture(autouse=True)
def reset_kernel_singleton():
    """Evita contaminación entre tests para /v1/quick-compare."""
    pipeline_router._cached_kernel = None
    pipeline_router._kernel_ready = False
    yield
    pipeline_router._cached_kernel = None
    pipeline_router._kernel_ready = False

