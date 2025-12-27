"""TextRef mínimo basado en caracteres."""
from __future__ import annotations

import unicodedata

from ipa_core.plugins.base import BasePlugin
from ipa_core.types import TextRefResult


class GraphemeTextRef(BasePlugin):
    """Convierte texto plano a símbolos aproximados (placeholder)."""

    async def to_ipa(self, text: str, *, lang: str, **kw) -> TextRefResult:  # noqa: D401
        """Normalización simple NFD/NFC y retorno de grafemas como tokens."""
        normalized = unicodedata.normalize("NFC", text.strip().lower())
        tokens = [char for char in normalized if not char.isspace()]
        return {"tokens": tokens, "meta": {"method": "grapheme", "lang": lang}}


__all__ = ["GraphemeTextRef"]