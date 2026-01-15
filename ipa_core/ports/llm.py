"""LLM runtime adapter port (prompt -> text)."""
from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMAdapter(Protocol):
    """Contract for local LLM runtime adapters."""

    async def setup(self) -> None:
        """Async initialization hook."""
        ...

    async def teardown(self) -> None:
        """Async cleanup hook."""
        ...

    async def complete(
        self,
        prompt: str,
        *,
        params: Optional[dict[str, Any]] = None,
        **kw,
    ) -> str:
        """Generate raw text completion for a prompt."""
        ...
