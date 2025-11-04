"""Puerto ASR (audio -> IPA tokens).

Patrón de diseño
----------------
- Strategy: múltiples implementaciones intercambiables (e.g., Whisper, Kaldi).

TODO (Issue #18)
----------------
- Establecer contrato de latencia/tiempo real para streaming en el futuro.
- Definir metadatos mínimos en `ASRResult.meta` (versión del modelo, idioma).
- Especificar comportamiento cuando `lang` es `None` (auto-detección o error).
"""
from __future__ import annotations

from typing import Optional, Protocol

from ipa_core.types import ASRResult, AudioInput


class ASRBackend(Protocol):
    def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult:  # noqa: D401
        """Transcribe audio y retorna tokens IPA normalizados."""
        ...
