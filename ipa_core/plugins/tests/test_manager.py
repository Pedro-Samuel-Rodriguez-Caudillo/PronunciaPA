import pytest
from unittest.mock import patch, MagicMock
from ipa_core.plugins.manager import PluginManager, PluginMetadata

class TestPluginManager:
    @patch("ipa_core.plugins.discovery.iter_plugin_entry_points")
    @patch("ipa_core.plugins.discovery.get_package_metadata")
    def test_get_installed_plugins(self, mock_get_meta, mock_iter_eps):
        """Should return a list of PluginMetadata objects."""
        
        # Mock Discovery
        ep1 = MagicMock()
        ep1.value = "my_pkg.module:Class"
        
        # category, name, entry_point
        mock_iter_eps.return_value = [("asr", "test_plugin", ep1)]
        
        # Mock Metadata
        mock_get_meta.return_value = {
            "version": "1.0.0",
            "author": "Tester",
            "description": "A test plugin"
        }
        
        manager = PluginManager()
        plugins = manager.get_installed_plugins()
        
        assert len(plugins) == 1
        p = plugins[0]
        assert isinstance(p, PluginMetadata)
        assert p.name == "test_plugin"
        assert p.category == "asr"
        assert p.version == "1.0.0"
        assert p.author == "Tester"
        assert p.description == "A test plugin"
        assert p.enabled is True  # Default should be true? or managed?

    def test_plugin_metadata_structure(self):
        """Verify PluginMetadata dataclass structure."""
        p = PluginMetadata(
            name="demo",
            category="tts",
            version="0.1",
            author="Me",
            description="Desc",
            entry_point="pkg:cls",
            enabled=False
        )
        assert p.name == "demo"
        assert p.enabled is False
