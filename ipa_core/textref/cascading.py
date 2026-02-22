"""TextRef en cascada: prueba múltiples proveedores en orden.

Implementa el patrón Chain of Responsibility para seleccionar
automáticamente el mejor proveedor G2P disponible para un idioma dado.

Orden por defecto (de más a menos preciso):
    1. EspeakTextRef  — 80+ idiomas, rápido, sin dependencias de modelo
    2. EpitranTextRef — 90+ idiomas, más preciso para morfología compleja
    3. GraphemeTextRef — última instancia (retorna caracteres individuales)

El primer proveedor que devuelva tokens no vacíos gana.  Si todos fallan
(o devuelven vacío), se retorna lista vacía con metadatos de diagnóstico.

Uso típico
----------
Activar con ``PRONUNCIAPA_TEXTREF=auto`` o ``textref.name: auto`` en config.
El kernel lo construye automáticamente según plugins disponibles.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ipa_core.plugins.base import BasePlugin
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import TextRefResult

logger = logging.getLogger(__name__)


class CascadingTextRef(BasePlugin):
    """Proveedor TextRef que encadena múltiples backends en orden de prioridad.

    Parámetros
    ----------
    providers : list[TextRefProvider]
        Backends a intentar en orden.  El primero que devuelva tokens
        no vacíos se usa como resultado final.
    """

    def __init__(self, providers: list[TextRefProvider]) -> None:
        super().__init__()
        if not providers:
            raise ValueError("CascadingTextRef requiere al menos un provider")
        self._providers = providers

    async def setup(self) -> None:
        for p in self._providers:
            try:
                await p.setup()
            except Exception as exc:  # pragma: no cover
                logger.debug("Provider %s.setup() falló: %s", type(p).__name__, exc)

    async def teardown(self) -> None:
        for p in self._providers:
            try:
                await p.teardown()
            except Exception:  # pragma: no cover
                pass

    async def to_ipa(
        self, text: str, *, lang: Optional[str] = None, **kw: Any
    ) -> TextRefResult:
        """Intentar proveedores en orden, retornar el primero con tokens."""
        tried: list[str] = []
        last_meta: dict[str, Any] = {}

        for provider in self._providers:
            name = type(provider).__name__
            tried.append(name)
            try:
                result = await provider.to_ipa(text, lang=lang, **kw)
                tokens = result.get("tokens", [])
                if tokens:
                    meta = dict(result.get("meta", {}))
                    meta["cascade_tried"] = tried
                    meta["cascade_winner"] = name
                    return {"tokens": tokens, "meta": meta}
                # Tokens vacíos → siguiente proveedor
                last_meta = result.get("meta", {})
                logger.debug(
                    "CascadingTextRef: %s devolvió tokens vacíos para lang=%s, probando siguiente",
                    name, lang,
                )
            except Exception as exc:
                last_meta = {"error": str(exc)}
                logger.debug(
                    "CascadingTextRef: %s lanzó excepción (%s), probando siguiente",
                    name, exc,
                )

        # Todos fallaron o devolvieron vacío
        logger.warning(
            "CascadingTextRef: ningún proveedor produjo tokens para texto=%r lang=%s. Intentados: %s",
            text[:50], lang, tried,
        )
        return {
            "tokens": [],
            "meta": {
                "method": "cascading",
                "cascade_tried": tried,
                "cascade_winner": None,
                **last_meta,
            },
        }


__all__ = ["CascadingTextRef"]
