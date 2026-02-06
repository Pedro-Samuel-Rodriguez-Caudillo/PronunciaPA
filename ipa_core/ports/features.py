"""Puerto FeatureExtractor (audio -> tensores).

Define la interfaz para convertir audio crudo en features (espectrogramas)
que consumen los modelos acústicos.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ipa_core.types import AudioInput

if TYPE_CHECKING:
    import numpy as np

@runtime_checkable
class FeatureExtractor(Protocol):
    """Contrato para extracción de características de audio."""
    
    async def extract(self, audio: AudioInput) -> np.ndarray:
        """Convierte audio en un tensor de características (e.g., MelSpectrogram).
        
        Retorna un array numpy con shape (batch, channels, time) o similar.
        """
        ...
