"""Tests para distancia articulatoria."""
from __future__ import annotations

import pytest

from ipa_core.compare.articulatory import (
    Place,
    Manner,
    Voicing,
    Height,
    Backness,
    Roundedness,
    CONSONANT_FEATURES,
    VOWEL_FEATURES,
    consonant_distance,
    vowel_distance,
    is_consonant,
    is_vowel,
    articulatory_distance,
    articulatory_substitution_cost,
)
from ipa_core.compare.levenshtein import LevenshteinComparator


class TestConsonantFeatures:
    """Tests para rasgos de consonantes."""
    
    def test_plosives_exist(self) -> None:
        """Plosivas definidas."""
        assert "p" in CONSONANT_FEATURES
        assert "b" in CONSONANT_FEATURES
        assert "t" in CONSONANT_FEATURES
        assert "d" in CONSONANT_FEATURES
        assert "k" in CONSONANT_FEATURES
        assert "g" in CONSONANT_FEATURES
    
    def test_fricatives_exist(self) -> None:
        """Fricativas definidas."""
        assert "f" in CONSONANT_FEATURES
        assert "s" in CONSONANT_FEATURES
        assert "ʃ" in CONSONANT_FEATURES
        assert "θ" in CONSONANT_FEATURES
    
    def test_place_values(self) -> None:
        """Lugares de articulación correctos."""
        assert CONSONANT_FEATURES["p"].place == Place.BILABIAL
        assert CONSONANT_FEATURES["t"].place == Place.ALVEOLAR
        assert CONSONANT_FEATURES["k"].place == Place.VELAR
    
    def test_voicing_values(self) -> None:
        """Sonoridad correcta."""
        assert CONSONANT_FEATURES["p"].voicing == Voicing.VOICELESS
        assert CONSONANT_FEATURES["b"].voicing == Voicing.VOICED


class TestVowelFeatures:
    """Tests para rasgos de vocales."""
    
    def test_cardinal_vowels_exist(self) -> None:
        """Vocales cardinales definidas."""
        assert "i" in VOWEL_FEATURES
        assert "e" in VOWEL_FEATURES
        assert "a" in VOWEL_FEATURES
        assert "o" in VOWEL_FEATURES
        assert "u" in VOWEL_FEATURES
    
    def test_english_vowels_exist(self) -> None:
        """Vocales inglesas definidas."""
        assert "ɪ" in VOWEL_FEATURES
        assert "ʊ" in VOWEL_FEATURES
        assert "æ" in VOWEL_FEATURES
        assert "ə" in VOWEL_FEATURES
    
    def test_height_values(self) -> None:
        """Alturas vocálicas correctas."""
        assert VOWEL_FEATURES["i"].height == Height.CLOSE
        assert VOWEL_FEATURES["e"].height == Height.CLOSE_MID
        assert VOWEL_FEATURES["a"].height == Height.OPEN


class TestConsonantDistance:
    """Tests para distancia entre consonantes."""
    
    def test_same_consonant(self) -> None:
        """Distancia 0 para mismo fonema."""
        assert consonant_distance("p", "p") == 0.0
        assert consonant_distance("t", "t") == 0.0
    
    def test_voicing_only_difference(self) -> None:
        """Diferencia solo en sonoridad = distancia pequeña."""
        dist = consonant_distance("p", "b")
        assert 0 < dist < 0.5  # Solo difieren en sonoridad
    
    def test_place_difference(self) -> None:
        """Diferencia en lugar = distancia mayor."""
        dist_pb = consonant_distance("p", "b")  # Solo sonoridad
        dist_pk = consonant_distance("p", "k")  # Lugar
        assert dist_pk > dist_pb
    
    def test_manner_difference(self) -> None:
        """Diferencia en modo = distancia mayor."""
        dist = consonant_distance("p", "f")  # Plosiva vs fricativa
        assert dist > 0.2
    
    def test_unknown_consonant(self) -> None:
        """Fonema desconocido = distancia máxima."""
        assert consonant_distance("p", "xyz") == 1.0


class TestVowelDistance:
    """Tests para distancia entre vocales."""
    
    def test_same_vowel(self) -> None:
        """Distancia 0 para misma vocal."""
        assert vowel_distance("i", "i") == 0.0
        assert vowel_distance("a", "a") == 0.0
    
    def test_height_difference(self) -> None:
        """Diferencia en altura = distancia notable."""
        dist_ie = vowel_distance("i", "e")  # Close vs close-mid
        dist_ia = vowel_distance("i", "a")  # Close vs open
        assert dist_ia > dist_ie
    
    def test_backness_difference(self) -> None:
        """Diferencia en anterioridad."""
        dist = vowel_distance("i", "u")  # Front vs back
        assert dist > 0
    
    def test_unknown_vowel(self) -> None:
        """Vocal desconocida = distancia máxima."""
        assert vowel_distance("a", "xyz") == 1.0


class TestArticulatoryDistance:
    """Tests para distancia articulatoria general."""
    
    def test_same_phone(self) -> None:
        """Mismo fonema = distancia 0."""
        assert articulatory_distance("p", "p") == 0.0
        assert articulatory_distance("a", "a") == 0.0
    
    def test_consonant_vs_vowel(self) -> None:
        """Consonante vs vocal = distancia máxima."""
        assert articulatory_distance("p", "a") == 1.0
        assert articulatory_distance("a", "p") == 1.0
    
    def test_similar_consonants(self) -> None:
        """Consonantes similares = distancia pequeña."""
        dist = articulatory_distance("p", "b")
        assert 0 < dist < 0.5
    
    def test_similar_vowels(self) -> None:
        """Vocales similares = distancia pequeña."""
        dist = articulatory_distance("i", "ɪ")
        assert 0 < dist < 0.5
    
    def test_distant_consonants(self) -> None:
        """Consonantes distantes = distancia grande."""
        dist = articulatory_distance("p", "h")
        assert dist > 0.5


class TestSubstitutionCost:
    """Tests para costo de sustitución articulatorio."""
    
    def test_cost_range(self) -> None:
        """Costo dentro del rango especificado."""
        cost = articulatory_substitution_cost("p", "b", base_cost=1.0, min_cost=0.3)
        assert 0.3 <= cost <= 1.0
    
    def test_similar_phones_lower_cost(self) -> None:
        """Fonemas similares = menor costo."""
        cost_similar = articulatory_substitution_cost("p", "b")
        cost_distant = articulatory_substitution_cost("p", "h")
        assert cost_similar < cost_distant


class TestLevenshteinWithArticulatory:
    """Tests para Levenshtein con pesos articulatorios."""
    
    @pytest.mark.asyncio
    async def test_without_articulatory(self) -> None:
        """Sin pesos articulatorios, comportamiento normal."""
        comp = LevenshteinComparator(use_articulatory=False)
        result = await comp.compare(["p", "a", "t"], ["b", "a", "t"])
        assert result["meta"]["use_articulatory"] is False
    
    @pytest.mark.asyncio
    async def test_with_articulatory(self) -> None:
        """Con pesos articulatorios, distancia diferente."""
        comp = LevenshteinComparator(use_articulatory=True)
        result = await comp.compare(["p", "a", "t"], ["b", "a", "t"])
        assert result["meta"]["use_articulatory"] is True
    
    @pytest.mark.asyncio
    async def test_articulatory_lowers_similar_cost(self) -> None:
        """Sustitución de fonemas similares tiene menor costo."""
        comp_normal = LevenshteinComparator(use_articulatory=False)
        comp_art = LevenshteinComparator(use_articulatory=True)
        
        # p→b es similar (solo sonoridad)
        result_normal = await comp_normal.compare(["p"], ["b"])
        result_art = await comp_art.compare(["p"], ["b"])
        
        # Con articulatory, la distancia debe ser menor
        assert result_art["meta"]["distance"] < result_normal["meta"]["distance"]
    
    @pytest.mark.asyncio
    async def test_backward_compatibility(self) -> None:
        """Default mantiene comportamiento original."""
        comp = LevenshteinComparator()  # Default: use_articulatory=False
        result = await comp.compare(["a", "b"], ["a", "c"])
        assert result["per"] > 0
