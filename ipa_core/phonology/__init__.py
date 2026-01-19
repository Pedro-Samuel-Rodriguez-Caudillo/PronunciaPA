"""Módulo de fonología para PronunciaPA.

Provee representación formal de segmentos fonológicos y reglas.
"""
from ipa_core.phonology.features import (
    FeatureBundle,
    get_features,
    feature_distance,
    natural_class,
    ALL_SEGMENT_FEATURES,
)
from ipa_core.phonology.segment import Segment, SegmentSequence
from ipa_core.phonology.inventory import PhoneticInventory
from ipa_core.phonology.rule import PhonologicalRule
from ipa_core.phonology.grammar import PhonologicalGrammar
from ipa_core.phonology.representation import (
    PhonologicalRepresentation,
    TranscriptionResult,
    ComparisonResult,
    RepresentationLevel,
)

__all__ = [
    # features
    "FeatureBundle",
    "get_features",
    "feature_distance",
    "natural_class",
    "ALL_SEGMENT_FEATURES",
    # segment
    "Segment",
    "SegmentSequence",
    # inventory
    "PhoneticInventory",
    # rule & grammar
    "PhonologicalRule",
    "PhonologicalGrammar",
    # representation
    "PhonologicalRepresentation",
    "TranscriptionResult",
    "ComparisonResult",
    "RepresentationLevel",
]
