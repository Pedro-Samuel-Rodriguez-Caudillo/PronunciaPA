"""Preprocesador básico de audio/tokens para el MVP.

Implementa el contrato `Preprocessor` con reglas mínimas:
- process_audio: valida estructura básica (no modifica contenido).
- normalize_tokens: minúsculas y recorte simple de espacios.
"""
from __future__ import annotations

from typing import Sequence

from ipa_core.types import AudioInput, Token, TokenSeq


class BasicPreprocessor:
    """Normalización mínima para pruebas iniciales.

    Nota: El ajuste de sample rate/canales se delega a futuras versiones.
    """

    def process_audio(self, audio: AudioInput) -> AudioInput:  # noqa: D401
        # Validación mínima de claves
        _ = audio["path"], audio["sample_rate"], audio["channels"]
        return audio

    def normalize_tokens(self, tokens: TokenSeq) -> list[Token]:  # noqa: D401
        out: list[Token] = []
        for t in tokens:
            s = str(t).strip().lower()
            if s:
                out.append(s)
        return out
