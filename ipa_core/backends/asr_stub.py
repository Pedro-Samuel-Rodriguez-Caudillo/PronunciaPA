"""Backend ASR de ejemplo para el MVP.

Devuelve tokens IPA a partir de parámetros de inicialización o un ejemplo fijo.
No realiza inferencia real; sirve para validar el pipeline.
"""
from __future__ import annotations

from typing import Optional

from ipa_core.plugins.base import BasePlugin
from ipa_core.types import ASRResult, AudioInput, Token


class StubASR(BasePlugin):
    """Implementación simple del contrato `ASRBackend`.

    Params (dict):
      - stub_tokens: list[str] opcional (por defecto: ["h","o","l","a"]).
    """

    def __init__(self, params: Optional[dict] = None) -> None:
        self._tokens: list[Token] = ["h", "o", "l", "a"]
        if params and isinstance(params.get("stub_tokens"), list):
            self._tokens = [str(t) for t in params["stub_tokens"]]

    async def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult:  # noqa: D401
        return {"tokens": list(self._tokens), "meta": {"backend": "stub", "lang": lang or ""}}