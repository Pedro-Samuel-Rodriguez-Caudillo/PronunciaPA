"""Tests para el generador G2P de ejercicios."""
from __future__ import annotations

import pytest
from typing import List

from ipa_core.textref.g2p_generator import (
    G2PExerciseGenerator,
    MINIMAL_PAIRS_EN,
    MINIMAL_PAIRS_ES,
)
from ipa_core.drill_types import DrillItem, DrillSet, MinimalPair


class MockTextRef:
    """Mock de TextRefProvider para testing."""
    
    async def to_ipa(self, text: str, *, lang: str, **kw) -> dict:
        """Retornar IPA mock basada en el texto."""
        # Transcripciones simples para testing
        mock_ipas = {
            "pin": "pɪn",
            "bin": "bɪn",
            "cat": "kæt",
            "bat": "bæt",
            "ship": "ʃɪp",
            "chip": "tʃɪp",
            "pato": "pato",
            "bato": "bato",
            "perro": "pero",
            "pero": "peɾo",
        }
        ipa = mock_ipas.get(text.lower(), f"mock:{text}")
        return {"tokens": ipa.split(" ") if " " in ipa else list(ipa), "meta": {}}


class TestMinimalPair:
    """Tests para MinimalPair dataclass."""
    
    def test_creation(self) -> None:
        """Verifica creación de MinimalPair."""
        pair = MinimalPair(
            word_a="pin",
            word_b="bin",
            ipa_a="pɪn",
            ipa_b="bɪn",
            target_phone="p",
            contrast_phone="b",
            position="initial",
        )
        assert pair.word_a == "pin"
        assert pair.target_phone == "p"
    
    def test_to_dict(self) -> None:
        """Verifica conversión a diccionario."""
        pair = MinimalPair(
            word_a="pin",
            word_b="bin",
            ipa_a="pɪn",
            ipa_b="bɪn",
            target_phone="p",
            contrast_phone="b",
        )
        d = pair.to_dict()
        assert d["word_a"] == "pin"
        assert "target_phone" in d


class TestDrillItem:
    """Tests para DrillItem dataclass."""
    
    def test_creation(self) -> None:
        """Verifica creación de DrillItem."""
        item = DrillItem(
            text="cat",
            ipa="kæt",
            target_phones=["k", "æ"],
            difficulty=2,
        )
        assert item.text == "cat"
        assert item.difficulty == 2
    
    def test_default_values(self) -> None:
        """Verifica valores por defecto."""
        item = DrillItem(text="cat", ipa="kæt")
        assert item.target_phones == []
        assert item.difficulty == 1
        assert item.hints == []


class TestDrillSet:
    """Tests para DrillSet dataclass."""
    
    def test_creation(self) -> None:
        """Verifica creación de DrillSet."""
        drill_set = DrillSet(
            name="Test Set",
            description="Testing drills",
            lang="en",
            target_phones=["p", "b"],
        )
        assert drill_set.name == "Test Set"
        assert len(drill_set) == 0
    
    def test_add_item(self) -> None:
        """Verifica adición de items."""
        drill_set = DrillSet(name="Test", description="", lang="en")
        drill_set.add_item(DrillItem(text="cat", ipa="kæt"))
        assert len(drill_set.items) == 1
    
    def test_add_minimal_pair(self) -> None:
        """Verifica adición de pares mínimos."""
        drill_set = DrillSet(name="Test", description="", lang="en")
        drill_set.add_minimal_pair(MinimalPair(
            word_a="pin", word_b="bin",
            ipa_a="pɪn", ipa_b="bɪn",
            target_phone="p", contrast_phone="b",
        ))
        assert len(drill_set.minimal_pairs) == 1
    
    def test_len_counts_both(self) -> None:
        """len() cuenta items y pares mínimos."""
        drill_set = DrillSet(name="Test", description="", lang="en")
        drill_set.add_item(DrillItem(text="cat", ipa="kæt"))
        drill_set.add_minimal_pair(MinimalPair(
            word_a="pin", word_b="bin",
            ipa_a="pɪn", ipa_b="bɪn",
            target_phone="p", contrast_phone="b",
        ))
        assert len(drill_set) == 2


class TestG2PExerciseGenerator:
    """Tests para el generador G2P."""
    
    @pytest.fixture
    def generator(self) -> G2PExerciseGenerator:
        """Generador con mock TextRef."""
        return G2PExerciseGenerator(textref=MockTextRef(), default_lang="en")
    
    @pytest.fixture
    def generator_no_textref(self) -> G2PExerciseGenerator:
        """Generador sin TextRef."""
        return G2PExerciseGenerator(default_lang="en")
    
    @pytest.mark.asyncio
    async def test_get_ipa_with_textref(self, generator: G2PExerciseGenerator) -> None:
        """get_ipa usa TextRef cuando está disponible."""
        ipa = await generator.get_ipa("pin", "en")
        assert len(ipa) > 0
    
    @pytest.mark.asyncio
    async def test_get_ipa_without_textref(self, generator_no_textref: G2PExerciseGenerator) -> None:
        """get_ipa retorna placeholder sin TextRef."""
        ipa = await generator_no_textref.get_ipa("pin", "en")
        assert "[pin]" == ipa
    
    @pytest.mark.asyncio
    async def test_generate_minimal_pairs_english(self, generator: G2PExerciseGenerator) -> None:
        """Genera pares mínimos para fonema inglés."""
        pairs = await generator.generate_minimal_pairs("p", lang="en")
        assert len(pairs) > 0
        assert all(isinstance(p, MinimalPair) for p in pairs)
        assert pairs[0].target_phone == "p"
    
    @pytest.mark.asyncio
    async def test_generate_minimal_pairs_spanish(self) -> None:
        """Genera pares mínimos para fonema español."""
        generator = G2PExerciseGenerator(textref=MockTextRef(), default_lang="es")
        pairs = await generator.generate_minimal_pairs("r", lang="es")
        assert len(pairs) > 0
    
    @pytest.mark.asyncio
    async def test_generate_minimal_pairs_unknown_phone(self, generator: G2PExerciseGenerator) -> None:
        """Retorna lista vacía para fonema desconocido."""
        pairs = await generator.generate_minimal_pairs("xyz", lang="en")
        assert pairs == []
    
    @pytest.mark.asyncio
    async def test_generate_drills(self, generator: G2PExerciseGenerator) -> None:
        """Genera drills para fonemas."""
        drills = await generator.generate_drills(["p"], lang="en")
        assert len(drills) > 0
        assert all(isinstance(d, DrillItem) for d in drills)
    
    @pytest.mark.asyncio
    async def test_generate_drill_set(self, generator: G2PExerciseGenerator) -> None:
        """Genera set completo de ejercicios."""
        drill_set = await generator.generate_drill_set(
            name="P and B Practice",
            target_phones=["p"],
            lang="en",
        )
        assert drill_set.name == "P and B Practice"
        assert len(drill_set) > 0
    
    def test_get_available_phones_english(self, generator: G2PExerciseGenerator) -> None:
        """Lista fonemas disponibles en inglés."""
        phones = generator.get_available_phones("en")
        assert "p" in phones
        assert "θ" in phones
    
    def test_get_available_phones_spanish(self, generator: G2PExerciseGenerator) -> None:
        """Lista fonemas disponibles en español."""
        phones = generator.get_available_phones("es")
        assert "r" in phones
        assert "ɾ" in phones


class TestMinimalPairsData:
    """Tests para los datos de pares mínimos predefinidos."""
    
    def test_english_pairs_exist(self) -> None:
        """Existen pares mínimos para inglés."""
        assert len(MINIMAL_PAIRS_EN) > 0
        assert "p" in MINIMAL_PAIRS_EN
        assert "θ" in MINIMAL_PAIRS_EN
    
    def test_spanish_pairs_exist(self) -> None:
        """Existen pares mínimos para español."""
        assert len(MINIMAL_PAIRS_ES) > 0
        assert "r" in MINIMAL_PAIRS_ES
        assert "ɾ" in MINIMAL_PAIRS_ES
    
    def test_pair_format(self) -> None:
        """Formato correcto de pares."""
        for phone, pairs in MINIMAL_PAIRS_EN.items():
            for pair in pairs:
                assert len(pair) == 4, f"Pair for {phone} should have 4 elements"
