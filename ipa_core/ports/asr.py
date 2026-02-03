"""Puerto ASR (audio -> IPA tokens).

Patrón sugerido
---------------
- Strategy: permite cambiar de backend (Whisper, Kaldi, etc.) sin modificar
  el resto del sistema.

Comportamiento de `lang=None`
-----------------------------
Cuando el parámetro `lang` es `None`, el backend DEBE:
1. Usar el idioma por defecto de la configuración (`options.lang`)
2. Si no hay configuración, usar "en" como fallback universal
3. NO intentar autodetección de idioma (añade latencia y complejidad)

Metadatos mínimos en ASRResult.meta
-----------------------------------
Todo backend DEBE incluir en `meta`:
- `backend`: Nombre del backend (ej: "allosaurus", "onnx")
- `model`: Identificador del modelo usado
- `lang`: Idioma efectivo usado para la transcripción

Metadatos opcionales recomendados:
- `version`: Versión del modelo
- `latency_ms`: Tiempo de inferencia en milisegundos
- `confidence`: Score de confianza promedio (si disponible)

Latencia esperada (no streaming)
--------------------------------
Modo actual: síncrono por archivo completo
- Target: < 3x RTF (real-time factor) para archivos < 30 segundos
- Streaming: NO implementado aún, diseño preparado para futuro
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from ipa_core.types import ASRResult, AudioInput


@runtime_checkable
class ASRBackend(Protocol):
    """Define el contrato de un backend de reconocimiento de voz.

    Un backend recibe un `AudioInput` y devuelve un `ASRResult` con tokens IPA.
    Debe soportar el ciclo de vida de `BasePlugin` (setup/teardown).
    
    Attributes
    ----------
    output_type : Literal["ipa", "text", "none"]
        REQUERIDO. Indica si el backend produce IPA directo ("ipa"),
        texto que requiere G2P ("text"), o ninguno ("none").
        El kernel rechaza backends con output_type != "ipa" por defecto.
    """
    
    output_type: str  # Should be Literal["ipa", "text", "none"] in implementations

    async def setup(self) -> None:
        """Configuración inicial del plugin (asíncrona)."""
        ...

    async def teardown(self) -> None:
        """Limpieza de recursos del plugin (asíncrona)."""
        ...

    async def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult:  # noqa: D401
        """Transcribir audio a tokens IPA.

        Parámetros
        ----------
        audio : AudioInput
            Descripción del archivo de audio a transcribir.
        lang : Optional[str]
            Idioma objetivo (por ejemplo, "es"). Si es None, usa el idioma
            por defecto de la configuración, o "en" como último fallback.

        Retorna
        -------
        ASRResult
            Tokens IPA y metadatos para depuración.
            
        Metadatos requeridos en ASRResult.meta
        --------------------------------------
        - backend: str - Nombre del backend
        - model: str - Identificador del modelo
        - lang: str - Idioma usado efectivamente
        """
        ...