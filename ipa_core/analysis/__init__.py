"""Módulos de análisis (acento, feedback, drill generation y métricas)."""

from ipa_core.analysis.accent import (
    build_feedback,
    extract_features,
    load_profile,
    rank_accents,
)
from ipa_core.analysis.drill_generator import (
    extract_confusion_pairs,
    generate_drills_from_errors,
)

__all__ = [
    "build_feedback",
    "extract_confusion_pairs",
    "extract_features",
    "generate_drills_from_errors",
    "load_profile",
    "rank_accents",
]
