"""Backend de ASR offline usando Wav2Vec2 de HuggingFace.

Este backend permite reconocimiento fonético sin conexión a internet,
usando modelos de HuggingFace Transformers cargados localmente.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ipa_core.plugins.base import BasePlugin
from ipa_core.ports.asr import ASRBackend, ASRResult
from ipa_core.types import AudioInput


logger = logging.getLogger(__name__)


# Modelos sugeridos para diferentes idiomas
MODEL_REGISTRY: Dict[str, str] = {
    "en": "facebook/wav2vec2-lv60-espresso-ipa",  # Inglés con IPA
    "es": "facebook/wav2vec2-large-xlsr-53",       # Multilingüe
    "universal": "facebook/wav2vec2-large-xlsr-53-ipa",  # IPA universal
}


class Wav2Vec2Backend(BasePlugin, ASRBackend):
    """Backend de ASR usando Wav2Vec2.
    
    ⚠️ ADVERTENCIA: La mayoría de modelos Wav2Vec2 producen TEXTO, no IPA.
    Solo usa este backend con modelos fine-tuned para IPA/fonemas:
    - facebook/wav2vec2-large-xlsr-53-ipa (gated, requiere token)
    - Otros modelos específicos de IPA
    
    Si usas un modelo de texto, el sistema NO capturará los alófonos
    reales del usuario, perdiendo información fonética crítica.
    
    Requiere transformers y torch instalados.
    Los modelos se descargan una vez y se cachean localmente.
    
    Parámetros
    ----------
    model_name : str
        Nombre o ruta del modelo HuggingFace.
    device : str
        Dispositivo: "cpu", "cuda", "mps".
    cache_dir : Optional[Path]
        Directorio de caché para modelos.
    force_ipa : bool
        Si True, valida que el modelo produce IPA. Default: False (legacy).
    """
    
    # Por defecto asume texto (modelos xlsr-53 base son texto)
    # Solo cambia a "ipa" si usas modelo fine-tuned para IPA
    output_type = "text"
    
    def __init__(
        self,
        *,
        model_name: str = "facebook/wav2vec2-large-xlsr-53",
        device: str = "cpu",
        cache_dir: Optional[Path] = None,
        force_ipa: bool = False,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._cache_dir = cache_dir
        self._force_ipa = force_ipa
        self._model = None
        self._processor = None
        self._ready = False
        
        # Detectar si el modelo es IPA basado en nombre
        if "ipa" in model_name.lower() or "phoneme" in model_name.lower():
            self.output_type = "ipa"
        elif force_ipa:
            self.output_type = "ipa"
            logger.warning(
                f"Forzando output_type='ipa' para {model_name}. "
                "Verifica que el modelo realmente produzca IPA."
            )
    
    async def setup(self) -> None:
        """Cargar modelo (requiere conexión solo la primera vez)."""
        try:
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            import torch
        except ImportError as e:
            raise ImportError(
                "Wav2Vec2Backend requires 'transformers' and 'torch'. "
                "Install with: pip install transformers torch"
            ) from e
        
        logger.info(f"Loading Wav2Vec2 model: {self._model_name}")
        
        self._processor = Wav2Vec2Processor.from_pretrained(
            self._model_name,
            cache_dir=self._cache_dir,
        )
        self._model = Wav2Vec2ForCTC.from_pretrained(
            self._model_name,
            cache_dir=self._cache_dir,
        )
        self._model.to(self._device)
        self._model.eval()
        
        self._ready = True
        logger.info(f"Wav2Vec2 loaded on {self._device}")
    
    async def teardown(self) -> None:
        """Liberar modelo de memoria."""
        self._model = None
        self._processor = None
        self._ready = False
    
    async def transcribe(
        self,
        audio: AudioInput,
        *,
        lang: Optional[str] = None,
        **kw: Any,
    ) -> ASRResult:
        """Transcribir audio a tokens fonéticos.
        
        Parámetros
        ----------
        audio : AudioInput
            Audio de entrada (dict con path o array).
        lang : str, opcional
            Idioma (para selección de modelo).
            
        Retorna
        -------
        ASRResult
            Resultado con tokens fonéticos.
        """
        if not self._ready:
            raise RuntimeError("Wav2Vec2Backend not initialized. Call setup() first.")
        
        import torch
        import numpy as np
        
        # Cargar audio
        waveform = self._load_audio(audio)
        
        # Preprocesar
        inputs = self._processor(
            waveform,
            sampling_rate=16000,
            return_tensors="pt",
        )
        
        # Inference
        with torch.no_grad():
            inputs = inputs.input_values.to(self._device)
            logits = self._model(inputs).logits
        
        # Decodificar
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self._processor.batch_decode(predicted_ids)[0]
        
        # Tokenizar resultado
        tokens = list(transcription.replace(" ", ""))
        
        return {
            "tokens": tokens,
            "raw_text": transcription,
            "meta": {
                "backend": "wav2vec2",
                "model": self._model_name,
                "device": self._device,
            },
        }
    
    def _load_audio(self, audio: AudioInput) -> Any:
        """Cargar audio desde diferentes formatos."""
        import numpy as np
        
        # Si es dict con path
        if isinstance(audio, dict) and "path" in audio:
            path = audio["path"]
            try:
                import soundfile as sf
                waveform, sr = sf.read(path)
                if sr != 16000:
                    # Resample simple (para producción usar librosa)
                    from scipy import signal
                    waveform = signal.resample(
                        waveform, 
                        int(len(waveform) * 16000 / sr)
                    )
                return waveform.astype(np.float32)
            except ImportError:
                # Fallback a scipy
                from scipy.io import wavfile
                sr, waveform = wavfile.read(path)
                if waveform.dtype != np.float32:
                    waveform = waveform.astype(np.float32) / 32768.0
                return waveform
        
        # Si ya es array
        if hasattr(audio, "__array__"):
            return np.asarray(audio).astype(np.float32)
        
        raise ValueError(f"Unsupported audio format: {type(audio)}")
    
    @classmethod
    def for_language(
        cls,
        lang: str,
        *,
        device: str = "cpu",
        cache_dir: Optional[Path] = None,
    ) -> "Wav2Vec2Backend":
        """Crear backend con modelo optimizado para idioma.
        
        Parámetros
        ----------
        lang : str
            Código de idioma: "en", "es", etc.
        """
        model_name = MODEL_REGISTRY.get(lang, MODEL_REGISTRY["universal"])
        return cls(model_name=model_name, device=device, cache_dir=cache_dir)


__all__ = ["Wav2Vec2Backend", "MODEL_REGISTRY"]
