"""Audio streaming buffer con detección de silencio.

Módulo para procesamiento de audio en tiempo real con buffer acumulativo
y detección de pausas usando VAD (Voice Activity Detection).

Uso:
    buffer = AudioBuffer(on_segment_ready=callback, silence_timeout_ms=1000)
    buffer.add_chunk(audio_bytes)  # Llamar repetidamente con chunks de audio
    buffer.flush()  # Forzar procesamiento del buffer actual
"""
from __future__ import annotations

import asyncio
import io
import logging
import struct
import tempfile
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, List, Optional

logger = logging.getLogger(__name__)

# Constantes por defecto
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_SAMPLE_WIDTH = 2  # 16-bit audio
DEFAULT_SILENCE_TIMEOUT_MS = 1000  # 1 segundo de silencio
DEFAULT_ENERGY_THRESHOLD = 0.01
DEFAULT_FRAME_MS = 30
DEFAULT_MAX_BUFFER_SECONDS = 30


@dataclass
class StreamConfig:
    """Configuración del buffer de streaming."""
    
    sample_rate: int = DEFAULT_SAMPLE_RATE
    channels: int = DEFAULT_CHANNELS
    sample_width: int = DEFAULT_SAMPLE_WIDTH
    silence_timeout_ms: int = DEFAULT_SILENCE_TIMEOUT_MS
    energy_threshold: float = DEFAULT_ENERGY_THRESHOLD
    frame_ms: int = DEFAULT_FRAME_MS
    max_buffer_seconds: int = DEFAULT_MAX_BUFFER_SECONDS


@dataclass
class AudioSegment:
    """Segmento de audio listo para procesamiento."""
    
    audio_path: Path
    duration_ms: int
    speech_ratio: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class StreamState:
    """Estado actual del buffer de streaming."""
    
    is_speaking: bool = False
    volume_level: float = 0.0  # 0.0 a 1.0
    buffer_duration_ms: int = 0
    last_speech_time: float = 0.0
    status: str = "idle"  # idle, listening, speaking, processing


# Tipo para callback de segmento listo
SegmentCallback = Callable[[AudioSegment], Awaitable[None]]
StateCallback = Callable[[StreamState], Awaitable[None]]


class AudioBuffer:
    """Buffer de audio con detección de silencio para streaming.
    
    Acumula chunks de audio y detecta pausas para determinar cuándo
    un segmento está completo y listo para procesamiento.
    
    Features:
    - Detección de volumen en tiempo real
    - Detección de voz/silencio por energía
    - Callback cuando se detecta pausa de 1+ segundo
    - Estado observable para UI
    """
    
    def __init__(
        self,
        on_segment_ready: Optional[SegmentCallback] = None,
        on_state_change: Optional[StateCallback] = None,
        config: Optional[StreamConfig] = None,
    ) -> None:
        self._config = config or StreamConfig()
        self._on_segment_ready = on_segment_ready
        self._on_state_change = on_state_change
        
        # Buffer de audio acumulado
        self._chunks: List[bytes] = []
        self._total_bytes = 0
        
        # Estado de VAD
        self._is_speaking = False
        self._last_speech_time = 0.0
        self._silence_start_time: Optional[float] = None
        
        # Volumen actual (para UI)
        self._current_volume = 0.0
        
        # Control de procesamiento
        self._processing_lock = asyncio.Lock()
        self._silence_timer: Optional[asyncio.Task] = None
    
    @property
    def state(self) -> StreamState:
        """Obtener estado actual del buffer."""
        buffer_bytes = self._total_bytes
        bytes_per_ms = (self._config.sample_rate * 
                       self._config.sample_width * 
                       self._config.channels) / 1000
        
        return StreamState(
            is_speaking=self._is_speaking,
            volume_level=self._current_volume,
            buffer_duration_ms=int(buffer_bytes / bytes_per_ms) if bytes_per_ms > 0 else 0,
            last_speech_time=self._last_speech_time,
            status=self._get_status(),
        )
    
    def _get_status(self) -> str:
        """Determinar status actual."""
        if self._silence_timer and not self._silence_timer.done():
            return "processing"
        if self._is_speaking:
            return "speaking"
        if self._total_bytes > 0:
            return "listening"
        return "idle"
    
    async def add_chunk(self, audio_data: bytes) -> StreamState:
        """Agregar un chunk de audio al buffer.
        
        Args:
            audio_data: Bytes de audio PCM 16-bit
            
        Returns:
            Estado actual del buffer
        """
        if not audio_data:
            return self.state
        
        self._chunks.append(audio_data)
        self._total_bytes += len(audio_data)
        
        # Calcular volumen y detectar voz
        volume, is_speech = self._analyze_chunk(audio_data)
        self._current_volume = volume
        
        now = time.time()
        
        if is_speech:
            self._is_speaking = True
            self._last_speech_time = now
            self._silence_start_time = None
            
            # Cancelar timer de silencio si existe
            if self._silence_timer and not self._silence_timer.done():
                self._silence_timer.cancel()
                self._silence_timer = None
        else:
            # Detectar inicio de silencio
            if self._is_speaking and self._silence_start_time is None:
                self._silence_start_time = now
            
            # Verificar si pasó el timeout de silencio
            if (self._silence_start_time and 
                self._total_bytes > 0 and
                (now - self._silence_start_time) * 1000 >= self._config.silence_timeout_ms):
                # Iniciar procesamiento asíncrono
                if self._silence_timer is None or self._silence_timer.done():
                    self._silence_timer = asyncio.create_task(self._process_segment())
        
        # Verificar máximo de buffer
        max_bytes = (self._config.max_buffer_seconds * 
                    self._config.sample_rate * 
                    self._config.sample_width * 
                    self._config.channels)
        
        if self._total_bytes >= max_bytes:
            logger.warning("Buffer máximo alcanzado, forzando procesamiento")
            await self._process_segment()
        
        # Notificar cambio de estado
        current_state = self.state
        if self._on_state_change:
            await self._on_state_change(current_state)
        
        return current_state
    
    def _analyze_chunk(self, audio_data: bytes) -> tuple[float, bool]:
        """Analizar chunk para volumen y detección de voz.
        
        Returns:
            Tuple de (volumen normalizado 0-1, es_voz bool)
        """
        if len(audio_data) < 2:
            return 0.0, False
        
        # Calcular RMS
        try:
            n_samples = len(audio_data) // self._config.sample_width
            if n_samples == 0:
                return 0.0, False
            
            fmt = f"<{n_samples}h"
            samples = struct.unpack(fmt, audio_data[:n_samples * 2])
            
            sum_sq = sum(s * s for s in samples)
            rms = (sum_sq / n_samples) ** 0.5
            
            # Normalizar a 0-1 (16-bit max = 32767)
            volume = min(1.0, rms / 32767.0 * 10)  # x10 para mejor visualización
            
            # Detectar voz por umbral de energía
            # Umbral absoluto mínimo para 16-bit
            is_speech = rms > 100 and (rms / 32767.0) > self._config.energy_threshold
            
            return volume, is_speech
            
        except (struct.error, ZeroDivisionError):
            return 0.0, False
    
    async def _process_segment(self) -> None:
        """Procesar el buffer actual como un segmento completo."""
        async with self._processing_lock:
            if not self._chunks or self._total_bytes == 0:
                return
            
            # Guardar audio a archivo temporal
            audio_data = b"".join(self._chunks)
            audio_path = await self._save_to_wav(audio_data)
            
            # Calcular duración
            bytes_per_ms = (self._config.sample_rate * 
                          self._config.sample_width * 
                          self._config.channels) / 1000
            duration_ms = int(len(audio_data) / bytes_per_ms) if bytes_per_ms > 0 else 0
            
            # Estimar speech ratio (simplificado)
            speech_ratio = 0.8 if self._is_speaking else 0.2
            
            # Crear segmento
            segment = AudioSegment(
                audio_path=audio_path,
                duration_ms=duration_ms,
                speech_ratio=speech_ratio,
            )
            
            # Limpiar buffer
            self._chunks.clear()
            self._total_bytes = 0
            self._is_speaking = False
            self._silence_start_time = None
            
            logger.info(f"Segmento listo: {duration_ms}ms, speech_ratio={speech_ratio:.2f}")
            
            # Notificar callback
            if self._on_segment_ready:
                try:
                    await self._on_segment_ready(segment)
                except Exception as e:
                    logger.error(f"Error en callback de segmento: {e}")
    
    async def _save_to_wav(self, audio_data: bytes) -> Path:
        """Guardar audio PCM a archivo WAV temporal."""
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav",
            prefix="realtime_",
        ) as tmp:
            tmp_path = Path(tmp.name)
        
        # Escribir WAV
        with wave.open(str(tmp_path), "wb") as w:
            w.setnchannels(self._config.channels)
            w.setsampwidth(self._config.sample_width)
            w.setframerate(self._config.sample_rate)
            w.writeframes(audio_data)
        
        return tmp_path
    
    async def flush(self) -> Optional[AudioSegment]:
        """Forzar procesamiento del buffer actual.
        
        Útil cuando el usuario termina de grabar manualmente.
        
        Returns:
            AudioSegment si había datos, None si buffer vacío
        """
        if self._silence_timer and not self._silence_timer.done():
            self._silence_timer.cancel()
        
        if self._total_bytes > 0:
            await self._process_segment()
            return None  # El callback ya fue llamado
        return None
    
    def reset(self) -> None:
        """Limpiar buffer sin procesar."""
        if self._silence_timer and not self._silence_timer.done():
            self._silence_timer.cancel()
        
        self._chunks.clear()
        self._total_bytes = 0
        self._is_speaking = False
        self._silence_start_time = None
        self._current_volume = 0.0


__all__ = [
    "AudioBuffer",
    "AudioSegment",
    "StreamConfig",
    "StreamState",
    "SegmentCallback",
    "StateCallback",
]
