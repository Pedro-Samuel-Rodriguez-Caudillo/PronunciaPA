"""Puerto FeatureExtractor (audio -> tensores).

Define la interfaz para convertir audio crudo en features (espectrogramas)
que consumen los modelos acústicos.
"""
from typing import Protocol, runtime_checkable
import numpy as np
from ipa_core.types import AudioInput

@runtime_checkable
class FeatureExtractor(Protocol):
    """Contrato para extracción de características de audio."""
    
    async def extract(self, audio: AudioInput) -> np.ndarray:
        """Convierte audio en un tensor de características (e.g., MelSpectrogram).
        
        Retorna un array numpy con shape (batch, channels, time) o similar.
        """
        ...
