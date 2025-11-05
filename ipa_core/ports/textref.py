"""Puerto TextRef (texto -> IPA tokens).

Patrón sugerido
---------------
- Strategy: permite cambiar el proveedor de conversión texto→IPA sin afectar
  otras partes del sistema.

TODO
----
- Definir una limpieza previa del texto (normalización simple) antes de G2P.
- Documentar el tratamiento de puntuación y números para unificar resultados.
- Especificar una caché sencilla por `(texto, lang, backend)` con invalidación
  explícita para evitar recomputaciones.
"""
from __future__ import annotations

from typing import Protocol

from ipa_core.types import Token


class TextRefProvider(Protocol):
    """Define el contrato para convertir texto plano a tokens IPA."""

    def to_ipa(self, text: str, *, lang: str, **kw) -> list[Token]:  # noqa: D401
        """Convertir texto a tokens IPA.

        Parámetros
        ----------
        text: str
            Texto de entrada a convertir.
        lang: str
            Idioma objetivo (por ejemplo, "es").

        Retorna
        -------
        list[str]
            Lista de tokens IPA representando el texto normalizado.
        """
        ...
