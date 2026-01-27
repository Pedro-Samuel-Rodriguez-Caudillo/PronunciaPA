"""Canonical Error Report builder for LLM feedback.

This module builds enriched error reports with articulatory features
that help the LLM generate more precise and pedagogical feedback.
"""
from __future__ import annotations

from typing import Any, Optional
from ipa_core.types import CompareResult, Token

# ========================================================================
# Articulatory Feature Maps for Common IPA Phones
# ========================================================================

CONSONANT_FEATURES: dict[str, dict[str, Any]] = {
    # Stops (Plosives)
    "p": {"manner": "stop", "place": "bilabial", "voice": False},
    "b": {"manner": "stop", "place": "bilabial", "voice": True},
    "t": {"manner": "stop", "place": "alveolar", "voice": False},
    "d": {"manner": "stop", "place": "alveolar", "voice": True},
    "k": {"manner": "stop", "place": "velar", "voice": False},
    "g": {"manner": "stop", "place": "velar", "voice": True},
    "ʔ": {"manner": "stop", "place": "glottal", "voice": False},
    # Affricates
    "tʃ": {"manner": "affricate", "place": "postalveolar", "voice": False},
    "dʒ": {"manner": "affricate", "place": "postalveolar", "voice": True},
    "ts": {"manner": "affricate", "place": "alveolar", "voice": False},
    "dz": {"manner": "affricate", "place": "alveolar", "voice": True},
    # Fricatives
    "f": {"manner": "fricative", "place": "labiodental", "voice": False},
    "v": {"manner": "fricative", "place": "labiodental", "voice": True},
    "θ": {"manner": "fricative", "place": "dental", "voice": False},
    "ð": {"manner": "fricative", "place": "dental", "voice": True},
    "s": {"manner": "fricative", "place": "alveolar", "voice": False},
    "z": {"manner": "fricative", "place": "alveolar", "voice": True},
    "ʃ": {"manner": "fricative", "place": "postalveolar", "voice": False},
    "ʒ": {"manner": "fricative", "place": "postalveolar", "voice": True},
    "x": {"manner": "fricative", "place": "velar", "voice": False},
    "ɣ": {"manner": "fricative", "place": "velar", "voice": True},
    "h": {"manner": "fricative", "place": "glottal", "voice": False},
    "ɦ": {"manner": "fricative", "place": "glottal", "voice": True},
    # Nasals
    "m": {"manner": "nasal", "place": "bilabial", "voice": True},
    "n": {"manner": "nasal", "place": "alveolar", "voice": True},
    "ɲ": {"manner": "nasal", "place": "palatal", "voice": True},
    "ŋ": {"manner": "nasal", "place": "velar", "voice": True},
    # Laterals
    "l": {"manner": "lateral", "place": "alveolar", "voice": True},
    "ʎ": {"manner": "lateral", "place": "palatal", "voice": True},
    # Approximants
    "ɹ": {"manner": "approximant", "place": "alveolar", "voice": True},
    "r": {"manner": "trill", "place": "alveolar", "voice": True},
    "ɾ": {"manner": "tap", "place": "alveolar", "voice": True},
    "w": {"manner": "approximant", "place": "labiovelar", "voice": True},
    "j": {"manner": "approximant", "place": "palatal", "voice": True},
    "ʝ": {"manner": "fricative", "place": "palatal", "voice": True},
    "β": {"manner": "fricative", "place": "bilabial", "voice": True},
    "ɸ": {"manner": "fricative", "place": "bilabial", "voice": False},
}

VOWEL_FEATURES: dict[str, dict[str, Any]] = {
    # Close vowels
    "i": {"height": "close", "backness": "front", "rounded": False},
    "y": {"height": "close", "backness": "front", "rounded": True},
    "ɨ": {"height": "close", "backness": "central", "rounded": False},
    "ʉ": {"height": "close", "backness": "central", "rounded": True},
    "ɯ": {"height": "close", "backness": "back", "rounded": False},
    "u": {"height": "close", "backness": "back", "rounded": True},
    # Near-close vowels
    "ɪ": {"height": "near-close", "backness": "front", "rounded": False},
    "ʊ": {"height": "near-close", "backness": "back", "rounded": True},
    # Close-mid vowels
    "e": {"height": "close-mid", "backness": "front", "rounded": False},
    "ø": {"height": "close-mid", "backness": "front", "rounded": True},
    "o": {"height": "close-mid", "backness": "back", "rounded": True},
    # Mid vowels
    "ə": {"height": "mid", "backness": "central", "rounded": False},
    # Open-mid vowels
    "ɛ": {"height": "open-mid", "backness": "front", "rounded": False},
    "œ": {"height": "open-mid", "backness": "front", "rounded": True},
    "ɔ": {"height": "open-mid", "backness": "back", "rounded": True},
    "ʌ": {"height": "open-mid", "backness": "back", "rounded": False},
    # Near-open vowels
    "æ": {"height": "near-open", "backness": "front", "rounded": False},
    "ɐ": {"height": "near-open", "backness": "central", "rounded": False},
    # Open vowels
    "a": {"height": "open", "backness": "front", "rounded": False},
    "ɑ": {"height": "open", "backness": "back", "rounded": False},
    "ɒ": {"height": "open", "backness": "back", "rounded": True},
}

# Height ordering for distance calculation
VOWEL_HEIGHT_ORDER = ["close", "near-close", "close-mid", "mid", "open-mid", "near-open", "open"]
BACKNESS_ORDER = ["front", "central", "back"]


def get_phone_features(phone: str) -> dict[str, Any]:
    """Get articulatory features for a phone.
    
    Parameters
    ----------
    phone : str
        IPA phone symbol.
        
    Returns
    -------
    dict
        Features including type (consonant/vowel), manner, place, voice, etc.
    """
    if phone in CONSONANT_FEATURES:
        return {"type": "consonant", **CONSONANT_FEATURES[phone]}
    if phone in VOWEL_FEATURES:
        return {"type": "vowel", **VOWEL_FEATURES[phone]}
    return {"type": "unknown"}


def calculate_articulatory_distance(ref: str, hyp: str) -> float:
    """Calculate articulatory distance between two phones.
    
    Distance is 0.0 for identical phones and 1.0 for maximally different.
    Phones of different types (consonant vs vowel) get maximum distance.
    
    Parameters
    ----------
    ref : str
        Reference phone.
    hyp : str
        Hypothesis phone (what the user produced).
        
    Returns
    -------
    float
        Distance between 0.0 and 1.0.
    """
    if ref == hyp:
        return 0.0
        
    ref_feat = get_phone_features(ref)
    hyp_feat = get_phone_features(hyp)
    
    # Different types = max distance
    if ref_feat["type"] != hyp_feat["type"]:
        return 1.0
    
    if ref_feat["type"] == "consonant":
        distance = 0.0
        # Manner of articulation (most important)
        if ref_feat.get("manner") != hyp_feat.get("manner"):
            distance += 0.4
        # Place of articulation
        if ref_feat.get("place") != hyp_feat.get("place"):
            distance += 0.35
        # Voicing
        if ref_feat.get("voice") != hyp_feat.get("voice"):
            distance += 0.25
        return min(distance, 1.0)
    
    if ref_feat["type"] == "vowel":
        distance = 0.0
        # Height (most important for vowels)
        ref_height = ref_feat.get("height", "")
        hyp_height = hyp_feat.get("height", "")
        if ref_height != hyp_height:
            # Calculate distance based on position in height scale
            try:
                diff = abs(VOWEL_HEIGHT_ORDER.index(ref_height) - VOWEL_HEIGHT_ORDER.index(hyp_height))
                distance += 0.15 * diff  # Up to 0.9 for extreme differences
            except ValueError:
                distance += 0.4
        # Backness
        ref_back = ref_feat.get("backness", "")
        hyp_back = hyp_feat.get("backness", "")
        if ref_back != hyp_back:
            try:
                diff = abs(BACKNESS_ORDER.index(ref_back) - BACKNESS_ORDER.index(hyp_back))
                distance += 0.15 * diff
            except ValueError:
                distance += 0.3
        # Rounding
        if ref_feat.get("rounded") != hyp_feat.get("rounded"):
            distance += 0.2
        return min(distance, 1.0)
    
    # Unknown types
    return 0.5


def categorize_error(op: dict[str, Any]) -> str:
    """Categorize an error by its articulatory impact.
    
    Returns one of: 'minor', 'moderate', 'significant', 'major'
    """
    op_type = op.get("op", "")
    
    if op_type == "eq":
        return "none"
    
    distance = op.get("articulatory_distance", 0.5)
    
    if op_type in ("ins", "del"):
        # Insertions and deletions are more significant
        return "significant" if distance < 0.5 else "major"
    
    # Substitutions
    if distance < 0.25:
        return "minor"
    elif distance < 0.5:
        return "moderate"
    elif distance < 0.75:
        return "significant"
    else:
        return "major"


def build_enriched_error_report(
    *,
    target_text: str,
    target_tokens: list[Token],
    hyp_tokens: list[Token],
    compare_result: CompareResult,
    lang: str,
    mode: str = "objective",
    evaluation_level: str = "phonemic",
    feedback_level: Optional[str] = None,
    confidence: Optional[str] = None,
    warnings: Optional[list[str]] = None,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build enriched Error Report with articulatory features.
    
    This report is designed to be the canonical input for LLM feedback
    generation, containing all information needed for pedagogical advice.
    
    Parameters
    ----------
    target_text : str
        Original text the user was trying to pronounce.
    target_tokens : list[Token]
        IPA tokens of the target pronunciation.
    hyp_tokens : list[Token]
        IPA tokens of what the user actually produced.
    compare_result : CompareResult
        Result from the comparator with ops and alignment.
    lang : str
        Language code (e.g., 'es', 'en-us').
    mode : str
        Evaluation mode: 'casual', 'objective', 'phonetic'.
    evaluation_level : str
        Level: 'phonemic' or 'phonetic'.
    feedback_level : str, optional
        Nivel de feedback: 'casual' o 'precise'.
    confidence : str, optional
        Nivel de confianza de la comparacion.
    warnings : list[str], optional
        Advertencias sobre confiabilidad o datos incompletos.
    meta : dict, optional
        Additional metadata (ASR info, audio quality, etc.).
        
    Returns
    -------
    dict
        Enriched error report ready for LLM consumption.
    """
    ops = compare_result.get("ops", [])
    
    # Enrich each error operation with features
    enriched_ops = []
    error_summary = {"minor": 0, "moderate": 0, "significant": 0, "major": 0}
    
    for op in ops:
        enriched_op = dict(op)
        op_type = op.get("op", "")
        
        if op_type == "sub":
            ref = op.get("ref", "")
            hyp = op.get("hyp", "")
            enriched_op["ref_features"] = get_phone_features(ref)
            enriched_op["hyp_features"] = get_phone_features(hyp)
            enriched_op["articulatory_distance"] = calculate_articulatory_distance(ref, hyp)
        elif op_type == "del":
            ref = op.get("ref", "")
            enriched_op["ref_features"] = get_phone_features(ref)
            enriched_op["articulatory_distance"] = 1.0  # Missing phone
        elif op_type == "ins":
            hyp = op.get("hyp", "")
            enriched_op["hyp_features"] = get_phone_features(hyp)
            enriched_op["articulatory_distance"] = 0.8  # Extra phone
        else:
            enriched_op["articulatory_distance"] = 0.0
        
        # Categorize error severity
        category = categorize_error(enriched_op)
        enriched_op["severity"] = category
        if category in error_summary:
            error_summary[category] += 1
        
        enriched_ops.append(enriched_op)
    
    # Calculate weighted error score
    per = compare_result.get("per", 0.0)
    weighted_score = max(0.0, (1.0 - per) * 100.0)
    
    # Adjust score based on error severity distribution
    if mode == "casual":
        # In casual mode, minor errors don't penalize much
        weighted_score += error_summary.get("minor", 0) * 2
    elif mode == "phonetic":
        # In phonetic mode, even minor errors matter
        weighted_score -= error_summary.get("minor", 0) * 1
    
    weighted_score = max(0.0, min(100.0, weighted_score))
    
    # Select focus errors (top 3 most impactful)
    focus_errors = [
        op for op in enriched_ops 
        if op.get("op") != "eq" and op.get("articulatory_distance", 0) > 0.3
    ][:3]
    
    return {
        "target_text": target_text,
        "target_ipa": " ".join(target_tokens),
        "observed_ipa": " ".join(hyp_tokens),
        "metrics": {
            "per": per,
            "score": round(weighted_score, 1),
            "total_tokens": len(target_tokens),
            "error_count": sum(1 for op in enriched_ops if op.get("op") != "eq"),
        },
        "error_summary": error_summary,
        "ops": enriched_ops,
        "focus_errors": focus_errors,
        "alignment": compare_result.get("alignment", []),
        "lang": lang,
        "mode": mode,
        "evaluation_level": evaluation_level,
        "feedback_level": feedback_level,
        "confidence": confidence,
        "warnings": warnings or [],
        "meta": meta or {},
    }


__all__ = [
    "build_enriched_error_report",
    "get_phone_features",
    "calculate_articulatory_distance",
    "categorize_error",
    "CONSONANT_FEATURES",
    "VOWEL_FEATURES",
]
