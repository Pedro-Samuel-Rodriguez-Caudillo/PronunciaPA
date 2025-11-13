"""Comparador mínimo para pruebas."""
from __future__ import annotations

from typing import Optional

from ipa_core.ports.compare import Comparator
from ipa_core.types import CompareResult, CompareWeights, TokenSeq


class NoOpComparator(Comparator):
    """Devuelve PER 0.0 sin cálculo real."""

    def compare(
        self,
        ref: TokenSeq,
        hyp: TokenSeq,
        *,
        weights: Optional[CompareWeights] = None,
        **kw,
    ) -> CompareResult:
        return {"per": 0.0, "ops": [], "alignment": [], "meta": {"comparator": "noop"}}


__all__ = ["NoOpComparator"]
