"""Paquete de comparación IPA vs IPA."""

from .base import CompareResult, Comparator, PhonemeStats
from .levenshtein import LevenshteinComparator

__all__ = [
    "Comparator",
    "CompareResult",
    "PhonemeStats",
    "LevenshteinComparator",
]
