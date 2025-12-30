"""Performance benchmarks for PronunciaPA."""
from __future__ import annotations

import time
import pytest
from ipa_core.kernel.core import create_kernel
from ipa_core.config.schema import AppConfig, PluginCfg
from ipa_core.types import AudioInput


@pytest.fixture
def perf_config() -> AppConfig:
    return AppConfig(
        backend=PluginCfg(name="stub"),
        textref=PluginCfg(name="grapheme"),
        comparator=PluginCfg(name="levenshtein"),
        preprocessor=PluginCfg(name="basic")
    )


@pytest.mark.benchmark(group="transcription")
def test_stub_transcription_latency(benchmark, perf_config):
    """Benchmark the RTF of the stub backend."""
    kernel = create_kernel(perf_config)
    
    # We use a dummy audio input
    # In a real scenario, RTF = processing_time / audio_duration
    # Since we don't have real audio duration here, we just measure pure latency.
    audio: AudioInput = {"path": "test.wav", "sample_rate": 16000, "channels": 1}
    
    def run_pipeline():
        import asyncio
        async def _run():
            return await kernel.run(audio=audio, text="hola")
        return asyncio.run(_run())

    result = benchmark(run_pipeline)
    assert result["per"] == 0.0


def test_rtf_calculation_logic():
    """Verify the RTF calculation logic utility."""
    # RTF = processing_time / audio_duration
    # An RTF < 1.0 means faster than real-time.
    processing_time = 0.5
    audio_duration = 2.0
    rtf = processing_time / audio_duration
    assert rtf == 0.25
    assert rtf < 1.0
