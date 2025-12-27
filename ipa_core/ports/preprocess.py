"""Puerto Preprocessor (audio/tokens -> normalización).

Patrón sugerido
---------------
- Chain of Responsibility: permite encadenar pasos simples de normalización.
- Template Method: define un esqueleto de pasos que pueden especializarse.

TODO
----
- Acordar si se hace un recorte básico del audio (VAD simple) en `process_audio`.
- Documentar un orden recomendado para normalizar tokens (espacios, casing, IPA).
- Garantizar que `normalize_tokens` sea idempotente (llamar dos veces no cambia el resultado).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ipa_core.types import AudioInput, PreprocessorResult, TokenSeq


@runtime_checkable
class Preprocessor(Protocol):
    """Define operaciones simples para preparar audio y tokens.

    Separar audio y tokens facilita pruebas y reemplazos puntuales.
    Debe soportar el ciclo de vida de `BasePlugin`.
    """

    async def setup(self) -> None:
        """Configuración inicial del plugin (asíncrona)."""
        ...

    async def teardown(self) -> None:
        """Limpieza de recursos del plugin (asíncrona)."""
        ...

    async def process_audio(self, audio: AudioInput, **kw) -> PreprocessorResult:  # noqa: D401
        """Normalizar/validar formato del audio (SR, canales, contenedor).

        Retorna `PreprocessorResult` con la clave `audio` poblada.
        """
        ...

    async def normalize_tokens(self, tokens: TokenSeq, **kw) -> PreprocessorResult:  # noqa: D401
        """Normalizar tokens IPA (espacios, casing y símbolos).

        Retorna `PreprocessorResult` con la clave `tokens` poblada.
        """
        ...