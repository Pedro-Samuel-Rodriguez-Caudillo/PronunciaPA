"""TextRef provider basado en la CLI de eSpeak/eSpeak-NG."""
from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.types import TextRefResult


class EspeakTextRef(BasePlugin):
    """Convierte texto a IPA usando el binario `espeak`/`espeak-ng`. """

    _VOICE_MAP = {
        "es": "es",
        "en": "en",
        "fr": "fr",
        "pt": "pt",
    }

    def __init__(
        self,
        *,
        default_lang: str = "es",
        binary: Optional[str] = None,
    ) -> None:
        self._default_lang = default_lang
        self._binary = binary or os.getenv("PRONUNCIAPA_ESPEAK_BIN") or self._detect_binary()

    def _detect_binary(self) -> str:
        for candidate in (os.getenv("ESPEAK_BIN"), "espeak-ng", "espeak"):
            if candidate and shutil.which(candidate):
                return candidate
        raise NotReadyError(
            "No se encontró 'espeak' ni 'espeak-ng'. Instálalo o exporta PRONUNCIAPA_ESPEAK_BIN."
        )

    def _resolve_voice(self, lang: str) -> str:
        lang = lang or self._default_lang
        return self._VOICE_MAP.get(lang, lang)

    async def to_ipa(self, text: str, *, lang: str, **kw: Any) -> TextRefResult:  # noqa: D401
        """Convertir texto a IPA usando el binario externo de forma asíncrona."""
        cleaned = text.strip()
        if not cleaned:
            return {"tokens": [], "meta": {"empty": True}}
            
        voice = self._resolve_voice(lang or self._default_lang)
        cmd = [self._binary, "-q", "-v", voice, "--ipa=3", cleaned]
        
        try:
            # Ejecución asíncrona del subproceso
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise ValidationError(f"eSpeak falló con código {proc.returncode}: {stderr.decode()}")
                
            output = stdout.decode().strip()
            
        except FileNotFoundError as exc:  # pragma: no cover
            raise NotReadyError(f"No se pudo ejecutar {self._binary}") from exc
        except Exception as exc:  # pragma: no cover
            if isinstance(exc, (ValidationError, NotReadyError)):
                raise
            raise ValidationError(f"Error al ejecutar eSpeak: {exc}") from exc
            
        tokens = [tok for tok in output.replace("\n", " ").split() if tok]
        return {"tokens": tokens, "meta": {"method": "espeak", "voice": voice}}


__all__ = ["EspeakTextRef"]