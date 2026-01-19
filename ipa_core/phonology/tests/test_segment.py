"""Tests para segment.py - Segmentos fonológicos."""
from __future__ import annotations

import pytest

from ipa_core.phonology.segment import Segment, SegmentSequence


class TestSegment:
    """Tests para Segment."""
    
    def test_create_phoneme(self) -> None:
        """Crear fonema."""
        seg = Segment.phoneme("p")
        assert seg.symbol == "p"
        assert seg.is_phoneme is True
        assert seg.base_phoneme is None
    
    def test_create_allophone(self) -> None:
        """Crear alófono."""
        seg = Segment.allophone("β", "b")
        assert seg.symbol == "β"
        assert seg.is_phoneme is False
        assert seg.base_phoneme == "b"
    
    def test_allophone_requires_base(self) -> None:
        """Alófono sin base lanza error."""
        with pytest.raises(ValueError):
            Segment(symbol="β", is_phoneme=False)
    
    def test_repr_phoneme(self) -> None:
        """Representación de fonema usa slashes."""
        seg = Segment.phoneme("p")
        assert repr(seg) == "/p/"
    
    def test_repr_allophone(self) -> None:
        """Representación de alófono usa brackets."""
        seg = Segment.allophone("β", "b")
        assert repr(seg) == "[β]"
    
    def test_equality(self) -> None:
        """Igualdad de segmentos."""
        s1 = Segment.phoneme("p")
        s2 = Segment.phoneme("p")
        s3 = Segment.phoneme("b")
        assert s1 == s2
        assert s1 != s3
    
    def test_hash(self) -> None:
        """Segmentos son hashables."""
        s1 = Segment.phoneme("p")
        s2 = Segment.phoneme("p")
        assert hash(s1) == hash(s2)
        
        # Pueden usarse en sets
        s = {s1, s2}
        assert len(s) == 1


class TestSegmentSequence:
    """Tests para SegmentSequence."""
    
    def test_create_empty(self) -> None:
        """Crear secuencia vacía."""
        seq = SegmentSequence()
        assert len(seq) == 0
    
    def test_create_phonemic(self) -> None:
        """Crear secuencia fonémica."""
        seq = SegmentSequence.from_string("kasa", level="phonemic")
        assert seq.level == "phonemic"
        assert len(seq) == 4
    
    def test_create_phonetic(self) -> None:
        """Crear secuencia fonética."""
        seq = SegmentSequence.from_string("kasa", level="phonetic")
        assert seq.level == "phonetic"
    
    def test_to_ipa_phonemic(self) -> None:
        """IPA fonémico usa slashes."""
        seq = SegmentSequence.from_string("kasa", level="phonemic")
        assert seq.to_ipa() == "/kasa/"
    
    def test_to_ipa_phonetic(self) -> None:
        """IPA fonético usa brackets."""
        seq = SegmentSequence.from_string("kasa", level="phonetic")
        assert seq.to_ipa() == "[kasa]"
    
    def test_strip_delimiters(self) -> None:
        """from_string remueve delimitadores."""
        seq = SegmentSequence.from_string("/kasa/", level="phonemic")
        assert seq.to_ipa() == "/kasa/"
    
    def test_iteration(self) -> None:
        """Secuencia es iterable."""
        seq = SegmentSequence.from_string("abc", level="phonemic")
        symbols = [s.symbol for s in seq]
        assert symbols == ["a", "b", "c"]
    
    def test_indexing(self) -> None:
        """Secuencia soporta indexación."""
        seq = SegmentSequence.from_string("abc", level="phonemic")
        assert seq[0].symbol == "a"
        assert seq[2].symbol == "c"
    
    def test_invalid_level(self) -> None:
        """Nivel inválido lanza error."""
        with pytest.raises(ValueError):
            SegmentSequence(level="invalid")
