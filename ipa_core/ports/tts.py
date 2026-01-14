"""TTS port (text -> audio file).

Strategy pattern: allow switching local TTS backends without touching core.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from ipa_core.types import TTSResult


@runtime_checkable
class TTSProvider(Protocol):
    """Contract for local text-to-speech backends."""

    async def setup(self) -> None:
        """Async initialization hook."""
        ...

    async def teardown(self) -> None:
        """Async cleanup hook."""
        ...

    async def synthesize(
        self,
        text: str,
        *,
        lang: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None,
        **kw,
    ) -> TTSResult:
        """Synthesize speech into a local audio file.

        Parameters
        ----------
        text: str
            Input text to render.
        lang: str
            Language or locale code (for example, "en").
        voice: Optional[str]
            Voice name or speaker id, backend dependent.
        output_path: Optional[str]
            Destination path; if omitted a temp file is created.
        """
        ...
