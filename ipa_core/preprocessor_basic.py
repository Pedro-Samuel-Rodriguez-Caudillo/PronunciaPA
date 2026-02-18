"""Preprocesador básico de audio/tokens para el MVP.

Implementa el contrato `Preprocessor` con reglas mínimas:
- process_audio: valida estructura básica; opcionalmente ejecuta AudioProcessingChain.
- normalize_tokens: minúsculas y recorte simple de espacios.
"""
from __future__ import annotations

from typing import Any, Optional
import unicodedata

from ipa_core.errors import ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.types import AudioInput, PreprocessorResult, Token, TokenSeq
from ipa_core.normalization.mappings import normalize_unicode
from ipa_core.normalization.normalizer import IPANormalizer


class BasicPreprocessor(BasePlugin):
    """Normalización mínima para pruebas iniciales.

    Parameters
    ----------
    audio_chain : AudioProcessingChain, optional
        Cadena de procesamiento de audio. Si es ``None`` (por defecto),
        ``process_audio`` solo valida claves y devuelve el audio intacto,
        preservando el comportamiento original. Si se proporciona, ejecuta
        la cadena completa (EnsureWav → VADTrim → QualityCheck).
    """

    _REQUIRED_AUDIO_KEYS = ("path", "sample_rate", "channels")

    def __init__(self, *, audio_chain: Optional[Any] = None) -> None:
        super().__init__()
        self._audio_chain = audio_chain

    async def process_audio(self, audio: AudioInput, **kw: Any) -> PreprocessorResult:  # noqa: D401
        """Validar claves esperadas; si hay audio_chain, ejecutarla completa."""
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

        if self._audio_chain is not None:
            from ipa_core.audio.processing_chain import AudioContext
            ctx = AudioContext(audio=dict(audio), lang=kw.get("lang", ""))  # type: ignore[arg-type]
            ctx = await self._audio_chain.process(ctx)
            meta: dict = {
                "preprocessor": "basic",
                "audio_valid": True,
                "steps": ctx.steps_applied,
                **ctx.meta,
            }
            return {"audio": ctx.audio, "meta": meta}  # type: ignore[return-value]

        return {"audio": dict(audio), "meta": {"preprocessor": "basic", "audio_valid": True}}  # type: ignore

    async def normalize_tokens(self, tokens: TokenSeq, **kw: Any) -> PreprocessorResult:  # noqa: D401
        """Aplicar strip/lower/NFC y descartar tokens vacíos para mantener idempotencia."""
        inventory = kw.get("inventory")
        allophone_rules = kw.get("allophone_rules")
        use_normalizer = bool(inventory or allophone_rules or kw.get("use_normalizer"))

        if use_normalizer:
            normalizer = IPANormalizer(inventory=inventory, collapse_oov=False)
            if allophone_rules:
                normalizer.load_allophone_rules(allophone_rules)
            raw_tokens = [
                unicodedata.normalize("NFC", str(token).strip().lower())
                for token in tokens
                if str(token).strip()
            ]
            out = await normalizer.normalize(raw_tokens)
            meta = {"preprocessor": "basic", "count": len(out)}
            if inventory:
                oov_tokens = [
                    t for t in inventory.get_oov_phones(out)
                    if not inventory.is_valid_symbol(t)
                ]
                meta["oov_tokens"] = oov_tokens
                meta["oov_count"] = len(oov_tokens)
            return {"tokens": out, "meta": meta}

        out: list[Token] = []
        for token in tokens:
            # Strip, lower and NFC normalization + unicode IPA mappings
            normalized = normalize_unicode(str(token).strip().lower())
            if normalized:
                out.append(normalized)
        return {"tokens": out, "meta": {"preprocessor": "basic", "count": len(out)}}
