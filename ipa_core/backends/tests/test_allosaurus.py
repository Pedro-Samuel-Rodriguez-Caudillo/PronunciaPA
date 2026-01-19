"""Tests para el backend Allosaurus."""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import wave
import struct

from ipa_core.backends.allosaurus_backend import (
    AllosaurusBackend,
    AllosaurusBackendStub,
    ALLOSAURUS_AVAILABLE,
)
from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.types import AudioInput


def create_test_wav(path: Path, duration_sec: float = 0.5) -> Path:
    """Crear archivo WAV de prueba con tono sinusoidal."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)
    
    with wave.open(str(path), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            # Generar tono 440 Hz
            import math
            value = int(32767 * 0.5 * math.sin(2 * math.pi * 440 * i / sample_rate))
            wav_file.writeframes(struct.pack('<h', value))
    
    return path


class TestAllosaurusBackendStub:
    """Tests para el stub de Allosaurus."""
    
    @pytest.fixture
    def stub(self) -> AllosaurusBackendStub:
        """Stub con tokens predefinidos."""
        return AllosaurusBackendStub(
            mock_tokens=["h", "ɛ", "l", "oʊ"],
            mock_timestamps=[(0.0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4)],
        )
    
    @pytest.fixture
    def audio_input(self, tmp_path: Path) -> AudioInput:
        """Audio de prueba."""
        wav_path = create_test_wav(tmp_path / "test.wav")
        return {
            "path": str(wav_path),
            "sample_rate": 16000,
            "channels": 1,
        }
    
    @pytest.mark.asyncio
    async def test_stub_not_ready_before_setup(self, stub: AllosaurusBackendStub, audio_input: AudioInput) -> None:
        """Stub falla si no se llama setup."""
        with pytest.raises(NotReadyError):
            await stub.transcribe(audio_input)
    
    @pytest.mark.asyncio
    async def test_stub_ready_after_setup(self, stub: AllosaurusBackendStub, audio_input: AudioInput) -> None:
        """Stub funciona después de setup."""
        await stub.setup()
        result = await stub.transcribe(audio_input)
        assert result["tokens"] == ["h", "ɛ", "l", "oʊ"]
    
    @pytest.mark.asyncio
    async def test_stub_returns_timestamps(self, stub: AllosaurusBackendStub, audio_input: AudioInput) -> None:
        """Stub retorna timestamps configurados."""
        await stub.setup()
        result = await stub.transcribe(audio_input)
        assert result["time_stamps"] is not None
        assert len(result["time_stamps"]) == 4
    
    @pytest.mark.asyncio
    async def test_stub_teardown(self, stub: AllosaurusBackendStub, audio_input: AudioInput) -> None:
        """Teardown deja el stub en estado no listo."""
        await stub.setup()
        await stub.teardown()
        with pytest.raises(NotReadyError):
            await stub.transcribe(audio_input)
    
    @pytest.mark.asyncio
    async def test_stub_meta_includes_lang(self, stub: AllosaurusBackendStub, audio_input: AudioInput) -> None:
        """Meta incluye el idioma solicitado."""
        await stub.setup()
        result = await stub.transcribe(audio_input, lang="en")
        assert result["meta"]["lang"] == "en"


class TestAllosaurusBackend:
    """Tests para el backend real de Allosaurus."""
    
    @pytest.mark.skipif(
        not ALLOSAURUS_AVAILABLE,
        reason="Allosaurus no instalado"
    )
    @pytest.mark.asyncio
    async def test_backend_requires_setup(self, tmp_path: Path) -> None:
        """Backend real falla sin setup."""
        backend = AllosaurusBackend()
        audio_input: AudioInput = {
            "path": str(tmp_path / "test.wav"),
            "sample_rate": 16000,
            "channels": 1,
        }
        with pytest.raises(NotReadyError):
            await backend.transcribe(audio_input)
    
    def test_lang_mapping(self) -> None:
        """Mapeo de códigos de idioma funciona."""
        backend = AllosaurusBackend()
        assert backend._resolve_lang("en") == "eng"
        assert backend._resolve_lang("es") == "spa"
        assert backend._resolve_lang("unknown") == "unknown"
    
    def test_parse_output_string(self) -> None:
        """Parseo de salida en formato string."""
        backend = AllosaurusBackend()
        tokens, timestamps = backend._parse_output("h ɛ l oʊ")
        assert tokens == ["h", "ɛ", "l", "oʊ"]
        assert timestamps is None
    
    def test_parse_output_list(self) -> None:
        """Parseo de salida con timestamps."""
        backend = AllosaurusBackend()
        output = [
            (0.0, 0.1, "h"),
            (0.1, 0.2, "ɛ"),
            (0.2, 0.3, "l"),
            (0.3, 0.4, "oʊ"),
        ]
        tokens, timestamps = backend._parse_output(output)
        assert tokens == ["h", "ɛ", "l", "oʊ"]
        assert timestamps == [(0.0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4)]
    
    def test_parse_output_empty(self) -> None:
        """Parseo de salida vacía."""
        backend = AllosaurusBackend()
        tokens, timestamps = backend._parse_output("")
        assert tokens == []
        assert timestamps is None


class TestAllosaurusAvailability:
    """Tests para verificar disponibilidad de Allosaurus."""
    
    def test_availability_flag_exists(self) -> None:
        """El flag de disponibilidad existe."""
        assert isinstance(ALLOSAURUS_AVAILABLE, bool)
