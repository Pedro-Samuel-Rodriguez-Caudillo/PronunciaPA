"""Puerto TextRef (texto -> IPA tokens).

Patrón sugerido
---------------
- Strategy: permite cambiar el proveedor de conversión texto→IPA sin afectar
  otras partes del sistema.

Normalización de texto previa a G2P
-----------------------------------
Antes de invocar G2P, el texto DEBE ser normalizado:
1. Convertir a minúsculas (case-folding)
2. Remover puntuación excepto apóstrofes en contracciones (I'm, don't)
3. Expandir números a palabras ("42" -> "forty two" / "cuarenta y dos")
4. Eliminar espacios múltiples y trim

Tratamiento de puntuación y números
-----------------------------------
- Signos de puntuación: IGNORADOS (no producen tokens IPA)
- Números: EXPANDIR a palabras según idioma antes de G2P
- Símbolos especiales (@, #, $): IGNORADOS o expandir según contexto

Política de caché
-----------------
Se recomienda implementar caché a nivel de implementación:
- Key: (texto_normalizado, lang, version_backend)
- Invalidación: al cambiar configuración o reiniciar el servicio
- TTL sugerido: sin expiración (texto → IPA es determinista)
- Size limit: 10,000 entradas por defecto

Nota: La caché es responsabilidad de la implementación, no del protocolo.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from ipa_core.types import TextRefResult


@runtime_checkable
class TextRefProvider(Protocol):
    """Define el contrato para convertir texto plano a tokens IPA.
    
    Debe soportar el ciclo de vida de `BasePlugin`.
    
    Las implementaciones DEBEN normalizar el texto antes de procesar
    (ver documentación del módulo sobre normalización).
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
        text : str
            Texto de entrada a convertir. Se normalizará automáticamente
            (minúsculas, sin puntuación, números expandidos).
        lang : str
            Idioma objetivo (por ejemplo, "es", "en").

        Retorna
        -------
        TextRefResult
            Contiene la lista de tokens IPA y metadatos.
            
        Metadatos recomendados en TextRefResult.meta
        --------------------------------------------
        - method: str - Método G2P usado (ej: "espeak", "epitran")
        - normalized_input: str - Texto después de normalización
        - cache_hit: bool - Si el resultado vino de caché
        """
        ...