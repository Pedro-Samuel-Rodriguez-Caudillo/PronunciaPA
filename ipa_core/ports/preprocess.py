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

from typing import Protocol

from ipa_core.types import AudioInput, Token, TokenSeq


class Preprocessor(Protocol):
    """Define operaciones simples para preparar audio y tokens.

    Separar audio y tokens facilita pruebas y reemplazos puntuales.
    """

    def process_audio(self, audio: AudioInput) -> AudioInput:  # noqa: D401
        """Normalizar/validar formato del audio (SR, canales, contenedor)."""
        ...

    def normalize_tokens(self, tokens: TokenSeq) -> list[Token]:  # noqa: D401
        """Normalizar tokens IPA (espacios, casing y símbolos)."""
        ...
