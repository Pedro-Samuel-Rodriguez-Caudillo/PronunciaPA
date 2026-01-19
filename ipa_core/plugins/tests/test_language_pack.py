"""Tests para LanguagePackPlugin."""
from __future__ import annotations

import pytest
from pathlib import Path

from ipa_core.plugins.language_pack import (
    LanguagePackPlugin,
    ScoringProfile,
    LanguagePackManifest,
)
from ipa_core.errors import NotReadyError, ValidationError


PACKS_DIR = Path(__file__).parent.parent.parent.parent / "plugins" / "language_packs"


class TestScoringProfile:
    """Tests para ScoringProfile."""
    
    def test_default_casual(self) -> None:
        """Perfil casual por defecto."""
        profile = ScoringProfile.default("casual")
        assert profile.mode == "casual"
        assert profile.tolerance == "high"
        assert profile.allophone_error_weight < 0.5
    
    def test_default_phonetic(self) -> None:
        """Perfil phonetic por defecto."""
        profile = ScoringProfile.default("phonetic")
        assert profile.mode == "phonetic"
        assert profile.tolerance == "low"
        assert profile.allophone_error_weight > 0.5


class TestLanguagePackPlugin:
    """Tests para LanguagePackPlugin."""
    
    @pytest.fixture
    def es_mx_pack(self) -> LanguagePackPlugin:
        """Pack de español mexicano."""
        return LanguagePackPlugin(PACKS_DIR / "es-mx")
    
    @pytest.mark.asyncio
    async def test_not_ready_before_setup(self, es_mx_pack: LanguagePackPlugin) -> None:
        """Error si se usa antes de setup."""
        with pytest.raises(NotReadyError):
            _ = es_mx_pack.id
    
    @pytest.mark.asyncio
    async def test_setup_loads_manifest(self, es_mx_pack: LanguagePackPlugin) -> None:
        """Setup carga el manifest."""
        await es_mx_pack.setup()
        assert es_mx_pack.id == "es-mx"
        assert es_mx_pack.language == "es"
    
    @pytest.mark.asyncio
    async def test_setup_loads_inventory(self, es_mx_pack: LanguagePackPlugin) -> None:
        """Setup carga el inventario."""
        await es_mx_pack.setup()
        inv = es_mx_pack.get_inventory()
        assert inv.is_phoneme("b")
        assert inv.is_phoneme("a")
    
    @pytest.mark.asyncio
    async def test_setup_loads_grammar(self, es_mx_pack: LanguagePackPlugin) -> None:
        """Setup carga la gramática."""
        await es_mx_pack.setup()
        grammar = es_mx_pack.get_grammar()
        assert len(grammar.rules) > 0
    
    @pytest.mark.asyncio
    async def test_setup_loads_scoring(self, es_mx_pack: LanguagePackPlugin) -> None:
        """Setup carga perfiles de scoring."""
        await es_mx_pack.setup()
        casual = es_mx_pack.get_scoring_profile("casual")
        assert casual.tolerance == "high"
    
    @pytest.mark.asyncio
    async def test_derive(self, es_mx_pack: LanguagePackPlugin) -> None:
        """derive() transforma fonémico a fonético."""
        await es_mx_pack.setup()
        result = es_mx_pack.derive("dedo")
        # d intervocálica → ð
        assert "ð" in result
    
    @pytest.mark.asyncio
    async def test_collapse(self, es_mx_pack: LanguagePackPlugin) -> None:
        """collapse() transforma fonético a fonémico."""
        await es_mx_pack.setup()
        result = es_mx_pack.collapse("[ˈka.sa]")
        assert result == "kasa"
    
    @pytest.mark.asyncio
    async def test_get_exception(self, es_mx_pack: LanguagePackPlugin) -> None:
        """get_exception() retorna IPA para palabras irregulares."""
        await es_mx_pack.setup()
        result = es_mx_pack.get_exception("méxico")
        assert result == "ˈmexiko"
    
    @pytest.mark.asyncio
    async def test_teardown(self, es_mx_pack: LanguagePackPlugin) -> None:
        """teardown() libera recursos."""
        await es_mx_pack.setup()
        await es_mx_pack.teardown()
        with pytest.raises(NotReadyError):
            _ = es_mx_pack.id


class TestLanguagePackManifest:
    """Tests para LanguagePackManifest."""
    
    def test_from_yaml(self) -> None:
        """Cargar manifest desde YAML."""
        manifest_path = PACKS_DIR / "es-mx" / "manifest.yaml"
        if manifest_path.exists():
            manifest = LanguagePackManifest.from_yaml(manifest_path)
            assert manifest.id == "es-mx"
            assert manifest.language == "es"
