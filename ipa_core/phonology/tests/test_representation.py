"""Tests para representation.py."""
from __future__ import annotations

import pytest

from ipa_core.phonology.representation import (
    PhonologicalRepresentation,
    TranscriptionResult,
    ComparisonResult,
)


class TestPhonologicalRepresentation:
    """Tests para PhonologicalRepresentation."""
    
    def test_create_phonemic(self) -> None:
        """Crear representación fonémica."""
        rep = PhonologicalRepresentation.phonemic("kasa")
        assert rep.level == "phonemic"
        assert rep.ipa == "kasa"
    
    def test_create_phonetic(self) -> None:
        """Crear representación fonética."""
        rep = PhonologicalRepresentation.phonetic("ˈka.sa")
        assert rep.level == "phonetic"
    
    def test_strips_delimiters(self) -> None:
        """Elimina delimitadores del input."""
        rep = PhonologicalRepresentation.phonemic("/kasa/")
        assert rep.ipa == "kasa"
        
        rep2 = PhonologicalRepresentation.phonetic("[ˈka.sa]")
        assert "ˈ" in rep2.ipa
    
    def test_to_ipa_phonemic(self) -> None:
        """to_ipa() usa slashes para fonémico."""
        rep = PhonologicalRepresentation.phonemic("kasa")
        assert rep.to_ipa() == "/kasa/"
    
    def test_to_ipa_phonetic(self) -> None:
        """to_ipa() usa brackets para fonético."""
        rep = PhonologicalRepresentation.phonetic("ˈka.sa")
        assert rep.to_ipa() == "[ˈka.sa]"
    
    def test_to_ipa_no_delimiters(self) -> None:
        """to_ipa(with_delimiters=False)."""
        rep = PhonologicalRepresentation.phonemic("kasa")
        assert rep.to_ipa(with_delimiters=False) == "kasa"
    
    def test_segments_tokenized(self) -> None:
        """Segmentos se tokenizan automáticamente."""
        rep = PhonologicalRepresentation.phonemic("kasa")
        assert rep.segments == ["k", "a", "s", "a"]
    
    def test_segments_with_digraphs(self) -> None:
        """Dígrafos se tokenizan correctamente."""
        rep = PhonologicalRepresentation.phonemic("tʃaɾo")
        assert "tʃ" in rep.segments
    
    def test_len(self) -> None:
        """len() retorna cantidad de segmentos."""
        rep = PhonologicalRepresentation.phonemic("kasa")
        assert len(rep) == 4
    
    def test_iteration(self) -> None:
        """Representación es iterable."""
        rep = PhonologicalRepresentation.phonemic("abc")
        segments = list(rep)
        assert segments == ["a", "b", "c"]
    
    def test_repr(self) -> None:
        """repr() muestra IPA con delimitadores."""
        rep = PhonologicalRepresentation.phonemic("kasa")
        assert repr(rep) == "/kasa/"


class TestTranscriptionResult:
    """Tests para TranscriptionResult."""
    
    def test_create(self) -> None:
        """Crear resultado de transcripción."""
        phonemic = PhonologicalRepresentation.phonemic("kasa")
        result = TranscriptionResult(text="casa", phonemic=phonemic, source="espeak")
        assert result.text == "casa"
        assert result.phonemic.ipa == "kasa"
    
    def test_get_at_level_phonemic(self) -> None:
        """get_at_level() retorna fonémico."""
        phonemic = PhonologicalRepresentation.phonemic("kasa")
        result = TranscriptionResult(text="casa", phonemic=phonemic)
        assert result.get_at_level("phonemic") == phonemic
    
    def test_get_at_level_phonetic(self) -> None:
        """get_at_level() retorna fonético si existe."""
        phonemic = PhonologicalRepresentation.phonemic("kasa")
        phonetic = PhonologicalRepresentation.phonetic("ˈka.sa")
        result = TranscriptionResult(text="casa", phonemic=phonemic, phonetic=phonetic)
        assert result.get_at_level("phonetic") == phonetic
    
    def test_get_at_level_missing_phonetic(self) -> None:
        """get_at_level() error si falta fonético."""
        phonemic = PhonologicalRepresentation.phonemic("kasa")
        result = TranscriptionResult(text="casa", phonemic=phonemic)
        with pytest.raises(ValueError):
            result.get_at_level("phonetic")


class TestComparisonResult:
    """Tests para ComparisonResult."""
    
    def test_create(self) -> None:
        """Crear resultado de comparación."""
        target = PhonologicalRepresentation.phonemic("kasa")
        observed = PhonologicalRepresentation.phonemic("kasa")
        result = ComparisonResult(
            target=target,
            observed=observed,
            mode="objective",
            evaluation_level="phonemic",
            distance=0.0,
            score=100.0,
        )
        assert result.score == 100.0
        assert result.mode == "objective"
