"""Tests para el módulo de normalización IPA."""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile

from ipa_core.normalization.mappings import (
    normalize_unicode,
    decompose_to_base_and_diacritics,
    UNICODE_MAPPINGS,
)
from ipa_core.normalization.inventory import Inventory
from ipa_core.normalization.normalizer import (
    IPANormalizer,
    SPANISH_ALLOPHONE_RULES,
    ENGLISH_ALLOPHONE_RULES,
)


class TestNormalizeUnicode:
    """Tests para normalización Unicode."""
    
    def test_basic_normalization(self) -> None:
        """Verifica normalización básica a NFC."""
        text = "hola"
        result = normalize_unicode(text)
        assert result == "hola"
    
    def test_stress_mark_mapping(self) -> None:
        """Verifica mapeo de apóstrofe a marca de estrés."""
        text = "'hello"
        result = normalize_unicode(text)
        assert result == "ˈhello"
    
    def test_length_mark_mapping(self) -> None:
        """Verifica mapeo de dos puntos a marca de longitud."""
        text = "a:b"
        result = normalize_unicode(text)
        assert result == "aːb"
    
    def test_strip_invisible_chars(self) -> None:
        """Verifica eliminación de caracteres invisibles."""
        text = "a\u200bb\ufffec"
        result = normalize_unicode(text)
        assert result == "abc"
    
    def test_preserve_valid_ipa(self) -> None:
        """Verifica que símbolos IPA válidos se preserven."""
        text = "ˈhɛloʊ"
        result = normalize_unicode(text)
        assert result == "ˈhɛloʊ"


class TestDecomposeBaseAndDiacritics:
    """Tests para descomposición de diacríticos."""
    
    def test_simple_char(self) -> None:
        """Carácter sin diacríticos."""
        base, diacritics = decompose_to_base_and_diacritics("a")
        assert base == "a"
        assert diacritics == []
    
    def test_char_with_diacritic(self) -> None:
        """Carácter con diacrítico combinado."""
        # ã = a + combining tilde
        base, diacritics = decompose_to_base_and_diacritics("ã")
        assert base == "a"
        assert len(diacritics) == 1
    
    def test_empty_string(self) -> None:
        """Cadena vacía."""
        base, diacritics = decompose_to_base_and_diacritics("")
        assert base == ""
        assert diacritics == []


class TestInventory:
    """Tests para carga de inventarios."""
    
    @pytest.fixture
    def sample_inventory_yaml(self, tmp_path: Path) -> Path:
        """Crear archivo de inventario temporal."""
        content = """
version: 1
language: en
accent: en-us
description: "Test inventory"
inventory:
  consonants:
    - p
    - b
    - t
    - d
    - k
    - g
  vowels:
    - i
    - e
    - a
    - o
    - u
  diphthongs:
    - aɪ
    - aʊ
  diacritics:
    - ː
    - ˈ
  suprasegmentals:
    - .
"""
        file_path = tmp_path / "inventory.yaml"
        file_path.write_text(content, encoding="utf-8")
        return file_path
    
    def test_load_from_yaml(self, sample_inventory_yaml: Path) -> None:
        """Verifica carga de inventario desde YAML."""
        inv = Inventory.from_yaml(sample_inventory_yaml)
        assert inv.language == "en"
        assert inv.accent == "en-us"
        assert "p" in inv.consonants
        assert "a" in inv.vowels
    
    def test_is_valid_phone(self, sample_inventory_yaml: Path) -> None:
        """Verifica validación de fonemas."""
        inv = Inventory.from_yaml(sample_inventory_yaml)
        assert inv.is_valid_phone("p") is True
        assert inv.is_valid_phone("a") is True
        assert inv.is_valid_phone("aɪ") is True
        assert inv.is_valid_phone("x") is False
    
    def test_is_valid_symbol(self, sample_inventory_yaml: Path) -> None:
        """Verifica validación de símbolos."""
        inv = Inventory.from_yaml(sample_inventory_yaml)
        assert inv.is_valid_symbol("ː") is True
        assert inv.is_valid_symbol("ˈ") is True
        assert inv.is_valid_symbol("~") is False
    
    def test_get_oov_phones(self, sample_inventory_yaml: Path) -> None:
        """Verifica detección de tokens OOV."""
        inv = Inventory.from_yaml(sample_inventory_yaml)
        oov = inv.get_oov_phones(["p", "a", "x", "z"])
        assert "x" in oov
        assert "z" in oov
        assert "p" not in oov
    
    def test_missing_file_raises(self) -> None:
        """Verifica error al cargar archivo inexistente."""
        with pytest.raises(Exception):
            Inventory.from_yaml(Path("/nonexistent/path.yaml"))


class TestIPANormalizer:
    """Tests para el normalizador IPA."""
    
    @pytest.fixture
    def normalizer(self) -> IPANormalizer:
        """Normalizer sin inventario."""
        return IPANormalizer()
    
    @pytest.fixture
    def inventory(self, tmp_path: Path) -> Inventory:
        """Inventario de prueba."""
        content = """
language: es
inventory:
  consonants: [p, b, t, d, k, g, f, s, m, n, l, r]
  vowels: [a, e, i, o, u]
"""
        file_path = tmp_path / "inv.yaml"
        file_path.write_text(content, encoding="utf-8")
        return Inventory.from_yaml(file_path)
    
    @pytest.mark.asyncio
    async def test_normalize_basic(self, normalizer: IPANormalizer) -> None:
        """Normalización básica sin inventario."""
        tokens = ["h", "o", "l", "a"]
        result = await normalizer.normalize(tokens)
        assert result == ["h", "o", "l", "a"]
    
    @pytest.mark.asyncio
    async def test_normalize_strips_empty(self, normalizer: IPANormalizer) -> None:
        """Tokens vacíos se eliminan."""
        tokens = ["h", "", "o", "  ", "l", "a"]
        result = await normalizer.normalize(tokens)
        assert result == ["h", "o", "l", "a"]
    
    @pytest.mark.asyncio
    async def test_normalize_with_inventory(
        self, normalizer: IPANormalizer, inventory: Inventory
    ) -> None:
        """Normalización con inventario marca OOV."""
        normalizer.set_inventory(inventory)
        tokens = ["o", "l", "a", "x"]  # 'x' no está en inventario
        result = await normalizer.normalize(tokens)
        assert "<?>" in result[-1]  # Marcado como OOV
    
    @pytest.mark.asyncio
    async def test_collapse_allophones(self, normalizer: IPANormalizer) -> None:
        """Colapso de alófonos según reglas."""
        normalizer.load_allophone_rules(SPANISH_ALLOPHONE_RULES)
        tokens = ["a", "β", "e", "ð", "o"]
        result = await normalizer.collapse_allophones(tokens)
        assert result == ["a", "b", "e", "d", "o"]
    
    def test_normalize_sync(self, normalizer: IPANormalizer) -> None:
        """Versión síncrona funciona correctamente."""
        tokens = ["h", "o", "l", "a"]
        result = normalizer.normalize_sync(tokens)
        assert result == ["h", "o", "l", "a"]
    
    @pytest.mark.asyncio
    async def test_validate_tokens_no_inventory(
        self, normalizer: IPANormalizer
    ) -> None:
        """Sin inventario, todos los tokens son válidos."""
        result = await normalizer.validate_tokens(["a", "b", "c"])
        assert result["valid"] is True
    
    @pytest.mark.asyncio
    async def test_validate_tokens_with_inventory(
        self, normalizer: IPANormalizer, inventory: Inventory
    ) -> None:
        """Con inventario, detecta OOV."""
        normalizer.set_inventory(inventory)
        result = await normalizer.validate_tokens(["a", "x", "z"])
        assert result["valid"] is False
        assert "x" in result["oov_tokens"]
        assert "z" in result["oov_tokens"]


class TestAllophoneRules:
    """Tests para reglas de colapso alofónico predefinidas."""
    
    def test_spanish_rules_exist(self) -> None:
        """Verifica que existen reglas para español."""
        assert "β" in SPANISH_ALLOPHONE_RULES
        assert "ð" in SPANISH_ALLOPHONE_RULES
        assert "ɣ" in SPANISH_ALLOPHONE_RULES
    
    def test_english_rules_exist(self) -> None:
        """Verifica que existen reglas para inglés."""
        assert "ɾ" in ENGLISH_ALLOPHONE_RULES
        assert "ɫ" in ENGLISH_ALLOPHONE_RULES
