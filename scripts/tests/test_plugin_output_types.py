"""Tests para validación de plugins ASR - output_type."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from ipa_core.plugins.base import BasePlugin
from ipa_core.types import ASRResult, AudioInput


class MockIPABackend(BasePlugin):
    """Mock backend que produce IPA."""
    output_type = "ipa"
    
    async def transcribe(self, audio: AudioInput, lang: str | None = None) -> ASRResult:
        return ASRResult(tokens=["k", "a", "s", "a"], text="kasa", confidence=0.95)


class MockTextBackend(BasePlugin):
    """Mock backend que produce texto."""
    output_type = "text"
    
    async def transcribe(self, audio: AudioInput, lang: str | None = None) -> ASRResult:
        return ASRResult(tokens=["casa"], text="casa", confidence=0.95)


def test_base_plugin_has_output_type():
    """Verifica que BasePlugin tiene el atributo output_type."""
    plugin = BasePlugin()
    assert hasattr(plugin, "output_type")
    assert plugin.output_type == "none"
    print("✅ BasePlugin has output_type attribute")


def test_ipa_backend_declares_output_type():
    """Verifica que un backend IPA declara correctamente su tipo."""
    backend = MockIPABackend()
    assert backend.output_type == "ipa"
    print("✅ IPA backend declares output_type='ipa'")


def test_text_backend_declares_output_type():
    """Verifica que un backend texto declara correctamente su tipo."""
    backend = MockTextBackend()
    assert backend.output_type == "text"
    print("✅ Text backend declares output_type='text'")


def test_kernel_validates_ipa_requirement():
    """Verifica que el kernel valida el requirement de IPA."""
    from ipa_core.config.schema import AppConfig, BackendConfig, TextRefConfig, ComparatorConfig, PreprocessorConfig
    
    # Mock config que requiere IPA
    cfg = AppConfig(
        backend=BackendConfig(name="mock_text_backend", params={}, require_ipa=True),
        textref=TextRefConfig(name="simple", params={}),
        comparator=ComparatorConfig(name="levenshtein", params={}),
        preprocessor=PreprocessorConfig(name="basic", params={}),
    )
    
    # Mock registry para retornar nuestro backend texto
    from ipa_core.plugins import registry
    original_resolve = registry.resolve_asr
    
    def mock_resolve_asr(name, params):
        if name == "mock_text_backend":
            return MockTextBackend()
        return original_resolve(name, params)
    
    # Parchear temporalmente
    registry.resolve_asr = mock_resolve_asr
    
    try:
        from ipa_core.kernel.core import create_kernel
        
        # Esto debe lanzar ValueError porque el backend produce texto
        with pytest.raises(ValueError) as exc_info:
            create_kernel(cfg)
        
        assert "produce 'text', no IPA" in str(exc_info.value)
        print("✅ Kernel rejects text backend when require_ipa=True")
    finally:
        # Restaurar
        registry.resolve_asr = original_resolve


def test_allosaurus_backend_is_ipa():
    """Verifica que AllosaurusBackend declara output_type='ipa'."""
    try:
        from ipa_core.backends.allosaurus_backend import AllosaurusBackend
        
        # Solo verifica el atributo de clase, no instancia (evita cargar modelo)
        assert hasattr(AllosaurusBackend, "output_type")
        assert AllosaurusBackend.output_type == "ipa"
        print("✅ AllosaurusBackend declares output_type='ipa'")
    except ImportError:
        print("⚠️ AllosaurusBackend not available (allosaurus not installed)")


def test_wav2vec2_backend_is_text_by_default():
    """Verifica que Wav2Vec2Backend declara output_type='text' por defecto."""
    try:
        from ipa_core.backends.wav2vec2_backend import Wav2Vec2Backend
        
        assert hasattr(Wav2Vec2Backend, "output_type")
        assert Wav2Vec2Backend.output_type == "text"
        print("✅ Wav2Vec2Backend declares output_type='text' by default")
    except ImportError:
        print("⚠️ Wav2Vec2Backend not available (transformers not installed)")


def test_vosk_backend_is_text():
    """Verifica que VoskBackend declara output_type='text'."""
    try:
        from ipa_core.backends.vosk_backend import VoskBackend
        
        assert hasattr(VoskBackend, "output_type")
        assert VoskBackend.output_type == "text"
        print("✅ VoskBackend declares output_type='text'")
    except ImportError:
        print("⚠️ VoskBackend not available (vosk not installed)")


if __name__ == "__main__":
    test_base_plugin_has_output_type()
    test_ipa_backend_declares_output_type()
    test_text_backend_declares_output_type()
    test_allosaurus_backend_is_ipa()
    test_wav2vec2_backend_is_text_by_default()
    test_vosk_backend_is_text()
    
    # Test de validación del kernel (requiere pytest)
    print("\n⚠️ Ejecuta `pytest` para el test de validación del kernel")
    print("   pytest scripts/tests/test_plugin_output_types.py::test_kernel_validates_ipa_requirement")
    
    print("\n✅ Basic plugin output_type tests passed!")
