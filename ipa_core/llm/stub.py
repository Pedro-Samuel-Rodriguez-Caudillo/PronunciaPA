"""Stub LLM adapter for tests and offline demos."""
from __future__ import annotations

import json
from typing import Any, Optional


_DEFAULT_PAYLOAD = {
    "summary": "Stub feedback.",
    "advice_short": "Keep practicing.",
    "advice_long": "This is a stubbed response for offline testing.",
    "drills": [{"type": "minimal_pair", "text": "la ra"}],
}


class StubLLMAdapter:
    """Return deterministic JSON payloads without running a model."""

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        params = params or {}
        payload = params.get("payload")
        self._payload = payload if isinstance(payload, dict) else dict(_DEFAULT_PAYLOAD)

    async def setup(self) -> None:
        return None

    async def teardown(self) -> None:
        return None

    async def complete(
        self,
        prompt: str,
        *,
        params: Optional[dict[str, Any]] = None,
        **kw,
    ) -> str:
        return json.dumps(self._payload, ensure_ascii=True)


__all__ = ["StubLLMAdapter"]
