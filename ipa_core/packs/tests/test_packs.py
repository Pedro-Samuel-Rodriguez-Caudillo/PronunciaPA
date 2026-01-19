"""Tests para validar estructura y contenido de language packs.

UPDATED: Ahora usan plugins/language_packs/ con manifest.yaml.
"""
from __future__ import annotations

import pytest
from pathlib import Path
import yaml


PACKS_DIR = Path(__file__).parent.parent.parent.parent / "plugins" / "language_packs"


class TestPackStructure:
    """Tests para verificar estructura de packs."""
    
    def test_packs_directory_exists(self) -> None:
        """Directorio de packs existe."""
        assert PACKS_DIR.exists(), f"Packs dir not found: {PACKS_DIR}"
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_pack_directory_exists(self, pack_id: str) -> None:
        """Cada pack tiene su directorio."""
        pack_dir = PACKS_DIR / pack_id
        assert pack_dir.exists(), f"Pack {pack_id} not found"
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_pack_has_manifest(self, pack_id: str) -> None:
        """Cada pack tiene manifest.yaml."""
        manifest = PACKS_DIR / pack_id / "manifest.yaml"
        assert manifest.exists(), f"Missing manifest.yaml for {pack_id}"
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_pack_has_inventory(self, pack_id: str) -> None:
        """Cada pack tiene inventory.yaml."""
        inventory = PACKS_DIR / pack_id / "inventory.yaml"
        assert inventory.exists(), f"Missing inventory.yaml for {pack_id}"


class TestPackManifest:
    """Tests para validar contenido de manifest.yaml."""
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_manifest_valid_yaml(self, pack_id: str) -> None:
        """Manifest es YAML válido."""
        manifest_path = PACKS_DIR / pack_id / "manifest.yaml"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_manifest_required_fields(self, pack_id: str) -> None:
        """Manifest tiene campos requeridos."""
        manifest_path = PACKS_DIR / pack_id / "manifest.yaml"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        required = ["id", "version", "language", "inventory"]
        for field in required:
            assert field in data, f"Missing field {field} in {pack_id}"
    
    @pytest.mark.parametrize("pack_id,expected_lang", [
        ("en-us", "en"),
        ("es-mx", "es"),
    ])
    def test_manifest_language(self, pack_id: str, expected_lang: str) -> None:
        """Manifest tiene idioma correcto."""
        manifest_path = PACKS_DIR / pack_id / "manifest.yaml"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["language"] == expected_lang


class TestPackInventory:
    """Tests para validar inventory.yaml."""
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_inventory_valid_yaml(self, pack_id: str) -> None:
        """Inventory es YAML válido."""
        inv_path = PACKS_DIR / pack_id / "inventory.yaml"
        with open(inv_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_inventory_has_phones(self, pack_id: str) -> None:
        """Inventory tiene consonantes y vocales."""
        inv_path = PACKS_DIR / pack_id / "inventory.yaml"
        with open(inv_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        inv = data.get("inventory", {})
        assert "consonants" in inv, f"Missing consonants in {pack_id}"
        assert "vowels" in inv, f"Missing vowels in {pack_id}"
        assert len(inv["consonants"]) > 0
        assert len(inv["vowels"]) > 0
    
    def test_es_mx_has_spanish_phones(self) -> None:
        """es-mx tiene fonemas españoles específicos."""
        inv_path = PACKS_DIR / "es-mx" / "inventory.yaml"
        with open(inv_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        consonants = data["inventory"]["consonants"]
        assert "ɲ" in consonants, "Missing ñ sound"
        assert "ɾ" in consonants, "Missing tap r"


class TestPackScoring:
    """Tests para perfiles de scoring."""
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_scoring_directory_exists(self, pack_id: str) -> None:
        """Pack tiene directorio scoring/."""
        scoring_dir = PACKS_DIR / pack_id / "scoring"
        assert scoring_dir.exists(), f"Missing scoring/ for {pack_id}"
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    @pytest.mark.parametrize("mode", ["casual", "objective", "phonetic"])
    def test_scoring_modes_exist(self, pack_id: str, mode: str) -> None:
        """Cada pack tiene profiles para los 3 modos."""
        mode_file = PACKS_DIR / pack_id / "scoring" / f"{mode}.yaml"
        assert mode_file.exists(), f"Missing {mode}.yaml for {pack_id}"
