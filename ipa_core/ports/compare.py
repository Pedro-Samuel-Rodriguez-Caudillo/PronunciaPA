"""Puerto Comparator (ref vs hyp -> métricas).

Patrón sugerido
---------------
- Strategy: posibilita distintas implementaciones (Levenshtein, DTW, etc.).
- Visitor (opcional): facilita recorrer alineaciones para generar reportes.

TODO
----
- Aclarar que la normalización de tokens ocurre antes (ver `Preprocessor`).
- Documentar el rango de PER [0, 1] y cómo se calcula de forma simple.
- Permitir pesos por operación (`CompareWeights`) con validaciones mínimas.
"""
from __future__ import annotations

from typing import Optional, Protocol

from ipa_core.types import CompareResult, CompareWeights, TokenSeq


class Comparator(Protocol):
    """Define el contrato para comparar dos secuencias de tokens IPA."""

    def compare(
        self,
        ref: TokenSeq,
        hyp: TokenSeq,
        *,
        weights: Optional[CompareWeights] = None,
        **kw,
    ) -> CompareResult:  # noqa: D401
        """Comparar `ref` (referencia) contra `hyp` (predicción).

        Retorna el `CompareResult` con PER y alineación.
        """
        ...
