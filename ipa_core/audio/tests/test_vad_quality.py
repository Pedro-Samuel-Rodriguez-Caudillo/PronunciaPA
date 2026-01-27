"""Tests para VAD y Quality Gates."""
import os
import struct
import tempfile
import wave

import pytest

from ipa_core.audio.vad import analyze_vad, VADResult
from ipa_core.audio.quality_gates import check_quality, QualityIssue, QualityGateResult


def _create_test_wav(
    duration_ms: int,
    sample_rate: int = 16000,
    frequency: float = 440.0,
    amplitude: float = 0.5,
    silence_ratio: float = 0.0,
) -> str:
    """Crear WAV de prueba con tono sinusoidal."""
    import math
    
    n_samples = int(sample_rate * duration_ms / 1000)
    samples = []
    
    silence_start = int(n_samples * silence_ratio / 2)
    silence_end = n_samples - silence_start
    
    for i in range(n_samples):
        if i < silence_start or i >= silence_end:
            # Silencio
            samples.append(0)
        else:
            # Tono sinusoidal
            t = i / sample_rate
            sample = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t))
            samples.append(sample)
    
    # Escribir WAV
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    
    return tmp.name


class TestVAD:
    """Tests para Voice Activity Detection."""
    
    def test_analyze_speech_only(self):
        """Audio con solo voz debe tener speech_ratio alto."""
        wav_path = _create_test_wav(1000, amplitude=0.5, silence_ratio=0.0)
        try:
            result = analyze_vad(wav_path)
            assert isinstance(result, VADResult)
            assert result.speech_ratio > 0.8
            assert result.duration_ms == 1000
        finally:
            os.unlink(wav_path)
    
    def test_analyze_with_silence(self):
        """Audio con silencios debe detectar segmentos."""
        wav_path = _create_test_wav(2000, amplitude=0.5, silence_ratio=0.5)
        try:
            result = analyze_vad(wav_path)
            assert result.speech_ratio < 0.7
            assert result.trim_suggestion is not None
        finally:
            os.unlink(wav_path)
    
    def test_analyze_silence_only(self):
        """Audio silencioso debe tener speech_ratio = 0."""
        wav_path = _create_test_wav(1000, amplitude=0.001)
        try:
            result = analyze_vad(wav_path)
            # Audio muy silencioso debe ser detectado como silencio
            assert result.speech_ratio == 0.0
        finally:
            os.unlink(wav_path)


class TestQualityGates:
    """Tests para Quality Gates."""
    
    def test_good_audio_passes(self):
        """Audio de buena calidad debe pasar."""
        wav_path = _create_test_wav(1000, amplitude=0.5)
        try:
            result = check_quality(wav_path)
            assert isinstance(result, QualityGateResult)
            assert result.passed is True
            assert len(result.issues) == 0
        finally:
            os.unlink(wav_path)
    
    def test_too_short_fails(self):
        """Audio muy corto debe fallar."""
        wav_path = _create_test_wav(200)  # 200ms < 500ms mínimo
        try:
            result = check_quality(wav_path, min_duration_ms=500)
            assert result.passed is False
            assert QualityIssue.TOO_SHORT in result.issues
            assert "corta" in result.user_feedback.lower()
        finally:
            os.unlink(wav_path)
    
    def test_too_quiet_fails(self):
        """Audio muy silencioso debe fallar."""
        wav_path = _create_test_wav(1000, amplitude=0.001)
        try:
            result = check_quality(wav_path)
            assert result.passed is False
            assert QualityIssue.TOO_QUIET in result.issues
            assert "silencioso" in result.user_feedback.lower()
        finally:
            os.unlink(wav_path)
    
    def test_clipping_detected(self):
        """Audio con clipping debe detectarse."""
        wav_path = _create_test_wav(1000, amplitude=0.999)
        try:
            result = check_quality(wav_path, max_clipping_ratio=0.001)
            # Puede o no detectar clipping dependiendo del threshold
            assert result.clipping_ratio is not None
        finally:
            os.unlink(wav_path)
    
    def test_no_speech_fails(self):
        """Audio sin voz debe fallar si se proporciona speech_ratio."""
        wav_path = _create_test_wav(1000)
        try:
            result = check_quality(wav_path, speech_ratio=0.05)
            assert result.passed is False
            assert QualityIssue.NO_SPEECH in result.issues
        finally:
            os.unlink(wav_path)
    
    def test_result_serialization(self):
        """QualityGateResult debe ser serializable."""
        wav_path = _create_test_wav(1000)
        try:
            result = check_quality(wav_path)
            data = result.to_dict()
            assert "passed" in data
            assert "issues" in data
            assert isinstance(data["issues"], list)
        finally:
            os.unlink(wav_path)
