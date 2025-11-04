"""Puerto Comparator (ref vs hyp -> métricas).

Patrón de diseño
----------------
- Strategy: distintos algoritmos de comparación (Levenshtein, DTW, etc.).
- Visitor: procesar/recorrer alineaciones y operaciones para reportes.

TODO (Issue #18)
----------------
- Definir convención de normalización previa de tokens (responsabilidad del `Preprocessor`).
- Documentar precisión numérica y límites (PER ∈ [0, 1]).
- Permitir pesos por operación (`CompareWeights`) y validaciones asociadas.
"""
from __future__ import annotations

from typing import Optional, Protocol

from ipa_core.types import CompareResult, CompareWeights, TokenSeq


class Comparator(Protocol):
    def compare(
        self,
        ref: TokenSeq,
        hyp: TokenSeq,
        *,
        weights: Optional[CompareWeights] = None,
        **kw,
    ) -> CompareResult:  # noqa: D401
        """Compara secuencias IPA y retorna métricas (PER, alineación)."""
        ...
