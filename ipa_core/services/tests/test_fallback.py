"""Tests for the fallback feedback generator."""
import pytest

from ipa_core.services.fallback import (
    generate_fallback_feedback,
    can_use_fallback,
    get_templates,
    TEMPLATES,
)


class TestGetTemplates:
    """Test language template resolution."""
    
    def test_spanish_returns_es_templates(self):
        templates = get_templates("es")
        assert templates == TEMPLATES["es"]
    
    def test_spanish_dialect_returns_es_templates(self):
        templates = get_templates("es-mx")
        assert templates == TEMPLATES["es"]
    
    def test_english_returns_en_templates(self):
        templates = get_templates("en")
        assert templates == TEMPLATES["en"]
    
    def test_unknown_language_falls_back_to_spanish(self):
        templates = get_templates("fr")
        assert templates == TEMPLATES["es"]


class TestGenerateFallbackFeedback:
    """Test the fallback feedback generator."""
    
    def test_perfect_pronunciation_returns_excellent(self):
        report = {
            "lang": "es",
            "metrics": {"per": 0.0},
            "ops": [],
        }
        feedback = generate_fallback_feedback(report)
        
        assert feedback["severity"] == "perfect"
        assert "Excelente" in feedback["advice_short"]
        assert feedback["source"] == "fallback_templates"
    
    def test_good_pronunciation_returns_good_message(self):
        report = {
            "lang": "es",
            "metrics": {"per": 0.10},
            "ops": [],
        }
        feedback = generate_fallback_feedback(report)
        
        assert feedback["severity"] == "good"
        assert "Muy bien" in feedback["advice_short"]
    
    def test_needs_work_returns_encouragement(self):
        report = {
            "lang": "es",
            "metrics": {"per": 0.30},
            "ops": [],
        }
        feedback = generate_fallback_feedback(report)
        
        assert feedback["severity"] == "needs_work"
        assert "Buen intento" in feedback["advice_short"]
    
    def test_substitution_error_generates_advice(self):
        report = {
            "lang": "es",
            "metrics": {"per": 0.25},
            "ops": [
                {"op": "sub", "ref": "a", "hyp": "e"},
            ],
        }
        feedback = generate_fallback_feedback(report)
        
        assert "[a]" in feedback["advice_long"]
        assert "[e]" in feedback["advice_long"]
        assert len(feedback["drills"]) == 1
        assert feedback["drills"][0]["type"] == "contrast"
    
    def test_insertion_error_generates_advice(self):
        report = {
            "lang": "es",
            "metrics": {"per": 0.20},
            "ops": [
                {"op": "ins", "ref": "", "hyp": "s"},
            ],
        }
        feedback = generate_fallback_feedback(report)
        
        assert "[s]" in feedback["advice_long"]
        assert "Añadiste" in feedback["advice_long"]
    
    def test_deletion_error_generates_advice(self):
        report = {
            "lang": "es",
            "metrics": {"per": 0.20},
            "ops": [
                {"op": "del", "ref": "r", "hyp": ""},
            ],
        }
        feedback = generate_fallback_feedback(report)
        
        assert "[r]" in feedback["advice_long"]
        assert "Omitiste" in feedback["advice_long"]
    
    def test_english_templates_used_for_en_lang(self):
        report = {
            "lang": "en",
            "metrics": {"per": 0.0},
            "ops": [],
        }
        feedback = generate_fallback_feedback(report)
        
        assert "Excellent" in feedback["advice_short"]
    
    def test_schema_fills_missing_keys(self):
        report = {"lang": "es", "metrics": {"per": 0.0}, "ops": []}
        schema = {
            "properties": {
                "extra_field": {"type": "string"},
                "extra_array": {"type": "array"},
            }
        }
        feedback = generate_fallback_feedback(report, schema=schema)
        
        assert "extra_field" in feedback
        assert "extra_array" in feedback
        assert feedback["extra_array"] == []
    
    def test_limits_drills_to_five(self):
        report = {
            "lang": "es",
            "metrics": {"per": 0.50},
            "ops": [
                {"op": "sub", "ref": "a", "hyp": "e"},
                {"op": "sub", "ref": "o", "hyp": "u"},
                {"op": "sub", "ref": "i", "hyp": "e"},
                {"op": "del", "ref": "s", "hyp": ""},
                {"op": "del", "ref": "n", "hyp": ""},
                {"op": "ins", "ref": "", "hyp": "x"},
                {"op": "ins", "ref": "", "hyp": "y"},
            ],
        }
        feedback = generate_fallback_feedback(report)
        
        assert len(feedback["drills"]) <= 5


class TestCanUseFallback:
    """Test the fallback eligibility check."""
    
    def test_returns_true_with_ops(self):
        report = {"ops": [{"op": "eq"}]}
        assert can_use_fallback(report) is True
    
    def test_returns_true_with_metrics(self):
        report = {"metrics": {"per": 0.1}}
        assert can_use_fallback(report) is True
    
    def test_returns_false_with_empty_report(self):
        report = {}
        assert can_use_fallback(report) is False
