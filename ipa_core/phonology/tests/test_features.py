"""Tests para features.py - Rasgos distintivos SPE."""
from __future__ import annotations

import pytest

from ipa_core.phonology.features import (
    FeatureBundle,
    get_features,
    feature_distance,
    natural_class,
    CONSONANT_FEATURES,
    VOWEL_FEATURES,
)


class TestFeatureBundle:
    """Tests para FeatureBundle."""
    
    def test_create_from_dict(self) -> None:
        """Crear bundle desde diccionario."""
        bundle = FeatureBundle.from_dict({
            "voice": True,
            "continuant": False,
        })
        assert bundle.is_positive("voice")
        assert bundle.is_negative("continuant")
    
    def test_has_feature(self) -> None:
        """Verificar presencia de rasgos."""
        bundle = FeatureBundle.from_dict({"voice": True, "nasal": False})
        assert bundle.has("voice") is True
        assert bundle.has("nasal") is False
        assert bundle.has("lateral") is None  # no especificado
    
    def test_conflict_raises_error(self) -> None:
        """Un rasgo no puede ser + y - a la vez."""
        with pytest.raises(ValueError):
            FeatureBundle(
                positive=frozenset(["voice"]),
                negative=frozenset(["voice"]),
            )
    
    def test_distance_same(self) -> None:
        """Distancia entre bundles idénticos es 0."""
        b1 = FeatureBundle.from_dict({"voice": True, "nasal": False})
        b2 = FeatureBundle.from_dict({"voice": True, "nasal": False})
        assert b1.distance(b2) == 0
    
    def test_distance_one_diff(self) -> None:
        """Distancia con un rasgo diferente."""
        b1 = FeatureBundle.from_dict({"voice": True, "nasal": False})
        b2 = FeatureBundle.from_dict({"voice": False, "nasal": False})
        assert b1.distance(b2) == 1
    
    def test_matches_compatible(self) -> None:
        """Bundle más específico coincide con menos específico."""
        general = FeatureBundle.from_dict({"voice": True})
        specific = FeatureBundle.from_dict({"voice": True, "nasal": True})
        assert general.matches(specific)
    
    def test_matches_incompatible(self) -> None:
        """Bundles con rasgos opuestos no coinciden."""
        b1 = FeatureBundle.from_dict({"voice": True})
        b2 = FeatureBundle.from_dict({"voice": False})
        assert not b1.matches(b2)
    
    def test_repr(self) -> None:
        """Representación legible."""
        bundle = FeatureBundle.from_dict({"voice": True, "nasal": False})
        repr_str = repr(bundle)
        assert "+voice" in repr_str
        assert "-nasal" in repr_str


class TestSegmentFeatures:
    """Tests para definiciones de segmentos."""
    
    def test_consonants_defined(self) -> None:
        """Consonantes principales están definidas."""
        for c in ["p", "b", "t", "d", "k", "g", "m", "n", "s", "f"]:
            assert c in CONSONANT_FEATURES, f"Missing consonant {c}"
    
    def test_vowels_defined(self) -> None:
        """Vocales principales están definidas."""
        for v in ["a", "e", "i", "o", "u"]:
            assert v in VOWEL_FEATURES, f"Missing vowel {v}"
    
    def test_voiced_consonants_have_voice(self) -> None:
        """Consonantes sonoras tienen +voice."""
        for c in ["b", "d", "g", "v", "z", "m", "n"]:
            features = CONSONANT_FEATURES[c]
            assert features.is_positive("voice"), f"{c} should be +voice"
    
    def test_voiceless_consonants_no_voice(self) -> None:
        """Consonantes sordas tienen -voice."""
        for c in ["p", "t", "k", "f", "s"]:
            features = CONSONANT_FEATURES[c]
            assert features.is_negative("voice"), f"{c} should be -voice"
    
    def test_vowels_are_syllabic(self) -> None:
        """Vocales son +syllabic."""
        for v in ["a", "e", "i", "o", "u"]:
            features = VOWEL_FEATURES[v]
            assert features.is_positive("syllabic"), f"{v} should be +syllabic"
    
    def test_nasals_are_nasal(self) -> None:
        """Nasales son +nasal."""
        for n in ["m", "n", "ŋ"]:
            features = CONSONANT_FEATURES[n]
            assert features.is_positive("nasal"), f"{n} should be +nasal"


class TestGetFeatures:
    """Tests para funciones de utilidad."""
    
    def test_get_known_segment(self) -> None:
        """Obtener rasgos de segmento conocido."""
        features = get_features("p")
        assert features is not None
        assert features.is_negative("voice")
    
    def test_get_unknown_segment(self) -> None:
        """Segmento desconocido retorna None."""
        features = get_features("¿")
        assert features is None
    
    def test_feature_distance_same(self) -> None:
        """Distancia entre mismo segmento es 0."""
        assert feature_distance("p", "p") == 0
    
    def test_feature_distance_similar(self) -> None:
        """p y b son similares (solo difieren en voice)."""
        dist = feature_distance("p", "b")
        assert dist <= 2  # Deberían diferir poco
    
    def test_feature_distance_different(self) -> None:
        """p y a son muy diferentes."""
        dist = feature_distance("p", "a")
        assert dist > 3  # Deberían diferir mucho
    
    def test_feature_distance_unknown(self) -> None:
        """Distancia con desconocido es máxima."""
        dist = feature_distance("p", "¿")
        assert dist == 999


class TestNaturalClass:
    """Tests para clases naturales."""
    
    def test_voiced_stops(self) -> None:
        """Encontrar oclusivas sonoras."""
        pattern = FeatureBundle.from_dict({
            "voice": True,
            "continuant": False,
            "sonorant": False,
        })
        matches = natural_class(pattern)
        assert "b" in matches
        assert "d" in matches
        assert "g" in matches
        assert "p" not in matches  # sorda
    
    def test_high_vowels(self) -> None:
        """Encontrar vocales altas."""
        pattern = FeatureBundle.from_dict({
            "syllabic": True,
            "high": True,
        })
        matches = natural_class(pattern)
        assert "i" in matches
        assert "u" in matches
        assert "a" not in matches  # baja
