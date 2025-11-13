"""TextRef provider basado en la CLI de eSpeak/eSpeak-NG."""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Callable, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import Token

Runner = Callable[[list[str], str], str]


class EspeakTextRef(TextRefProvider):
    """Convierte texto a IPA usando el binario `espeak`/`espeak-ng`."""

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
        runner: Optional[Runner] = None,
    ) -> None:
        self._default_lang = default_lang
        self._binary = binary or os.getenv("PRONUNCIAPA_ESPEAK_BIN") or self._detect_binary()
        self._runner = runner or self._run_command

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

    def to_ipa(self, text: str, *, lang: str, **kw) -> list[Token]:  # noqa: D401
        cleaned = text.strip()
        if not cleaned:
            return []
        voice = self._resolve_voice(lang or self._default_lang)
        cmd = [self._binary, "-q", "-v", voice, "--ipa=3", cleaned]
        try:
            output = self._runner(cmd, cleaned)
        except FileNotFoundError as exc:  # pragma: no cover
            raise NotReadyError(f"No se pudo ejecutar {self._binary}") from exc
        except subprocess.CalledProcessError as exc:  # pragma: no cover
            raise ValidationError(f"eSpeak falló con código {exc.returncode}: {exc.stderr}") from exc
        tokens = [tok for tok in output.replace("\n", " ").split() if tok]
        return tokens

    @staticmethod
    def _run_command(cmd: list[str], text: str) -> str:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


__all__ = ["EspeakTextRef"]
