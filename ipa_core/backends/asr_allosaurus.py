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
        return read_recognizer(model_dir=self._model_dir)

    def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult:  # noqa: D401
        path = audio.get("path")
        if not path:
            raise ValidationError("AudioInput requiere 'path'")

        current_lang = lang or self._default_lang
        raw: str = self._recognizer.recognize(path, lang=current_lang)  # type: ignore[attr-defined]
        tokens = [tok for tok in raw.strip().split() if tok]
        return {"tokens": tokens, "meta": {"backend": "allosaurus", "lang": current_lang}}


__all__ = ["AllosaurusASR"]
