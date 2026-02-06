"""Backend unificado de ASR con salida IPA.

Soporta múltiples engines:
- allosaurus: Universal, 200+ idiomas, CPU friendly (DEFAULT)
- wav2vec2-ipa: Alta precisión, requiere GPU/token HF
- xlsr-ipa: Multilingüe (128 idiomas), buen balance precisión/velocidad

Todos producen IPA directamente, no texto.
"""
from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Union

from ipa_core.plugins.base import BasePlugin
from ipa_core.types import ASRResult, AudioInput

logger = logging.getLogger(__name__)


class ASREngine(str, Enum):
    """Motores ASR disponibles con salida IPA."""
    ALLOSAURUS = "allosaurus"
    WAV2VEC2_IPA = "wav2vec2-ipa"
    XLSR_IPA = "xlsr-ipa"


# Modelos HuggingFace para cada engine
ENGINE_MODELS: Dict[ASREngine, str] = {
    ASREngine.WAV2VEC2_IPA: "facebook/wav2vec2-lv60-espresso-ipa",
    ASREngine.XLSR_IPA: "facebook/wav2vec2-xls-r-300m-phoneme",
}


class UnifiedIPABackend(BasePlugin):
    """Backend unificado que soporta múltiples engines IPA.
    
    Permite cambiar entre Allosaurus, Wav2Vec2-IPA y XLS-R IPA
    sin cambiar el código del cliente.
    
    Parámetros
    ----------
    engine : Union[str, ASREngine]
        Motor a usar: "allosaurus", "wav2vec2-ipa", "xlsr-ipa"
    device : str
        Dispositivo: "cpu", "cuda", "mps" (solo para transformers)
    cache_dir : Optional[Path]
        Directorio de caché para modelos HuggingFace
    allosaurus_lang : str
        Modelo de idioma para Allosaurus (default: "uni2005")
    
    Ejemplo
    -------
    >>> backend = UnifiedIPABackend(engine="allosaurus")
    >>> await backend.setup()
    >>> result = await backend.transcribe({"path": "audio.wav"}, lang="es")
    >>> print(result["tokens"])  # ['o', 'l', 'a']
    """
    
    output_type = "ipa"  # Siempre IPA
    
    def __init__(
        self,
        *,
        engine: Union[str, ASREngine] = ASREngine.ALLOSAURUS,
        device: str = "cpu",
        cache_dir: Optional[Path] = None,
        allosaurus_lang: str = "uni2005",
    ) -> None:
        super().__init__()
        if isinstance(engine, str):
            engine = ASREngine(engine)
        
        self._engine = engine
        self._device = device
        self._cache_dir = cache_dir
        self._allosaurus_lang = allosaurus_lang
        
        # Backend interno
        self._backend: Any = None
        self._model: Any = None  # Inicializar para evitar atributos no definidos
        self._processor: Any = None  # Inicializar para evitar atributos no definidos
        self._ready = False
    
    @property
    def engine_name(self) -> str:
        return self._engine.value
    
    async def setup(self) -> None:
        """Inicializar el backend seleccionado."""
        if self._engine == ASREngine.ALLOSAURUS:
            await self._setup_allosaurus()
        else:
            await self._setup_transformers()
        
        self._ready = True
        logger.info(f"UnifiedIPABackend ready: engine={self._engine.value}")
    
    async def _setup_allosaurus(self) -> None:
        """Configurar backend Allosaurus."""
        try:
            from allosaurus.app import read_recognizer
        except ImportError as e:
            raise ImportError(
                "Allosaurus not installed. Run: pip install allosaurus"
            ) from e
        
        logger.info(f"Loading Allosaurus model: {self._allosaurus_lang}")
        self._backend = read_recognizer(self._allosaurus_lang)
        logger.info("Allosaurus ready")
    
    async def _setup_transformers(self) -> None:
        """Configurar backend Transformers (Wav2Vec2-IPA o XLS-R IPA)."""
        try:
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            import torch
        except ImportError as e:
            raise ImportError(
                "transformers/torch not installed. Run: pip install transformers torch"
            ) from e
        
        model_name = ENGINE_MODELS[self._engine]
        logger.info(f"Loading {self._engine.value} model: {model_name}")
        
        # Detectar dispositivo óptimo
        if self._device == "auto":
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
        
        self._processor = Wav2Vec2Processor.from_pretrained(
            model_name,
            cache_dir=self._cache_dir,
        )
        self._model = Wav2Vec2ForCTC.from_pretrained(
            model_name,
            cache_dir=self._cache_dir,
        )
        self._model.to(self._device)
        self._model.eval()
        
        self._backend = "transformers"
        logger.info(f"{self._engine.value} ready on {self._device}")
    
    async def teardown(self) -> None:
        """Liberar recursos."""
        self._backend = None
        if hasattr(self, "_model"):
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
        """Transcribir audio a tokens IPA.
        
        Parámetros
        ----------
        audio : AudioInput
            Audio de entrada (dict con path o array)
        lang : str, opcional
            Idioma (usado por algunos backends)
            
        Retorna
        -------
        ASRResult
            tokens: Lista de fonemas IPA
            raw_text: Transcripción raw
            meta: Metadatos del backend
        """
        if not self._ready:
            raise RuntimeError("Backend not initialized. Call setup() first.")
        
        if self._engine == ASREngine.ALLOSAURUS:
            return await self._transcribe_allosaurus(audio, lang)
        else:
            return await self._transcribe_transformers(audio, lang)
    
    async def _transcribe_allosaurus(
        self, 
        audio: AudioInput, 
        lang: Optional[str]
    ) -> ASRResult:
        """Transcribir usando Allosaurus."""
        # Obtener path del audio
        if isinstance(audio, dict) and "path" in audio:
            audio_path = audio["path"]
        else:
            raise ValueError("Allosaurus requires audio with 'path' key")
        
        # Reconocer
        result = self._backend.recognize(audio_path)
        
        # Parsear tokens (Allosaurus devuelve "f o n e m a s")
        tokens = result.strip().split() if result else []
        
        return {
            "tokens": tokens,
            "raw_text": result,
            "meta": {
                "backend": "allosaurus",
                "engine": self._engine.value,
                "lang": lang,
            },
        }
    
    async def _transcribe_transformers(
        self, 
        audio: AudioInput, 
        lang: Optional[str]
    ) -> ASRResult:
        """Transcribir usando Transformers (Wav2Vec2-IPA o XLS-R)."""
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
        
        # Inferencia
        with torch.no_grad():
            inputs = inputs.input_values.to(self._device)
            logits = self._model(inputs).logits
        
        # Decodificar
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self._processor.batch_decode(predicted_ids)[0]
        
        # Tokenizar - separar por espacios o caracteres
        if " " in transcription:
            tokens = transcription.strip().split()
        else:
            tokens = list(transcription.strip())
        
        return {
            "tokens": tokens,
            "raw_text": transcription,
            "meta": {
                "backend": "transformers",
                "engine": self._engine.value,
                "model": ENGINE_MODELS[self._engine],
                "device": self._device,
                "lang": lang,
            },
        }
    
    def _load_audio(self, audio: AudioInput) -> Any:
        """Cargar audio desde diferentes formatos."""
        import numpy as np
        
        if isinstance(audio, dict) and "path" in audio:
            path = audio["path"]
            try:
                import soundfile as sf  # type: ignore
                # sf.read returns (data, samplerate) tuple
                read_result = sf.read(path)
                waveform = read_result[0]
                sr = read_result[1]
                if sr != 16000:
                    from scipy import signal  # type: ignore
                    waveform = signal.resample(
                        waveform, 
                        int(len(waveform) * 16000 / sr)
                    )
                # Ensure waveform is array after resampling
                waveform_array = np.asarray(waveform)
                return waveform_array.astype(np.float32)
            except ImportError:
                from scipy.io import wavfile
                # wavfile.read returns (sampling_rate: int, data: ndarray)
                read_result = wavfile.read(path)
                sr_int: int = read_result[0]
                waveform = read_result[1]
                
                # Ensure it's an array
                if not hasattr(waveform, 'dtype'):
                    waveform = np.array(waveform)
                if waveform.dtype != np.float32:
                    waveform = waveform.astype(np.float32) / 32768.0
                return waveform
        
        if hasattr(audio, "__array__"):
            return np.asarray(audio).astype(np.float32)
        
        raise ValueError(f"Unsupported audio format: {type(audio)}")
    
    @classmethod
    def available_engines(cls) -> List[str]:
        """Listar engines disponibles."""
        return [e.value for e in ASREngine]
    
    @classmethod
    def check_engine_ready(cls, engine: Union[str, ASREngine]) -> Dict[str, Any]:
        """Verificar si un engine está listo para usar.
        
        Retorna
        -------
        dict
            ready: bool
            missing: List[str] - dependencias faltantes
            message: str - descripción
        """
        if isinstance(engine, str):
            engine = ASREngine(engine)
        
        missing = []
        
        if engine == ASREngine.ALLOSAURUS:
            try:
                import allosaurus
            except ImportError:
                missing.append("allosaurus")
        else:
            try:
                import transformers
            except ImportError:
                missing.append("transformers")
            try:
                import torch
            except ImportError:
                missing.append("torch")
        
        return {
            "engine": engine.value,
            "ready": len(missing) == 0,
            "missing": missing,
            "message": f"Ready" if not missing else f"Missing: {', '.join(missing)}",
        }


def create_backend(engine: str = "allosaurus", **kwargs) -> UnifiedIPABackend:
    """Factory function para crear backend.
    
    Parámetros
    ----------
    engine : str
        Motor: "allosaurus", "wav2vec2-ipa", "xlsr-ipa"
    **kwargs
        Argumentos adicionales para el backend
        
    Ejemplo
    -------
    >>> backend = create_backend("xlsr-ipa", device="cuda")
    >>> await backend.setup()
    """
    return UnifiedIPABackend(engine=engine, **kwargs)


__all__ = [
    "ASREngine",
    "UnifiedIPABackend", 
    "create_backend",
    "ENGINE_MODELS",
]
