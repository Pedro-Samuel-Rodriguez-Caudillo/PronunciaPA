"""Tests para inventory.py - Inventario fonético."""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile

from ipa_core.phonology.inventory import PhoneticInventory


class TestPhoneticInventory:
    """Tests para PhoneticInventory."""
    
    @pytest.fixture
    def spanish_inventory(self) -> PhoneticInventory:
        """Inventario básico de español."""
        inv = PhoneticInventory(language="es", dialect="es-mx")
        # Añadir fonemas
        for c in ["p", "b", "t", "d", "k", "g", "m", "n"]:
            inv.add_phoneme(c)
        for v in ["a", "e", "i", "o", "u"]:
            inv.add_phoneme(v)
        # Añadir alófonos
        inv.add_allophone("β", "b")
        inv.add_allophone("ð", "d")
        inv.add_allophone("ɣ", "g")
        return inv
    
    def test_add_phoneme(self) -> None:
        """Añadir fonema."""
        inv = PhoneticInventory(language="es", dialect="es-mx")
        seg = inv.add_phoneme("p")
        assert seg.symbol == "p"
        assert seg.is_phoneme is True
        assert inv.is_phoneme("p")
    
    def test_add_allophone(self, spanish_inventory: PhoneticInventory) -> None:
        """Añadir alófono."""
        assert spanish_inventory.is_allophone("β")
        assert spanish_inventory.get_base_phoneme("β") == "b"
    
    def test_add_allophone_invalid_base(self) -> None:
        """Alófono con base inexistente lanza error."""
        inv = PhoneticInventory(language="es", dialect="es-mx")
        with pytest.raises(ValueError):
            inv.add_allophone("β", "b")  # b no está en inventario
    
    def test_is_phoneme(self, spanish_inventory: PhoneticInventory) -> None:
        """Verificar si es fonema."""
        assert spanish_inventory.is_phoneme("b")
        assert not spanish_inventory.is_phoneme("β")
        assert not spanish_inventory.is_phoneme("x")
    
    def test_is_allophone(self, spanish_inventory: PhoneticInventory) -> None:
        """Verificar si es alófono."""
        assert spanish_inventory.is_allophone("β")
        assert not spanish_inventory.is_allophone("b")
    
    def test_get_base_phoneme(self, spanish_inventory: PhoneticInventory) -> None:
        """Obtener fonema base."""
        assert spanish_inventory.get_base_phoneme("β") == "b"
        assert spanish_inventory.get_base_phoneme("ð") == "d"
        assert spanish_inventory.get_base_phoneme("b") == "b"  # fonema se retorna a sí mismo
        assert spanish_inventory.get_base_phoneme("x") is None  # desconocido
    
    def test_get_allophones_of(self, spanish_inventory: PhoneticInventory) -> None:
        """Obtener alófonos de un fonema."""
        allos = spanish_inventory.get_allophones_of("b")
        symbols = [a.symbol for a in allos]
        assert "β" in symbols
    
    def test_get_all_phonemes(self, spanish_inventory: PhoneticInventory) -> None:
        """Obtener todos los fonemas."""
        phonemes = spanish_inventory.get_all_phonemes()
        assert "b" in phonemes
        assert "a" in phonemes
        assert "β" not in phonemes  # es alófono
    
    def test_get_all_phones(self, spanish_inventory: PhoneticInventory) -> None:
        """Obtener todos los sonidos (fonemas + alófonos)."""
        phones = spanish_inventory.get_all_phones()
        assert "b" in phones
        assert "β" in phones
    
    def test_collapse_to_phoneme(self, spanish_inventory: PhoneticInventory) -> None:
        """Colapsar alófono a fonema."""
        assert spanish_inventory.collapse_to_phoneme("β") == "b"
        assert spanish_inventory.collapse_to_phoneme("b") == "b"
        assert spanish_inventory.collapse_to_phoneme("x") == "x"  # desconocido


class TestInventoryYAML:
    """Tests para carga desde YAML."""
    
    def test_from_yaml(self, tmp_path: Path) -> None:
        """Cargar desde YAML."""
        yaml_content = """
language: es
dialect: es-mx
inventory:
  consonants:
    - p
    - b
    - t
  vowels:
    - a
    - e
aliases:
  β: b
"""
        yaml_path = tmp_path / "inventory.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")
        
        inv = PhoneticInventory.from_yaml(yaml_path)
        assert inv.language == "es"
        assert inv.dialect == "es-mx"
        assert inv.is_phoneme("p")
        assert inv.is_phoneme("a")
        assert inv.is_allophone("β")
