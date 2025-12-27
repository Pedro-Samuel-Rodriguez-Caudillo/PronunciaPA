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

from typing import Optional, Protocol, runtime_checkable

from ipa_core.types import TextRefResult


@runtime_checkable
class TextRefProvider(Protocol):
    """Define el contrato para convertir texto plano a tokens IPA.
    
    Debe soportar el ciclo de vida de `BasePlugin`.
    """

    async def setup(self) -> None:
        """Configuración inicial del plugin (asíncrona)."""
        ...

    async def teardown(self) -> None:
        """Limpieza de recursos del plugin (asíncrona)."""
        ...

    async def to_ipa(self, text: str, *, lang: str, **kw) -> TextRefResult:  # noqa: D401
        """Convertir texto a tokens IPA.

        Parámetros
        ----------
        text: str
            Texto de entrada a convertir.
        lang: str
            Idioma objetivo (por ejemplo, "es").

        Retorna
        -------
        TextRefResult
            Contiene la lista de tokens IPA y metadatos.
        """
        ...