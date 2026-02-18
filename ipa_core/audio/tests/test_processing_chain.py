"""Tests para AudioProcessingChain y sus pasos."""
from __future__ import annotations

import os
import wave
import tempfile
import struct
import pytest

from ipa_core.audio.processing_chain import (
    AudioContext,
    AudioProcessingChain,
    EnsureWavStep,
    VADTrimStep,
    QualityCheckStep,
)
from ipa_core.types import AudioInput


# ── Helpers ───────────────────────────────────────────────────────────

def _make_wav(path: str, duration_ms: int = 500, sample_rate: int = 16000) -> None:
    """Crear un WAV sintético 16-bit mono con silencio."""
    n_frames = int(sample_rate * duration_ms / 1000)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))


def _audio_input(path: str, sample_rate: int = 16000) -> AudioInput:
    return {"path": path, "sample_rate": sample_rate, "channels": 1}


# ── AudioContext ──────────────────────────────────────────────────────

class TestAudioContext:
    def test_was_step_applied_false_initially(self):
        ctx = AudioContext(audio=_audio_input("/tmp/x.wav"))
        assert not ctx.was_step_applied("ensure_wav")

    def test_mark_step_idempotent(self):
        ctx = AudioContext(audio=_audio_input("/tmp/x.wav"))
        ctx.mark_step("ensure_wav")
        ctx.mark_step("ensure_wav")
        assert ctx.steps_applied.count("ensure_wav") == 1

    def test_cleanup_removes_temp_files(self, tmp_path):
        f = tmp_path / "tmp.wav"
        f.write_bytes(b"x")
        ctx = AudioContext(audio=_audio_input(str(f)))
        ctx.add_temp_file(str(f))
        ctx.cleanup()
        assert not f.exists()
        assert ctx.temp_files == []

    def test_cleanup_handles_missing_file(self, tmp_path):
        ctx = AudioContext(audio=_audio_input("/nonexistent/path.wav"))
        ctx.add_temp_file("/nonexistent/path.wav")
        ctx.cleanup()  # Should not raise
        assert ctx.temp_files == []


# ── EnsureWavStep ─────────────────────────────────────────────────────

class TestEnsureWavStep:
    @pytest.mark.asyncio
    async def test_already_valid_wav_no_conversion(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = EnsureWavStep()
        ctx = await step.process(ctx)
        assert ctx.was_step_applied("ensure_wav")
        # Valid 16kHz mono WAV should not create temp files
        assert len(ctx.temp_files) == 0 or ctx.audio["path"] == str(p)

    @pytest.mark.asyncio
    async def test_idempotent_second_call(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = EnsureWavStep()
        ctx = await step.process(ctx)
        initial_path = ctx.audio["path"]
        ctx = await step.process(ctx)  # second call
        assert ctx.audio["path"] == initial_path


# ── VADTrimStep ───────────────────────────────────────────────────────

class TestVADTrimStep:
    @pytest.mark.asyncio
    async def test_disabled_is_noop(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = VADTrimStep(enabled=False)
        ctx = await step.process(ctx)
        assert ctx.was_step_applied("vad_trim")
        assert ctx.vad_result is None
        assert ctx.audio["path"] == str(p)

    @pytest.mark.asyncio
    async def test_silent_wav_no_trim(self, tmp_path):
        """WAV de silencio puro: VAD no sugiere recorte porque no hay voz."""
        p = tmp_path / "silent.wav"
        _make_wav(str(p), duration_ms=1000)
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = VADTrimStep(enabled=True)
        ctx = await step.process(ctx)
        assert ctx.was_step_applied("vad_trim")
        # Silencio puro: no hay segmentos de voz → sin trim
        if ctx.vad_result:
            assert ctx.vad_result.trim_suggestion is None or ctx.audio["path"] == str(p)

    @pytest.mark.asyncio
    async def test_idempotent_second_call(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = VADTrimStep(enabled=False)
        ctx = await step.process(ctx)
        path_after_first = ctx.audio["path"]
        ctx = await step.process(ctx)
        assert ctx.audio["path"] == path_after_first


# ── QualityCheckStep ──────────────────────────────────────────────────

class TestQualityCheckStep:
    @pytest.mark.asyncio
    async def test_runs_without_error(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = QualityCheckStep()
        ctx = await step.process(ctx)
        assert ctx.was_step_applied("quality_check")

    @pytest.mark.asyncio
    async def test_idempotent(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = QualityCheckStep()
        ctx = await step.process(ctx)
        first_result = ctx.quality_result
        ctx = await step.process(ctx)  # second call
        assert ctx.quality_result is first_result


# ── AudioProcessingChain ──────────────────────────────────────────────

class TestAudioProcessingChain:
    @pytest.mark.asyncio
    async def test_default_chain_runs_all_steps(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        chain = AudioProcessingChain.default(vad_enabled=False)
        ctx = await chain.process(ctx)
        assert ctx.was_step_applied("ensure_wav")
        assert ctx.was_step_applied("vad_trim")
        assert ctx.was_step_applied("quality_check")

    @pytest.mark.asyncio
    async def test_steps_run_in_order(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        chain = AudioProcessingChain.default(vad_enabled=False)
        ctx = await chain.process(ctx)
        expected_order = ["ensure_wav", "vad_trim", "quality_check"]
        for expected, applied in zip(expected_order, ctx.steps_applied):
            assert expected == applied

    @pytest.mark.asyncio
    async def test_empty_chain(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        chain = AudioProcessingChain(steps=[])
        ctx = await chain.process(ctx)
        assert ctx.steps_applied == []

    @pytest.mark.asyncio
    async def test_minimal_chain(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        chain = AudioProcessingChain.minimal()
        ctx = await chain.process(ctx)
        assert ctx.was_step_applied("ensure_wav")
        assert not ctx.was_step_applied("quality_check")
