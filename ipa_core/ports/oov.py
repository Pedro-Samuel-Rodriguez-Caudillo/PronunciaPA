"""Puerto OOVHandlerPort — estrategia de manejo de fonemas fuera de inventario.

Patrón: Strategy — permite inyectar distintas implementaciones de manejo OOV
(colapso articulatorio, mapeo por reglas, pass-through, etc.) sin modificar
el pipeline principal.

Uso típico
----------
El Kernel expone un ``oov_factory: OOVHandlerFactory`` que el pipeline llama
cuando necesita crear un handler para el inventario del LanguagePack activo.

Ejemplo con implementación personalizada::

    class MyOOVHandler:
        def resolve(self, token): ...
        def filter_sequence(self, tokens, *, exclude_unknown=True): ...
        def normalize_pair(self, ref, hyp, *, exclude_unknown=True): ...

    def my_factory(inventory, *, collapse_threshold=0.3, level="phonemic"):
        return MyOOVHandler(inventory, ...)

    kernel.oov_factory = my_factory
"""
from __future__ import annotations

from typing import Literal, Optional, Protocol, Sequence, runtime_checkable

from ipa_core.types import Token


@runtime_checkable
class OOVHandlerPort(Protocol):
    """Contrato mínimo para una implementación de manejo OOV.

    Una implementación recibe un inventario fonético en construcción y expone
    métodos para resolver tokens individuales o secuencias completas.
    """

    def resolve(self, token: Token) -> object:
        """Resolver un token: decidir si está en inventario, colapsar o marcar.

        Retorna un objeto con al menos ``original``, ``resolved`` y ``decision``.
        """
        ...

    def filter_sequence(
        self,
        tokens: Sequence[Token],
        *,
        exclude_unknown: bool = True,
    ) -> list[Token]:
        """Resolver tokens y devolver la secuencia filtrada.

        Tokens ``UNKNOWN_TOKEN`` se excluyen si ``exclude_unknown=True``.
        """
        ...

    def normalize_pair(
        self,
        ref: Sequence[Token],
        hyp: Sequence[Token],
        *,
        exclude_unknown: bool = True,
    ) -> tuple[list[Token], list[Token]]:
        """Normalizar el par (referencia, hipótesis) manejando OOV en ambos.

        Retorna ``(ref_normalizada, hyp_normalizada)``.
        """
        ...


class OOVHandlerFactory(Protocol):
    """Protocolo para fábricas que crean OOVHandlerPort dado un inventario.

    Inyectar una fábrica distinta permite cambiar la estrategia OOV sin
    modificar el pipeline.
    """

    def __call__(
        self,
        inventory: Sequence[Token],
        *,
        collapse_threshold: float = 0.3,
        level: Literal["phonemic", "phonetic"] = "phonemic",
    ) -> OOVHandlerPort:
        """Construir un handler OOV para el inventario dado."""
        ...


def default_oov_factory(
    inventory: Sequence[Token],
    *,
    collapse_threshold: float = 0.3,
    level: Literal["phonemic", "phonetic"] = "phonemic",
) -> OOVHandlerPort:
    """Fábrica por defecto: crea un ``OOVHandler`` con distancia articulatoria.

    Ésta es la implementación estándar incluida en el core. Inyectar otra
    fábrica en el Kernel permite sobreescribir el comportamiento globalmente.
    """
    from ipa_core.compare.oov_handler import OOVHandler
    return OOVHandler(inventory, collapse_threshold=collapse_threshold, level=level)


__all__ = [
    "OOVHandlerFactory",
    "OOVHandlerPort",
    "default_oov_factory",
]
