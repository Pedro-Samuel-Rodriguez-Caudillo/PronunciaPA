"""Puerto OOVHandler (Out-Of-Vocabulary handler) inyectable.

Define el contrato para manejar fonemas fuera del inventario canónico
de un LanguagePack o de la lengua objetivo.

Motivación
----------
El OOV handler es una pieza de lógica intercambiable:
- La implementación por defecto colapsa fonemas cercanos (distancia
  articulatoria < umbral) y marca como desconocidos los lejanos.
- Implementaciones alternativas podrían usar mapeos léxicos, silenciar
  OOVs, o elevar errores estrictos según el modo de evaluación.

Integración con el Kernel
-------------------------
El Kernel puede recibir un ``OOVHandlerPort`` inyectado.  Si no se
especifica, el pipeline usará la implementación concreta ``OOVHandler``
de ``ipa_core.compare.oov_handler``.

Uso típico
----------
::

    from ipa_core.ports.oov import OOVHandlerPort

    class StrictOOVHandler:
        async def setup(self) -> None: ...
        async def teardown(self) -> None: ...
        def filter_sequence(self, tokens, *, inventory=None):
            return [t for t in tokens if t in inventory]
        def resolve(self, token, *, inventory=None):
            ...
"""
from __future__ import annotations

from typing import Optional, Protocol, Sequence, runtime_checkable

from ipa_core.types import Token


@runtime_checkable
class OOVHandlerPort(Protocol):
    """Contrato para el manejador de fonemas OOV.

    Implementaciones deben soportar el ciclo de vida BasePlugin
    (setup/teardown), aunque pueden ser no-op.
    """

    async def setup(self) -> None:
        """Configuración inicial (asíncrona)."""
        ...

    async def teardown(self) -> None:
        """Limpieza de recursos."""
        ...

    def filter_sequence(
        self,
        tokens: Sequence[Token],
        *,
        inventory: Optional[Sequence[Token]] = None,
    ) -> list[Token]:
        """Filtrar una secuencia de tokens resolviendo OOVs.

        Parámetros
        ----------
        tokens:
            Secuencia de tokens IPA a filtrar.
        inventory:
            Inventario canónico de símbolos válidos.  Si es None, el
            handler usa el inventario configurado en su constructor.

        Retorna
        -------
        list[Token]
            Tokens con OOVs resueltos (colapsados o marcados como ``"?"``).
        """
        ...

    def resolve(
        self,
        token: Token,
        *,
        inventory: Optional[Sequence[Token]] = None,
    ) -> Token:
        """Resolver un único token OOV.

        Retorna el token original si está en inventario, el más cercano
        si puede colapsarse, o ``"?"`` si es demasiado distante.
        """
        ...


class PassthroughOOVHandler:
    """OOVHandler que deja todos los tokens intactos (no filtra nada).

    Útil como no-op en modos donde el inventario no está definido o
    cuando se quiere deshabilitar el filtrado OOV explícitamente.
    """

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

    def filter_sequence(
        self,
        tokens: Sequence[Token],
        *,
        inventory: Optional[Sequence[Token]] = None,
    ) -> list[Token]:
        return list(tokens)

    def resolve(
        self,
        token: Token,
        *,
        inventory: Optional[Sequence[Token]] = None,
    ) -> Token:
        return token


__all__ = ["OOVHandlerPort", "PassthroughOOVHandler"]
