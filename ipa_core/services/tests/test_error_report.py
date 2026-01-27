"""Tests for the enriched error report module."""
from __future__ import annotations

import pytest

from ipa_core.services.error_report import (
    build_enriched_error_report,
    get_phone_features,
    calculate_articulatory_distance,
    categorize_error,
    CONSONANT_FEATURES,
    VOWEL_FEATURES,
)


class TestGetPhoneFeatures:
    """Test phone feature extraction."""

    def test_consonant_features(self):
        """Should return correct features for consonants."""
        features = get_phone_features("p")
        assert features["type"] == "consonant"
        assert features["manner"] == "stop"
        assert features["place"] == "bilabial"
        assert features["voice"] is False

    def test_voiced_consonant(self):
        """Should correctly identify voiced consonants."""
        features = get_phone_features("b")
        assert features["voice"] is True

    def test_vowel_features(self):
        """Should return correct features for vowels."""
        features = get_phone_features("i")
        assert features["type"] == "vowel"
        assert features["height"] == "close"
        assert features["backness"] == "front"
        assert features["rounded"] is False

    def test_rounded_vowel(self):
        """Should correctly identify rounded vowels."""
        features = get_phone_features("u")
        assert features["rounded"] is True

    def test_unknown_phone(self):
        """Should return unknown type for unrecognized phones."""
        features = get_phone_features("xyz")
        assert features["type"] == "unknown"


class TestArticulatoryDistance:
    """Test articulatory distance calculation."""

    def test_identical_phones(self):
        """Distance should be 0 for identical phones."""
        assert calculate_articulatory_distance("p", "p") == 0.0
        assert calculate_articulatory_distance("i", "i") == 0.0

    def test_voicing_difference(self):
        """Voicing difference should add 0.25 distance."""
        distance = calculate_articulatory_distance("p", "b")
        # Same manner and place, only voicing differs
        assert distance == pytest.approx(0.25, abs=0.01)

    def test_place_difference(self):
        """Place difference should add 0.35 distance."""
        distance = calculate_articulatory_distance("p", "t")
        # Both are voiceless stops, different place
        assert distance == pytest.approx(0.35, abs=0.01)

    def test_manner_difference(self):
        """Manner difference should add 0.4 distance."""
        distance = calculate_articulatory_distance("p", "f")
        # Both bilabial/labiodental voiceless, different manner
        # Actually p is bilabial stop, f is labiodental fricative
        assert distance > 0.4

    def test_consonant_vowel_max_distance(self):
        """Consonant vs vowel should be max distance."""
        distance = calculate_articulatory_distance("p", "a")
        assert distance == 1.0

    def test_vowel_height_distance(self):
        """Vowel height differences should be gradual."""
        # i (close) vs ɛ (open-mid) - 3 steps apart
        distance = calculate_articulatory_distance("i", "ɛ")
        assert 0.3 < distance < 0.7

    def test_unknown_phones(self):
        """Unknown phones should have moderate distance."""
        distance = calculate_articulatory_distance("xyz", "abc")
        assert distance == 0.5


class TestCategorizeError:
    """Test error categorization."""

    def test_eq_is_none(self):
        """Equal operations should have no severity."""
        op = {"op": "eq", "ref": "a", "hyp": "a"}
        assert categorize_error(op) == "none"

    def test_minor_substitution(self):
        """Small distance substitution should be minor."""
        op = {"op": "sub", "ref": "p", "hyp": "b", "articulatory_distance": 0.2}
        assert categorize_error(op) == "minor"

    def test_major_substitution(self):
        """Large distance substitution should be major."""
        op = {"op": "sub", "ref": "p", "hyp": "a", "articulatory_distance": 1.0}
        assert categorize_error(op) == "major"

    def test_deletion_is_significant(self):
        """Deletions should be at least significant."""
        op = {"op": "del", "ref": "a", "articulatory_distance": 0.3}
        assert categorize_error(op) == "significant"

    def test_insertion_is_significant(self):
        """Insertions should be at least significant."""
        op = {"op": "ins", "hyp": "a", "articulatory_distance": 0.3}
        assert categorize_error(op) == "significant"


class TestBuildEnrichedErrorReport:
    """Test the full error report builder."""

    def test_basic_report(self):
        """Should build a complete report with all fields."""
        compare_result = {
            "per": 0.25,
            "ops": [
                {"op": "eq", "ref": "h", "hyp": "h"},
                {"op": "sub", "ref": "o", "hyp": "a"},
                {"op": "eq", "ref": "l", "hyp": "l"},
                {"op": "eq", "ref": "a", "hyp": "a"},
            ],
            "alignment": [("h", "h"), ("o", "a"), ("l", "l"), ("a", "a")],
        }
        
        report = build_enriched_error_report(
            target_text="hola",
            target_tokens=["h", "o", "l", "a"],
            hyp_tokens=["h", "a", "l", "a"],
            compare_result=compare_result,
            lang="es",
        )
        
        assert report["target_text"] == "hola"
        assert report["target_ipa"] == "h o l a"
        assert report["observed_ipa"] == "h a l a"
        assert report["lang"] == "es"
        assert "metrics" in report
        assert report["metrics"]["per"] == 0.25
        assert "error_summary" in report
        assert len(report["ops"]) == 4

    def test_enriched_ops_have_features(self):
        """Substitution ops should have articulatory features."""
        compare_result = {
            "per": 0.5,
            "ops": [{"op": "sub", "ref": "p", "hyp": "b"}],
            "alignment": [("p", "b")],
        }
        
        report = build_enriched_error_report(
            target_text="p",
            target_tokens=["p"],
            hyp_tokens=["b"],
            compare_result=compare_result,
            lang="en",
        )
        
        sub_op = report["ops"][0]
        assert "ref_features" in sub_op
        assert "hyp_features" in sub_op
        assert "articulatory_distance" in sub_op
        assert sub_op["ref_features"]["type"] == "consonant"

    def test_focus_errors_limited(self):
        """Focus errors should be limited to top 3."""
        ops = [
            {"op": "sub", "ref": f"p{i}", "hyp": f"b{i}"}
            for i in range(10)
        ]
        compare_result = {"per": 0.5, "ops": ops, "alignment": []}
        
        report = build_enriched_error_report(
            target_text="test",
            target_tokens=["t", "e", "s", "t"],
            hyp_tokens=["d", "a", "z", "d"],
            compare_result=compare_result,
            lang="en",
        )
        
        # focus_errors is filtered by distance > 0.3, may be less than 3
        assert len(report["focus_errors"]) <= 3

    def test_mode_affects_score(self):
        """Different modes should adjust the score."""
        compare_result = {
            "per": 0.2,
            "ops": [
                {"op": "sub", "ref": "a", "hyp": "ə"},
            ],
            "alignment": [],
        }
        
        casual_report = build_enriched_error_report(
            target_text="a",
            target_tokens=["a"],
            hyp_tokens=["ə"],
            compare_result=compare_result,
            lang="en",
            mode="casual",
        )
        
        phonetic_report = build_enriched_error_report(
            target_text="a",
            target_tokens=["a"],
            hyp_tokens=["ə"],
            compare_result=compare_result,
            lang="en",
            mode="phonetic",
        )
        
        # Casual mode should be more lenient
        assert casual_report["metrics"]["score"] >= phonetic_report["metrics"]["score"]
