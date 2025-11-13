"""TextRef mínimo basado en caracteres."""
from __future__ import annotations

import unicodedata

from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import Token


class GraphemeTextRef(TextRefProvider):
    """Convierte texto plano a símbolos aproximados (placeholder)."""

    def to_ipa(self, text: str, *, lang: str, **kw) -> list[Token]:  # noqa: D401
        normalized = unicodedata.normalize("NFC", text.strip().lower())
        return [char for char in normalized if not char.isspace()]


__all__ = ["GraphemeTextRef"]
