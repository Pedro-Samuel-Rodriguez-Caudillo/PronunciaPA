"""Tests para AudioProcessingChain y sus pasos."""
from __future__ import annotations

import os
import wave
import tempfile
import struct
import pytest

from ipa_core.audio.processing_chain import (
    AGCStep,
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

    def test_trim_only_clips_tail_keeps_start_intact(self, tmp_path):
        """_trim_wav con start_ms=0 NO debe insertar silencio artificial al inicio.

        VADTrimStep siempre llama _trim_wav(path, 0, end_ms) para conservar
        el inicio original del audio y proteger plosivas sordas (/p/, /t/, /k/)
        que el VAD de energía puede detectar tarde.
        """
        import os
        import struct
        import wave

        # WAV con tono para que los primeros bytes no sean silencio
        p = tmp_path / "tone.wav"
        _make_wav_with_tone(str(p), duration_ms=1000, amplitude=1000)

        # Leer las primeras muestras del original para comparar
        with wave.open(str(p), "rb") as wf_orig:
            sr = wf_orig.getframerate()
            sw = wf_orig.getsampwidth()
            n_check = int(0.050 * sr)  # primeros 50 ms
            orig_head = wf_orig.readframes(n_check)

        end_ms = 800
        result_path = VADTrimStep._trim_wav(str(p), 0, end_ms)
        assert result_path is not None, "_trim_wav debe retornar una ruta"

        try:
            with wave.open(result_path, "rb") as wf_out:
                out_head = wf_out.readframes(n_check)
                n_frames_out = wf_out.getnframes()

            # El inicio del recorte coincide exactamente con el original
            assert out_head == orig_head, (
                "Los primeros 50 ms del audio recortado deben coincidir con el original; "
                "si no coinciden, se está inyectando silencio artificial al inicio"
            )

            # La duración del resultado es ~end_ms (±1 frame de tolerancia)
            expected_frames = int(end_ms * sr / 1000)
            assert abs(n_frames_out - expected_frames) <= 1, (
                f"Esperado ~{expected_frames} frames, obtenido {n_frames_out}"
            )
        finally:
            os.unlink(result_path)


# ── QualityCheckStep ──────────────────────────────────────────────────
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
        assert ctx.was_step_applied("agc")
        assert ctx.was_step_applied("vad_trim")
        assert ctx.was_step_applied("quality_check")

    @pytest.mark.asyncio
    async def test_steps_run_in_order(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        chain = AudioProcessingChain.default(vad_enabled=False)
        ctx = await chain.process(ctx)
        expected_order = ["ensure_wav", "agc", "vad_trim", "quality_check"]
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


# ── AGCStep ───────────────────────────────────────────────────────────

def _make_wav_with_tone(path: str, amplitude: int = 1000, duration_ms: int = 500, sample_rate: int = 16000) -> None:
    """Crear WAV con tono sinusoidal para probar AGC."""
    import math
    n_frames = int(sample_rate * duration_ms / 1000)
    samples = [int(amplitude * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(n_frames)]
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *samples))


class TestAGCStep:
    @pytest.mark.asyncio
    async def test_disabled_is_noop(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = AGCStep(enabled=False)
        ctx = await step.process(ctx)
        assert ctx.was_step_applied("agc")
        assert ctx.audio["path"] == str(p)

    @pytest.mark.asyncio
    async def test_silent_wav_no_gain(self, tmp_path):
        """WAV de silencio: AGC no aplica ganancia (RMS < 1.0)."""
        p = tmp_path / "silent.wav"
        _make_wav(str(p))  # silencio puro
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = AGCStep(enabled=True)
        ctx = await step.process(ctx)
        assert ctx.was_step_applied("agc")
        assert ctx.meta.get("agc", {}).get("applied") is False
        ctx.cleanup()

    @pytest.mark.asyncio
    async def test_tone_wav_may_apply_gain(self, tmp_path):
        """WAV con tono: AGC puede crear archivo temporal."""
        p = tmp_path / "tone.wav"
        _make_wav_with_tone(str(p), amplitude=500)
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = AGCStep(enabled=True, target_dbfs=-20.0)
        ctx = await step.process(ctx)
        assert ctx.was_step_applied("agc")
        ctx.cleanup()

    @pytest.mark.asyncio
    async def test_idempotent(self, tmp_path):
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = AGCStep(enabled=True)
        ctx = await step.process(ctx)
        path_after_first = ctx.audio["path"]
        ctx = await step.process(ctx)  # segunda llamada
        assert ctx.audio["path"] == path_after_first


# ── VADTrimStep backend selection ─────────────────────────────────────

class TestVADTrimStepBackend:
    """Tests para el parámetro `backend` de VADTrimStep."""

    @pytest.mark.asyncio
    async def test_energy_backend_runs(self, tmp_path):
        """backend='energy' usa el VAD de energía clásico sin Silero."""
        p = tmp_path / "test.wav"
        _make_wav(str(p), duration_ms=1000)
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = VADTrimStep(enabled=True, backend="energy")
        ctx = await step.process(ctx)
        assert ctx.was_step_applied("vad_trim")

    @pytest.mark.asyncio
    async def test_auto_backend_falls_back_to_energy_when_silero_unavailable(
        self, tmp_path, monkeypatch
    ):
        """backend='auto' cae al VAD de energía si silero_vad no está instalado."""
        import ipa_core.audio.vad as vad_module

        # Forzar que _get_silero_model lance ImportError
        def _raise_import(*args, **kwargs):
            raise ImportError("silero-vad no instalado (mock)")

        monkeypatch.setattr(vad_module, "_get_silero_model", _raise_import)
        # Reset cached availability so our mock is hit
        monkeypatch.setattr(vad_module, "_SILERO_AVAILABLE", None)

        p = tmp_path / "test.wav"
        _make_wav(str(p), duration_ms=1000)
        ctx = AudioContext(audio=_audio_input(str(p)))
        step = VADTrimStep(enabled=True, backend="auto")
        ctx = await step.process(ctx)
        assert ctx.was_step_applied("vad_trim")

    @pytest.mark.asyncio
    async def test_silero_backend_uses_model(self, tmp_path, monkeypatch):
        """backend='silero' llama a analyze_vad_silero (mockeado)."""
        import ipa_core.audio.vad as vad_module

        # Mock Silero model + helpers
        _fake_timestamps = [{"start": 3200, "end": 12800}]  # 200ms–800ms a 16kHz
        _fake_wav = [0.0] * 16000  # 1 segundo de muestras float

        class _FakeTensor:
            def __len__(self):
                return 16000

        monkeypatch.setattr(vad_module, "_SILERO_AVAILABLE", True)
        monkeypatch.setattr(vad_module, "_SILERO_MODEL", object())

        import sys
        import types

        silero_mod = types.ModuleType("silero_vad")

        def _read_audio(path, sampling_rate=16000):
            return _fake_wav

        def _get_ts(wav, model, **kwargs):
            return _fake_timestamps

        setattr(silero_mod, "read_audio", _read_audio)
        setattr(silero_mod, "get_speech_timestamps", _get_ts)
        setattr(silero_mod, "load_silero_vad", lambda: object())
        sys.modules["silero_vad"] = silero_mod

        try:
            p = tmp_path / "test.wav"
            _make_wav(str(p), duration_ms=1000)
            ctx = AudioContext(audio=_audio_input(str(p)))
            step = VADTrimStep(enabled=True, backend="silero")
            ctx = await step.process(ctx)
            assert ctx.was_step_applied("vad_trim")
        finally:
            sys.modules.pop("silero_vad", None)

    @pytest.mark.asyncio
    async def test_default_chain_accepts_vad_backend_param(self, tmp_path):
        """AudioProcessingChain.default() acepta vad_backend='energy'."""
        p = tmp_path / "test.wav"
        _make_wav(str(p))
        ctx = AudioContext(audio=_audio_input(str(p)))
        chain = AudioProcessingChain.default(vad_enabled=True, vad_backend="energy")
        ctx = await chain.process(ctx)
        assert ctx.was_step_applied("vad_trim")
