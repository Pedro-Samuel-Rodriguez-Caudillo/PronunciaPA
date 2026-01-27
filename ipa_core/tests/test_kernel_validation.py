"""Tests para validación de plugins ASR en el kernel.

Verifica que el kernel rechaza correctamente plugins ASR que:
1. No declaran output_type
2. Declaran output_type != 'ipa'
"""
import pytest
from unittest.mock import MagicMock

from ipa_core.config.schema import AppConfig, PluginCfg
from ipa_core.kernel.core import create_kernel


class FakeASRWithoutOutputType:
    """Plugin ASR que NO declara output_type."""
    
    async def setup(self) -> None:
        pass
    
    async def teardown(self) -> None:
        pass
    
    async def transcribe(self, audio, *, lang=None, **kw):
        return {"tokens": [], "raw_text": "", "meta": {}}


class FakeASRWithTextOutput:
    """Plugin ASR que declara output_type='text'."""
    
    output_type = "text"
    
    async def setup(self) -> None:
        pass
    
    async def teardown(self) -> None:
        pass
    
    async def transcribe(self, audio, *, lang=None, **kw):
        return {"tokens": [], "raw_text": "", "meta": {}}


class FakeASRWithIPAOutput:
    """Plugin ASR que declara output_type='ipa' (válido)."""
    
    output_type = "ipa"
    
    async def setup(self) -> None:
        pass
    
    async def teardown(self) -> None:
        pass
    
    async def transcribe(self, audio, *, lang=None, **kw):
        return {"tokens": ["h", "o", "l", "a"], "raw_text": "", "meta": {}}


def test_kernel_rejects_asr_without_output_type(monkeypatch):
    """El kernel debe rechazar plugins que no declaran output_type."""
    # Mock del registry para retornar nuestro plugin fake
    from ipa_core.plugins import registry
    
    monkeypatch.setattr(registry, "resolve_asr", lambda name, params: FakeASRWithoutOutputType())
    monkeypatch.setattr(registry, "resolve_preprocessor", lambda name, params: MagicMock())
    monkeypatch.setattr(registry, "resolve_textref", lambda name, params: MagicMock())
    monkeypatch.setattr(registry, "resolve_comparator", lambda name, params: MagicMock())
    
    cfg = AppConfig(
        backend=PluginCfg(name="fake_no_output", params={})
    )
    
    with pytest.raises(ValueError, match="produce 'none', no IPA"):
        create_kernel(cfg)


def test_kernel_rejects_asr_with_text_output(monkeypatch):
    """El kernel debe rechazar plugins que producen texto."""
    from ipa_core.plugins import registry
    
    monkeypatch.setattr(registry, "resolve_asr", lambda name, params: FakeASRWithTextOutput())
    monkeypatch.setattr(registry, "resolve_preprocessor", lambda name, params: MagicMock())
    monkeypatch.setattr(registry, "resolve_textref", lambda name, params: MagicMock())
    monkeypatch.setattr(registry, "resolve_comparator", lambda name, params: MagicMock())
    
    cfg = AppConfig(
        backend=PluginCfg(name="fake_text", params={})
    )
    
    with pytest.raises(ValueError, match="produce 'text', no IPA"):
        create_kernel(cfg)


def test_kernel_accepts_asr_with_ipa_output(monkeypatch):
    """El kernel debe aceptar plugins que producen IPA."""
    from ipa_core.plugins import registry
    
    monkeypatch.setattr(registry, "resolve_asr", lambda name, params: FakeASRWithIPAOutput())
    monkeypatch.setattr(registry, "resolve_preprocessor", lambda name, params: MagicMock())
    monkeypatch.setattr(registry, "resolve_textref", lambda name, params: MagicMock())
    monkeypatch.setattr(registry, "resolve_comparator", lambda name, params: MagicMock())
    
    cfg = AppConfig(
        backend=PluginCfg(name="fake_ipa", params={})
    )
    
    # No debe lanzar excepción
    kernel = create_kernel(cfg)
    assert kernel.asr is not None


def test_kernel_allows_bypass_with_require_ipa_false(monkeypatch):
    """El kernel debe permitir bypass con require_ipa=false."""
    from ipa_core.plugins import registry
    
    monkeypatch.setattr(registry, "resolve_asr", lambda name, params: FakeASRWithTextOutput())
    monkeypatch.setattr(registry, "resolve_preprocessor", lambda name, params: MagicMock())
    monkeypatch.setattr(registry, "resolve_textref", lambda name, params: MagicMock())
    monkeypatch.setattr(registry, "resolve_comparator", lambda name, params: MagicMock())
    
    cfg = AppConfig(
        backend=PluginCfg(name="fake_text", params={"require_ipa": False})
    )
    
    # No debe lanzar excepción porque require_ipa=False
    kernel = create_kernel(cfg)
    assert kernel.asr is not None
