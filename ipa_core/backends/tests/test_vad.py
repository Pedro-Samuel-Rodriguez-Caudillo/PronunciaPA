"""Tests para el módulo VAD."""
from __future__ import annotations

import pytest
import numpy as np

from ipa_core.backends.vad import (
    SpeechSegment,
    VADResult,
    SimpleVAD,
    SileroVAD,
    TORCH_AVAILABLE,
)
from ipa_core.errors import NotReadyError


class TestSpeechSegment:
    """Tests para SpeechSegment."""
    
    def test_creation(self) -> None:
        """Verifica creación de segmento."""
        seg = SpeechSegment(start=1.0, end=2.5, confidence=0.9)
        assert seg.start == 1.0
        assert seg.end == 2.5
        assert seg.confidence == 0.9
    
    def test_duration(self) -> None:
        """Verifica cálculo de duración."""
        seg = SpeechSegment(start=1.0, end=3.5)
        assert seg.duration == 2.5
    
    def test_to_dict(self) -> None:
        """Verifica conversión a diccionario."""
        seg = SpeechSegment(start=0.0, end=1.0)
        d = seg.to_dict()
        assert "start" in d
        assert "end" in d
        assert "duration" in d


class TestVADResult:
    """Tests para VADResult."""
    
    def test_creation(self) -> None:
        """Verifica creación de resultado."""
        segments = [
            SpeechSegment(start=0.0, end=1.0),
            SpeechSegment(start=2.0, end=3.0),
        ]
        result = VADResult(
            segments=segments,
            speech_ratio=0.5,
            total_duration=4.0,
            speech_duration=2.0,
        )
        assert len(result.segments) == 2
        assert result.speech_ratio == 0.5
    
    def test_to_dict(self) -> None:
        """Verifica conversión a diccionario."""
        result = VADResult(
            segments=[SpeechSegment(start=0.0, end=1.0)],
            speech_ratio=0.5,
            total_duration=2.0,
            speech_duration=1.0,
        )
        d = result.to_dict()
        assert "segments" in d
        assert "speech_ratio" in d
        assert "segment_count" in d
        assert d["segment_count"] == 1


class TestSimpleVAD:
    """Tests para SimpleVAD."""
    
    @pytest.fixture
    def vad(self) -> SimpleVAD:
        """VAD simple para testing."""
        return SimpleVAD(energy_threshold=0.01, min_speech_duration=0.1)
    
    def create_audio_with_speech(
        self,
        duration: float = 2.0,
        sample_rate: int = 16000,
        speech_level: float = 0.5,
        noise_level: float = 0.001,
    ) -> np.ndarray:
        """Crear audio de prueba con segmento de voz simulado."""
        total_samples = int(duration * sample_rate)
        audio = np.random.randn(total_samples) * noise_level
        
        # Añadir "voz" en el medio (energía alta)
        speech_start = int(0.3 * sample_rate)
        speech_end = int(1.5 * sample_rate)
        audio[speech_start:speech_end] = np.random.randn(speech_end - speech_start) * speech_level
        
        return audio.astype(np.float32)
    
    @pytest.mark.asyncio
    async def test_not_ready_before_setup(self, vad: SimpleVAD) -> None:
        """VAD falla antes de setup."""
        audio = np.zeros(16000, dtype=np.float32)
        with pytest.raises(NotReadyError):
            await vad.detect_speech(audio, 16000)
    
    @pytest.mark.asyncio
    async def test_ready_after_setup(self, vad: SimpleVAD) -> None:
        """VAD funciona después de setup."""
        await vad.setup()
        audio = np.zeros(16000, dtype=np.float32)
        result = await vad.detect_speech(audio, 16000)
        assert isinstance(result, VADResult)
    
    @pytest.mark.asyncio
    async def test_detects_silence(self, vad: SimpleVAD) -> None:
        """Detecta silencio cuando no hay voz."""
        await vad.setup()
        # Audio muy silencioso
        audio = np.random.randn(16000) * 0.0001
        audio = audio.astype(np.float32)
        result = await vad.detect_speech(audio, 16000)
        assert result.speech_ratio < 0.1
    
    @pytest.mark.asyncio
    async def test_detects_speech(self, vad: SimpleVAD) -> None:
        """Detecta voz cuando hay energía."""
        await vad.setup()
        audio = self.create_audio_with_speech()
        result = await vad.detect_speech(audio, 16000)
        assert len(result.segments) > 0
        assert result.speech_ratio > 0
    
    @pytest.mark.asyncio
    async def test_teardown(self, vad: SimpleVAD) -> None:
        """Teardown deja VAD no listo."""
        await vad.setup()
        await vad.teardown()
        audio = np.zeros(16000, dtype=np.float32)
        with pytest.raises(NotReadyError):
            await vad.detect_speech(audio, 16000)


class TestSileroVAD:
    """Tests para SileroVAD."""
    
    @pytest.mark.skipif(
        not TORCH_AVAILABLE,
        reason="PyTorch no instalado"
    )
    @pytest.mark.asyncio
    async def test_not_ready_before_setup(self) -> None:
        """Silero VAD falla antes de setup."""
        vad = SileroVAD()
        audio = np.zeros(16000, dtype=np.float32)
        with pytest.raises(NotReadyError):
            await vad.detect_speech(audio, 16000)
    
    def test_init_params(self) -> None:
        """Verifica parámetros de inicialización."""
        vad = SileroVAD(
            threshold=0.7,
            min_speech_duration=0.2,
            sample_rate=8000,
        )
        assert vad._threshold == 0.7
        assert vad._min_speech_duration == 0.2
        assert vad._sample_rate == 8000


class TestTorchAvailability:
    """Tests para disponibilidad de PyTorch."""
    
    def test_flag_exists(self) -> None:
        """El flag de disponibilidad existe."""
        assert isinstance(TORCH_AVAILABLE, bool)
