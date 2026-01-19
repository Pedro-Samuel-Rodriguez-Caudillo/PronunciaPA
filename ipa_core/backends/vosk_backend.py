"""Backend de ASR ligero usando Vosk.

Vosk es más ligero que Wav2Vec2 y funciona bien en dispositivos
con recursos limitados. Soporta múltiples idiomas.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ipa_core.plugins.base import BasePlugin
from ipa_core.ports.asr import ASRBackend, ASRResult
from ipa_core.types import AudioInput


logger = logging.getLogger(__name__)


# Modelos Vosk disponibles (descargables desde alphacephei.com/vosk/models)
VOSK_MODELS: Dict[str, str] = {
    "en-us": "vosk-model-en-us-0.22",
    "en-us-small": "vosk-model-small-en-us-0.15",
    "es": "vosk-model-small-es-0.42",
    "es-small": "vosk-model-small-es-0.42",
}


class VoskBackend(BasePlugin, ASRBackend):
    """Backend de ASR usando Vosk.
    
    Vosk es más ligero y rápido que Wav2Vec2, pero produce
    texto en lugar de IPA. Requiere post-procesamiento G2P.
    
    Parámetros
    ----------
    model_path : Path
        Ruta al modelo Vosk descargado.
    sample_rate : int
        Frecuencia de muestreo (16000 recomendado).
    """
    
    def __init__(
        self,
        *,
        model_path: Path,
        sample_rate: int = 16000,
    ) -> None:
        self._model_path = Path(model_path)
        self._sample_rate = sample_rate
        self._model = None
        self._recognizer = None
        self._ready = False
    
    async def setup(self) -> None:
        """Cargar modelo Vosk."""
        try:
            from vosk import Model, KaldiRecognizer
        except ImportError as e:
            raise ImportError(
                "VoskBackend requires 'vosk'. Install with: pip install vosk"
            ) from e
        
        if not self._model_path.exists():
            raise FileNotFoundError(f"Vosk model not found: {self._model_path}")
        
        logger.info(f"Loading Vosk model from: {self._model_path}")
        
        self._model = Model(str(self._model_path))
        self._recognizer = KaldiRecognizer(self._model, self._sample_rate)
        self._recognizer.SetWords(True)  # Incluir timestamps
        
        self._ready = True
        logger.info("Vosk model loaded")
    
    async def teardown(self) -> None:
        """Liberar modelo."""
        self._model = None
        self._recognizer = None
        self._ready = False
    
    async def transcribe(
        self,
        audio: AudioInput,
        *,
        lang: Optional[str] = None,
        **kw: Any,
    ) -> ASRResult:
        """Transcribir audio a texto.
        
        Nota: Vosk produce texto, no IPA. Requiere G2P post-processing.
        """
        if not self._ready:
            raise RuntimeError("VoskBackend not initialized. Call setup() first.")
        
        # Cargar audio
        audio_data = self._load_audio(audio)
        
        # Reconocer
        from vosk import KaldiRecognizer
        self._recognizer = KaldiRecognizer(self._model, self._sample_rate)
        
        if self._recognizer.AcceptWaveform(audio_data):
            result = json.loads(self._recognizer.Result())
        else:
            result = json.loads(self._recognizer.PartialResult())
        
        text = result.get("text", "")
        words = result.get("result", [])
        
        # Vosk produce texto, no tokens IPA
        # El servicio debe usar G2P para convertir
        return {
            "tokens": [],  # Vacío - requiere G2P
            "raw_text": text,
            "segments": [
                {
                    "text": w["word"],
                    "start": w.get("start", 0),
                    "end": w.get("end", 0),
                }
                for w in words
            ],
            "meta": {
                "backend": "vosk",
                "model_path": str(self._model_path),
                "requires_g2p": True,
            },
        }
    
    def _load_audio(self, audio: AudioInput) -> bytes:
        """Cargar audio como bytes."""
        import wave
        
        if isinstance(audio, dict) and "path" in audio:
            path = audio["path"]
            with wave.open(path, "rb") as wf:
                return wf.readframes(wf.getnframes())
        
        raise ValueError(f"VoskBackend requires audio path, got: {type(audio)}")


__all__ = ["VoskBackend", "VOSK_MODELS"]
