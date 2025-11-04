"""Puerto TextRef (texto -> IPA tokens).

Patrón de diseño
----------------
- Strategy: proveedor de conversión texto→IPA intercambiable.

TODO (Issue #18)
----------------
- Definir normalización previa al G2P (Template/Chain para pasos de limpieza).
- Acordar manejo de signos de puntuación y números (convenciones de tokens).
- Establecer caché por `(texto, lang, backend)` y su política de expiración.
"""
from __future__ import annotations

from typing import Protocol

from ipa_core.types import Token


class TextRefProvider(Protocol):
    def to_ipa(self, text: str, *, lang: str, **kw) -> list[Token]:  # noqa: D401
        """Convierte texto a tokens IPA según idioma."""
        ...
