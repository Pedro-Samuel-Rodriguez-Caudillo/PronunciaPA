"""Backend ASR de ejemplo para el MVP.

Devuelve tokens IPA a partir de parámetros de inicialización o un ejemplo fijo.
No realiza inferencia real; sirve para validar el pipeline.
"""
from __future__ import annotations

from typing import Optional, Any
from pathlib import Path

from ipa_core.plugins.base import BasePlugin
from ipa_core.types import ASRResult, AudioInput, Token


class StubASR(BasePlugin):
    """Implementación simple del contrato `ASRBackend`.

    Params (dict):
      - stub_tokens: list[str] opcional (por defecto: ["h","o","l","a"]).
      - model_path: ruta al modelo (simulado).
    """
    
    output_type = "ipa"  # Stub produces IPA tokens

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        params = params or {}
        self._tokens: list[Token] = ["h", "o", "l", "a"]
        if isinstance(params.get("stub_tokens"), list):
            self._tokens = [str(t) for t in params["stub_tokens"]]

        self._model_path = Path(params.get("model_path", "data/models/stub_model.bin"))
        self._download_stub = bool(params.get("download_stub"))

    async def setup(self) -> None:
        """Simula la verificación/descarga de activos."""
        if not self._download_stub:
            return
        await self.model_manager.ensure_model(
            name="Stub Model",
            local_path=self._model_path,
            download_url="https://example.com/models/stub.bin",
        )

    async def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult:  # noqa: D401

        return {"tokens": list(self._tokens), "meta": {"backend": "stub", "lang": lang or ""}}
