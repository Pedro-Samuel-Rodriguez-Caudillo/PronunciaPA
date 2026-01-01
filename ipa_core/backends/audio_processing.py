"""Procesamiento de audio usando Librosa.

Implementa la extracción de características acústicas para modelos ONNX.
"""
import numpy as np
from ipa_core.types import AudioInput
try:
    import librosa
except ImportError:
    librosa = None

class LibrosaFeatureExtractor:
    """Extractor de características usando Librosa (MelSpectrogram)."""
    
    def __init__(self, sample_rate: int = 16000, n_mels: int = 80):
        if librosa is None:
            raise ImportError("librosa is required for LibrosaFeatureExtractor")
        self.sample_rate = sample_rate
        self.n_mels = n_mels

    async def extract(self, audio: AudioInput) -> np.ndarray:
        """Carga y procesa el audio a un log-mel spectrogram."""
        # TODO: Handle 'microphone' input separately or assume path is a file for now
        path = str(audio["path"])
        
        # Cargar audio
        y, _ = librosa.load(path, sr=self.sample_rate)
        
        # Calcular Mel Spectrogram
        mels = librosa.feature.melspectrogram(y=y, sr=self.sample_rate, n_mels=self.n_mels)
        
        # Log-scale (dB)
        log_mels = librosa.power_to_db(mels, ref=np.max)
        
        # Añadir dimensión de batch: (1, n_mels, time)
        return log_mels[np.newaxis, ...]
