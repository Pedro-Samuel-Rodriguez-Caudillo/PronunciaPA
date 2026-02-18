"""Integration tests for Kernel orchestration."""
from __future__ import annotations

import pytest
from ipa_core.kernel.core import create_kernel, Kernel
from ipa_core.config.schema import AppConfig, PluginCfg
from ipa_core.types import AudioInput


@pytest.fixture
def mock_config() -> AppConfig:
    """Creates a config that uses stubs for all components."""
    return AppConfig(
        backend=PluginCfg(name="stub"),
        textref=PluginCfg(name="grapheme"),
        comparator=PluginCfg(name="levenshtein"),
        preprocessor=PluginCfg(name="basic")
    )


@pytest.mark.asyncio
async def test_kernel_run_e2e_flow(mock_config):
    """Verify the full flow: pre -> asr -> textref -> compare."""
    kernel = create_kernel(mock_config)
    await kernel.setup()
    try:
        audio: AudioInput = {"path": "test.wav", "sample_rate": 16000, "channels": 1}
        # test.wav does not exist → StubASR returns default tokens ['o', 'l', 'a']
        # grapheme textref for 'ola' -> ['o', 'l', 'a']
        # compare -> PER 0.0
        result = await kernel.run(audio=audio, text="ola", lang="es")

        assert result["per"] == 0.0
        assert len(result["alignment"]) == 3
        for ref, hyp in result["alignment"]:
            assert ref == hyp
    finally:
        await kernel.teardown()


@pytest.mark.asyncio
async def test_kernel_run_with_mismatch(mock_config):
    """Verify PER calculation when there is a mismatch."""
    kernel = create_kernel(mock_config)
    await kernel.setup()
    try:
        audio: AudioInput = {"path": "test.wav", "sample_rate": 16000, "channels": 1}
        # test.wav does not exist → StubASR returns default tokens ['o', 'l', 'a']
        # text 'hola' -> grapheme ['h', 'o', 'l', 'a']
        # Comparison: ['o','l','a'] vs ['h','o','l','a'] → 1 deletion → PER > 0
        result = await kernel.run(audio=audio, text="hola", lang="es")

        assert result["per"] > 0.0
        assert "ops" in result
    finally:
        await kernel.teardown()


@pytest.mark.asyncio
async def test_kernel_setup_failure(mock_config, monkeypatch):
    """Verify that kernel propagates setup failures from components."""
    from ipa_core.errors import NotReadyError
    
    kernel = create_kernel(mock_config)
    
    async def failing_setup():
        raise NotReadyError("Mock failure")
        
    monkeypatch.setattr(kernel.asr, "setup", failing_setup)
    
    with pytest.raises(NotReadyError):
        await kernel.setup()


@pytest.mark.asyncio
async def test_kernel_run_without_setup(mock_config):
    """Verify behavior when run is called without setup.
    
    Note: Current implementation delegates to run_pipeline, which might 
    implicitly trigger setup or fail if components require it.
    """
    kernel = create_kernel(mock_config)
    # Most backends (stubs) handle this, but real backends should fail.
    # Here we just verify it doesn't crash the kernel orchestrator itself.
    audio: AudioInput = {"path": "test.wav", "sample_rate": 16000, "channels": 1}
    await kernel.run(audio=audio, text="hola")
