"""TextRef provider basado en la CLI de eSpeak/eSpeak-NG."""
from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any, Optional, TYPE_CHECKING

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.textref.tokenize import tokenize_ipa
from ipa_core.types import TextRefResult

if TYPE_CHECKING:
    from ipa_core.textref.cache import TextRefCache


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
        cache: Optional["TextRefCache"] = None,
    ) -> None:
        self._default_lang = default_lang
        self._binary = binary or os.getenv("PRONUNCIAPA_ESPEAK_BIN") or self._detect_binary()
        self._cache = cache

    def _detect_binary(self) -> str:
        for candidate in (os.getenv("ESPEAK_BIN"), "espeak-ng", "espeak"):
            if candidate and shutil.which(candidate):
                return candidate
        windows_candidates = [
            r"C:\Program Files\eSpeak NG\espeak-ng.exe",
            r"C:\Program Files\eSpeak NG\espeak.exe",
            r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe",
            r"C:\Program Files (x86)\eSpeak NG\espeak.exe",
        ]
        for path in windows_candidates:
            if os.path.exists(path):
                return path
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
        
        resolved_lang = lang or self._default_lang
        
        # Usar cache si está disponible
        if self._cache is not None:
            return await self._cache.get_or_compute(
                cleaned, resolved_lang, "espeak",
                lambda: self._compute_ipa(cleaned, resolved_lang)
            )
        
        return await self._compute_ipa(cleaned, resolved_lang)
    
    async def _compute_ipa(self, text: str, lang: str) -> TextRefResult:
        """Ejecutar espeak para obtener transcripción IPA."""
        voice = self._resolve_voice(lang)
        cmd = [self._binary, "-q", "-v", voice, "--ipa=3", text]
        
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
            
        tokens = tokenize_ipa(output)
        return {"tokens": tokens, "meta": {"method": "espeak", "voice": voice}} 


__all__ = ["EspeakTextRef"]
