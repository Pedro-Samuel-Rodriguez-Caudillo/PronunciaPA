"""Módulos de análisis (acento, feedback y métricas)."""

from ipa_core.analysis.accent import (
    build_feedback,
    extract_features,
    load_profile,
    rank_accents,
)

__all__ = [
    "build_feedback",
    "extract_features",
    "load_profile",
    "rank_accents",
]
