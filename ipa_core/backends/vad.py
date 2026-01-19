"""Voice Activity Detection (VAD) para preprocesamiento de audio.

Proporciona detección de voz, recorte de silencios y métricas
de calidad para mejorar el input del ASR.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

import numpy as np

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin

if TYPE_CHECKING:
    pass


# Carga diferida de torch y Silero VAD
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None  # type: ignore


@dataclass
class SpeechSegment:
    """Segmento de voz detectado.
    
    Atributos
    ---------
    start : float
        Tiempo de inicio en segundos.
    end : float
        Tiempo de fin en segundos.
    confidence : float
        Confianza de la detección (0-1).
    """
    start: float
    end: float
    confidence: float = 1.0
    
    @property
    def duration(self) -> float:
        """Duración del segmento en segundos."""
        return self.end - self.start
    
    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "duration": self.duration,
        }


@dataclass
class VADResult:
    """Resultado del análisis VAD.
    
    Atributos
    ---------
    segments : list[SpeechSegment]
        Segmentos de voz detectados.
    speech_ratio : float
        Ratio de tiempo con voz vs total (0-1).
    total_duration : float
        Duración total del audio en segundos.
    speech_duration : float
        Duración total de voz en segundos.
    """
    segments: List[SpeechSegment]
    speech_ratio: float
    total_duration: float
    speech_duration: float
    
    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "segments": [s.to_dict() for s in self.segments],
            "speech_ratio": self.speech_ratio,
            "total_duration": self.total_duration,
            "speech_duration": self.speech_duration,
            "segment_count": len(self.segments),
        }


class SileroVAD(BasePlugin):
    """VAD basado en el modelo Silero VAD.
    
    Parámetros
    ----------
    threshold : float
        Umbral de probabilidad para detectar voz (0-1).
    min_speech_duration : float
        Duración mínima de segmento de voz en segundos.
    min_silence_duration : float
        Duración mínima de silencio para separar segmentos.
    sample_rate : int
        Frecuencia de muestreo esperada (16000 o 8000).
    """
    
    def __init__(
        self,
        *,
        threshold: float = 0.5,
        min_speech_duration: float = 0.1,
        min_silence_duration: float = 0.3,
        sample_rate: int = 16000,
    ) -> None:
        self._threshold = threshold
        self._min_speech_duration = min_speech_duration
        self._min_silence_duration = min_silence_duration
        self._sample_rate = sample_rate
        self._model = None
        self._ready = False
    
    async def setup(self) -> None:
        """Cargar el modelo Silero VAD."""
        if not TORCH_AVAILABLE:
            raise NotReadyError(
                "PyTorch no instalado. Ejecuta: pip install torch"
            )
        
        def load_model():
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True,
            )
            return model, utils
        
        loop = asyncio.get_event_loop()
        self._model, self._utils = await loop.run_in_executor(None, load_model)
        self._ready = True
    
    async def teardown(self) -> None:
        """Liberar recursos."""
        self._model = None
        self._ready = False
    
    async def detect_speech(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> VADResult:
        """Detectar segmentos de voz en el audio.
        
        Parámetros
        ----------
        audio : np.ndarray
            Array de audio (mono, float32, normalizado a [-1, 1]).
        sample_rate : int
            Frecuencia de muestreo del audio.
            
        Retorna
        -------
        VADResult
            Resultado con segmentos detectados y métricas.
        """
        if not self._ready or self._model is None:
            raise NotReadyError("SileroVAD no inicializado.")
        
        # Resample si es necesario
        if sample_rate != self._sample_rate:
            audio = self._resample(audio, sample_rate, self._sample_rate)
        
        # Convertir a tensor
        audio_tensor = torch.from_numpy(audio).float()
        
        # Obtener timestamps usando get_speech_timestamps
        get_speech_ts = self._utils[0]
        
        def run_vad():
            return get_speech_ts(
                audio_tensor,
                self._model,
                sampling_rate=self._sample_rate,
                threshold=self._threshold,
                min_speech_duration_ms=int(self._min_speech_duration * 1000),
                min_silence_duration_ms=int(self._min_silence_duration * 1000),
            )
        
        loop = asyncio.get_event_loop()
        speech_timestamps = await loop.run_in_executor(None, run_vad)
        
        # Convertir a SpeechSegments
        segments = []
        for ts in speech_timestamps:
            start = ts['start'] / self._sample_rate
            end = ts['end'] / self._sample_rate
            segments.append(SpeechSegment(start=start, end=end))
        
        # Calcular métricas
        total_duration = len(audio) / self._sample_rate
        speech_duration = sum(s.duration for s in segments)
        speech_ratio = speech_duration / total_duration if total_duration > 0 else 0.0
        
        return VADResult(
            segments=segments,
            speech_ratio=speech_ratio,
            total_duration=total_duration,
            speech_duration=speech_duration,
        )
    
    async def trim_silence(
        self,
        audio: np.ndarray,
        sample_rate: int,
        *,
        padding: float = 0.1,
    ) -> Tuple[np.ndarray, VADResult]:
        """Recortar silencios al inicio y final del audio.
        
        Parámetros
        ----------
        audio : np.ndarray
            Audio de entrada.
        sample_rate : int
            Frecuencia de muestreo.
        padding : float
            Padding adicional en segundos a mantener.
            
        Retorna
        -------
        tuple[np.ndarray, VADResult]
            Audio recortado y resultado VAD.
        """
        vad_result = await self.detect_speech(audio, sample_rate)
        
        if not vad_result.segments:
            # No se detectó voz, retornar audio original
            return audio, vad_result
        
        # Encontrar inicio y fin de voz
        first_segment = vad_result.segments[0]
        last_segment = vad_result.segments[-1]
        
        # Calcular índices con padding
        start_sample = max(0, int((first_segment.start - padding) * sample_rate))
        end_sample = min(len(audio), int((last_segment.end + padding) * sample_rate))
        
        trimmed_audio = audio[start_sample:end_sample]
        return trimmed_audio, vad_result
    
    def _resample(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int,
    ) -> np.ndarray:
        """Resamplear audio a la frecuencia objetivo."""
        if orig_sr == target_sr:
            return audio
        
        # Resampleo simple por interpolación lineal
        duration = len(audio) / orig_sr
        target_length = int(duration * target_sr)
        indices = np.linspace(0, len(audio) - 1, target_length)
        return np.interp(indices, np.arange(len(audio)), audio)


class SimpleVAD(BasePlugin):
    """VAD simple basado en energía (sin dependencias externas).
    
    Útil para testing y como fallback cuando Silero no está disponible.
    """
    
    def __init__(
        self,
        *,
        energy_threshold: float = 0.01,
        min_speech_duration: float = 0.1,
    ) -> None:
        self._energy_threshold = energy_threshold
        self._min_speech_duration = min_speech_duration
        self._ready = False
    
    async def setup(self) -> None:
        """Inicializar (no requiere carga de modelo)."""
        self._ready = True
    
    async def teardown(self) -> None:
        """Liberar recursos."""
        self._ready = False
    
    async def detect_speech(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> VADResult:
        """Detectar voz basándose en energía del audio."""
        if not self._ready:
            raise NotReadyError("SimpleVAD no inicializado.")
        
        # Calcular energía por ventanas
        window_size = int(0.02 * sample_rate)  # 20ms
        hop_size = int(0.01 * sample_rate)  # 10ms
        
        segments = []
        in_speech = False
        speech_start = 0.0
        
        for i in range(0, len(audio) - window_size, hop_size):
            window = audio[i:i + window_size]
            energy = np.sqrt(np.mean(window ** 2))
            time = i / sample_rate
            
            if energy > self._energy_threshold:
                if not in_speech:
                    speech_start = time
                    in_speech = True
            else:
                if in_speech:
                    duration = time - speech_start
                    if duration >= self._min_speech_duration:
                        segments.append(SpeechSegment(
                            start=speech_start,
                            end=time,
                        ))
                    in_speech = False
        
        # Cerrar último segmento si quedó abierto
        if in_speech:
            end_time = len(audio) / sample_rate
            duration = end_time - speech_start
            if duration >= self._min_speech_duration:
                segments.append(SpeechSegment(
                    start=speech_start,
                    end=end_time,
                ))
        
        total_duration = len(audio) / sample_rate
        speech_duration = sum(s.duration for s in segments)
        speech_ratio = speech_duration / total_duration if total_duration > 0 else 0.0
        
        return VADResult(
            segments=segments,
            speech_ratio=speech_ratio,
            total_duration=total_duration,
            speech_duration=speech_duration,
        )


__all__ = [
    "SpeechSegment",
    "VADResult",
    "SileroVAD",
    "SimpleVAD",
    "TORCH_AVAILABLE",
]
