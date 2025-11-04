"""Puerto Preprocessor (audio/tokens -> normalización).

Patrón de diseño
----------------
- Chain of Responsibility: pasos encadenados de normalización de tokens.
- Template Method: definir pipeline de preprocesamiento con pasos extensibles.

TODO (Issue #18)
----------------
- Definir contrato para paso de VAD/recorte (si aplica) en `process_audio`.
- Documentar orden recomendado de normalización de tokens (espacios, casing, IPA).
- Establecer idempotencia de `normalize_tokens` para evitar efectos duplicados.
"""
from __future__ import annotations

from typing import Protocol

from ipa_core.types import AudioInput, Token, TokenSeq


class Preprocessor(Protocol):
    def process_audio(self, audio: AudioInput) -> AudioInput:  # noqa: D401
        """Normaliza/valida el audio de entrada (formato, SR, canales)."""
        ...

    def normalize_tokens(self, tokens: TokenSeq) -> list[Token]:  # noqa: D401
        """Normaliza tokens IPA (espacios, casing, símbolos)."""
        ...
