"""Preprocesador básico de audio/tokens para el MVP.

Implementa el contrato `Preprocessor` con reglas mínimas:
- process_audio: valida estructura básica (no modifica contenido).
- normalize_tokens: minúsculas y recorte simple de espacios.
"""
from __future__ import annotations

from ipa_core.errors import ValidationError
from ipa_core.types import AudioInput, Token, TokenSeq


class BasicPreprocessor:
    """Normalización mínima para pruebas iniciales.

    Nota: El ajuste de sample rate/canales se delega a futuras versiones.
    """

    _REQUIRED_AUDIO_KEYS = ("path", "sample_rate", "channels")

    def process_audio(self, audio: AudioInput) -> AudioInput:  # noqa: D401
        """Validar claves esperadas y devolver el audio intacto."""
        try:
            path = audio["path"]
            sample_rate = audio["sample_rate"]
            channels = audio["channels"]
        except KeyError as exc:  # Mantener error de validación uniforme.
            raise ValidationError(f"AudioInput missing required key: {exc.args[0]}") from exc

        if not isinstance(path, str) or not path.strip():
            raise ValidationError("AudioInput.path must be a non-empty string")
        if not isinstance(sample_rate, int) or sample_rate <= 0:
            raise ValidationError("AudioInput.sample_rate must be a positive integer")
        if not isinstance(channels, int) or channels <= 0:
            raise ValidationError("AudioInput.channels must be a positive integer")

        return audio

    def normalize_tokens(self, tokens: TokenSeq) -> list[Token]:  # noqa: D401
        """Aplicar strip/lower y descartar tokens vacíos para mantener idempotencia."""
        out: list[Token] = []
        for token in tokens:
            # Normalizar tokens garantiza que futuros pasos reciban entradas previsibles.
            normalized = str(token).strip().lower()
            if normalized:
                out.append(normalized)
        return out
