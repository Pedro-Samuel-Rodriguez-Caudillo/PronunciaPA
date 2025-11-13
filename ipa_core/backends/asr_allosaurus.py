"""Backend ASR basado en Allosaurus."""
from __future__ import annotations

from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.ports.asr import ASRBackend
from ipa_core.types import ASRResult, AudioInput

try:  # Carga diferida para evitar fallos en entornos sin el modelo.
    from allosaurus.app import read_recognizer
except ImportError:  # pragma: no cover
    read_recognizer = None  # type: ignore[assignment]

# Mapeo de códigos ISO 639-1 (2 letras) a ISO 639-3 (3 letras) que usa Allosaurus
LANG_MAP = {
    "es": "spa",  # Español
    "en": "eng",  # Inglés
    "fr": "fra",  # Francés
    "de": "deu",  # Alemán
    "it": "ita",  # Italiano
    "pt": "por",  # Portugués
    "zh": "cmn",  # Chino mandarín
    "ja": "jpn",  # Japonés
    "ko": "kor",  # Coreano
    "ar": "ara",  # Árabe
}


class AllosaurusASR:
    """Implementación de `ASRBackend` usando el modelo Allosaurus."""

    def __init__(self, params: Optional[dict[str, Any]] = None, *, recognizer: Any | None = None) -> None:
        params = params or {}
        self._default_lang: str = params.get("lang", "eng")
        self._model_dir: Optional[str] = params.get("model_dir")
        self._recognizer = recognizer or self._load()

    def _load(self) -> Any:
        if read_recognizer is None:
            raise NotReadyError("Allosaurus no está instalado. Usa `pip install ipa-core[dev]`.")
        # Allosaurus 1.0.x no acepta model_dir como keyword argument
        if self._model_dir:
            return read_recognizer(self._model_dir)
        return read_recognizer()

    def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult:  # noqa: D401
        path = audio.get("path")
        if not path:
            raise ValidationError("AudioInput requiere 'path'")

        current_lang = lang or self._default_lang
        # Convertir código de idioma a formato ISO 639-3 si es necesario
        allosaurus_lang = LANG_MAP.get(current_lang, current_lang)
        # Allosaurus 1.0.x: recognize(path, lang_id) - lang_id es posicional
        raw: str = self._recognizer.recognize(path, allosaurus_lang)  # type: ignore[attr-defined]
        tokens = [tok for tok in raw.strip().split() if tok]
        return {"tokens": tokens, "meta": {"backend": "allosaurus", "lang": current_lang}}


__all__ = ["AllosaurusASR"]
