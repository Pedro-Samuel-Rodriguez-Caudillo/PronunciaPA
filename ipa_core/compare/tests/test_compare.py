"""Tests para compare.py con ScoringProfile."""
from __future__ import annotations

import pytest

from ipa_core.compare.compare import compare_representations
from ipa_core.phonology.representation import PhonologicalRepresentation
from ipa_core.plugins.language_pack import ScoringProfile


class TestCompareRepresentations:
    """Tests para compare_representations."""
    
    @pytest.mark.asyncio
    async def test_perfect_match(self) -> None:
        """Score perfecto cuando son iguales."""
        target = PhonologicalRepresentation.phonemic("kasa")
        observed = PhonologicalRepresentation.phonemic("kasa")
        
        result = await compare_representations(
            target, observed,
            mode="objective",
        )
        
        assert result.score == 100.0
        assert result.distance == 0.0
    
    @pytest.mark.asyncio
    async def test_one_error(self) -> None:
        """Score reducido con un error."""
        target = PhonologicalRepresentation.phonemic("kasa")
        observed = PhonologicalRepresentation.phonemic("kesa")  # a→e
        
        result = await compare_representations(
            target, observed,
            mode="objective",
        )
        
        assert result.score < 100.0
        assert result.distance > 0.0
    
    @pytest.mark.asyncio
    async def test_different_levels_error(self) -> None:
        """Error si niveles son diferentes."""
        target = PhonologicalRepresentation.phonemic("kasa")
        observed = PhonologicalRepresentation.phonetic("kasa")
        
        with pytest.raises(ValueError):
            await compare_representations(target, observed)
    
    @pytest.mark.asyncio
    async def test_casual_mode_more_tolerant(self) -> None:
        """Modo casual es más tolerante."""
        target = PhonologicalRepresentation.phonemic("kasa")
        observed = PhonologicalRepresentation.phonemic("gasa")
        
        casual_result = await compare_representations(
            target, observed,
            mode="casual",
        )
        phonetic_result = await compare_representations(
            target, observed,
            mode="phonetic",
        )
        
        # Casual debería dar score más alto (más tolerante)
        # porque usa min_cost más bajo
        assert casual_result.score >= phonetic_result.score
    
    @pytest.mark.asyncio
    async def test_with_scoring_profile(self) -> None:
        """Perfil de scoring ajusta el score."""
        target = PhonologicalRepresentation.phonemic("aba")
        observed = PhonologicalRepresentation.phonemic("aβa")  # b→β
        
        # Perfil que acepta b↔β
        profile = ScoringProfile(
            mode="casual",
            allophone_error_weight=0.1,
            acceptable_variants={("b", "β")},
        )
        
        result = await compare_representations(
            target, observed,
            mode="casual",
            profile=profile,
        )
        
        # Score alto porque β es variante aceptable de b
        assert result.score > 90.0
