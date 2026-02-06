"""Backend ASR basado en Allosaurus para reconocimiento fonético.

Allosaurus es un modelo de reconocimiento fonético multilingüe
que produce transcripciones IPA directamente desde audio.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.types import ASRResult, AudioInput

if TYPE_CHECKING:
    pass


# Carga diferida de Allosaurus
# Nota: panphon (dependencia) puede fallar en Python < 3.10 con TypeError
try:
    from allosaurus.app import read_recognizer
    ALLOSAURUS_AVAILABLE = True
except (ImportError, TypeError) as e:
    ALLOSAURUS_AVAILABLE = False
    read_recognizer = None  # type: ignore
    _ALLOSAURUS_ERROR = str(e)


class AllosaurusBackend(BasePlugin):
    """Backend ASR usando Allosaurus para transcripción fonética.
    
    Allosaurus es un reconocedor fonético universal que produce
    tokens IPA directamente sin necesidad de G2P intermedio.
    
    Parámetros
    ----------
    model_name : str
        Nombre del modelo a usar. Default: "uni2005" (universal).
    lang : str | None
        Código de idioma para restringir el inventario fonético.
        Si es None, usa el inventario universal.
    device : str
        Dispositivo de inferencia: "cpu" o "cuda".
    emit_timestamps : bool
        Si True, intenta obtener timestamps por token.
    """
    
    # Declara que este backend produce IPA directo
    output_type = "ipa"
    
    # Mapeo de códigos ISO a códigos Allosaurus
    _LANG_MAP = {
        "en": "eng",
        "es": "spa",
        "fr": "fra",
        "de": "deu",
        "it": "ita",
        "pt": "por",
        "zh": "cmn",
        "ja": "jpn",
        "ko": "kor",
        "ar": "ara",
        "ru": "rus",
    }
    
    def __init__(
        self,
        *,
        model_name: str = "uni2005",
        lang: Optional[str] = None,
        device: str = "cpu",
        emit_timestamps: bool = False,
    ) -> None:
        super().__init__()
        self._model_name = model_name
        self._lang = lang
        self._device = device
        self._emit_timestamps = emit_timestamps
        self._model = None
        self._ready = False
    
    async def setup(self) -> None:
        """Cargar el modelo de Allosaurus."""
        if not ALLOSAURUS_AVAILABLE:
            raise NotReadyError(
                "Allosaurus no instalado. Ejecuta: pip install allosaurus"
            )
        
        # Cargar modelo en un thread para no bloquear
        def load_model():
            return read_recognizer(self._model_name)
        
        loop = asyncio.get_event_loop()
        self._model = await loop.run_in_executor(None, load_model)
        self._ready = True
    
    async def teardown(self) -> None:
        """Liberar recursos del modelo."""
        self._model = None
        self._ready = False
    
    def _resolve_lang(self, lang: Optional[str]) -> Optional[str]:
        """Resolver código de idioma a formato Allosaurus."""
        if lang is None:
            return self._lang
        
        resolved = lang or self._lang
        if resolved:
            return self._LANG_MAP.get(resolved, resolved)
        return None
    
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
            Diccionario con path, sample_rate y channels.
        lang : str | None
            Código de idioma para restringir inventario.
            
        Retorna
        -------
        ASRResult
            Tokens IPA y metadatos.
        """
        if not self._ready or self._model is None:
            raise NotReadyError("AllosaurusBackend no inicializado. Llama setup() primero.")
        
        audio_path = Path(audio["path"])
        if not audio_path.exists():
            raise ValidationError(f"Archivo de audio no existe: {audio_path}")
        
        resolved_lang = self._resolve_lang(lang)
        
        # Ejecutar reconocimiento en thread separado
        def recognize():
            if resolved_lang:
                return self._model.recognize(
                    str(audio_path),
                    lang_id=resolved_lang,
                    timestamp=self._emit_timestamps,
                )
            else:
                return self._model.recognize(
                    str(audio_path),
                    timestamp=self._emit_timestamps,
                )
        
        loop = asyncio.get_event_loop()
        raw_output = await loop.run_in_executor(None, recognize)
        
        # Parsear salida
        tokens, timestamps = self._parse_output(raw_output)
        
        return {
            "tokens": tokens,
            "raw_text": raw_output if isinstance(raw_output, str) else " ".join(tokens),
            "time_stamps": timestamps,
            "meta": {
                "model": self._model_name,
                "lang": resolved_lang,
                "device": self._device,
            },
        }
    
    def _parse_output(
        self,
        output: Any,
    ) -> tuple[list[str], Optional[list[tuple[float, float]]]]:
        """Parsear la salida de Allosaurus.
        
        Allosaurus puede retornar:
        - str: "p a l a b r a" (tokens separados por espacio)
        - list: [(start, end, phone), ...] si timestamp=True
        """
        if isinstance(output, str):
            # Formato simple: tokens separados por espacio
            tokens = [t.strip() for t in output.split() if t.strip()]
            return tokens, None
        
        if isinstance(output, list):
            # Formato con timestamps
            tokens = []
            timestamps = []
            for item in output:
                if len(item) >= 3:
                    start, end, phone = item[0], item[1], item[2]
                    tokens.append(str(phone).strip())
                    timestamps.append((float(start), float(end)))
            return tokens, timestamps if timestamps else None
        
        # Fallback
        return [], None


class AllosaurusBackendStub(BasePlugin):
    """Stub de Allosaurus para testing sin modelo real.
    
    Retorna tokens predefinidos para pruebas unitarias.
    """
    output_type = "ipa"
    
    def __init__(
        self,
        *,
        mock_tokens: Optional[list[str]] = None,
        mock_timestamps: Optional[list[tuple[float, float]]] = None,
    ) -> None:
        self._mock_tokens = mock_tokens or ["h", "ɛ", "l", "oʊ"]
        self._mock_timestamps = mock_timestamps
        self._ready = False
    
    async def setup(self) -> None:
        """Simular carga de modelo."""
        self._ready = True
    
    async def teardown(self) -> None:
        """Simular liberación de recursos."""
        self._ready = False
    
    async def transcribe(
        self,
        audio: AudioInput,
        *,
        lang: Optional[str] = None,
        **kw: Any,
    ) -> ASRResult:
        """Retornar tokens mock."""
        if not self._ready:
            raise NotReadyError("Stub no inicializado.")
        
        return {
            "tokens": self._mock_tokens,
            "raw_text": " ".join(self._mock_tokens),
            "time_stamps": self._mock_timestamps,
            "meta": {
                "model": "stub",
                "lang": lang,
            },
        }


__all__ = [
    "AllosaurusBackend",
    "AllosaurusBackendStub",
    "ALLOSAURUS_AVAILABLE",
]
