"""Puerto ASR (audio -> IPA tokens).

Patrón sugerido
---------------
- Strategy: permite cambiar de backend (Whisper, Kaldi, etc.) sin modificar
  el resto del sistema.

TODO
----
- Acordar qué ocurre cuando `lang` es `None` (usar autodetección básica o
  requerir idioma explícito).
- Definir un conjunto mínimo de metadatos en `ASRResult.meta` (modelo, versión,
  fecha de inferencia) para facilitar depuración.
- Documentar expectativas de latencia (no implementar streaming aún, solo
  clarificar el futuro comportamiento para que el diseño lo soporte).
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from ipa_core.types import ASRResult, AudioInput


@runtime_checkable
class ASRBackend(Protocol):
    """Define el contrato de un backend de reconocimiento de voz.

    Un backend recibe un `AudioInput` y devuelve un `ASRResult` con tokens IPA.
    """

    def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult:  # noqa: D401
        """Transcribir audio a tokens IPA.

        Parámetros
        ----------
        audio: AudioInput
            Descripción del archivo de audio a transcribir.
        lang: Optional[str]
            Idioma objetivo (por ejemplo, "es"). Si es None, seguir la política
            documentada en los TODOs.

        Retorna
        -------
        ASRResult
            Tokens IPA y metadatos para depuración.
        """
        ...
