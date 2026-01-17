import pytest
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app
from unittest.mock import patch

runner = CliRunner()

def test_plugin_list_enhanced():
    """Should display a table with category, name, version and author."""
    with patch("ipa_core.plugins.discovery.iter_plugin_entry_points") as mock_iter, \
         patch("ipa_core.plugins.discovery.get_package_metadata") as mock_meta:
        
        from unittest.mock import MagicMock
        ep = MagicMock()
        ep.name = "asr.test_asr"
        ep.value = "test_pkg.asr:MyASR"
        
        mock_iter.return_value = [("asr", "test_asr", ep)]
        mock_meta.return_value = {
            "version": "1.2.3",
            "author": "Test Author",
            "description": "Test Desc"
        }
        
        result = runner.invoke(app, ["plugin", "list"])
        
        assert result.exit_code == 0
        assert "asr" in result.stdout
        assert "test_asr" in result.stdout
        assert "1.2.3" in result.stdout
        assert "Test Author" in result.stdout
        assert "Enabled" in result.stdout or "Installed" in result.stdout

def test_plugin_info_not_found():
    """Should show error when plugin not found."""
    with patch("ipa_core.plugins.discovery.get_plugin_details") as mock_details:
        mock_details.return_value = {}
        result = runner.invoke(app, ["plugin", "info", "asr", "ghost"])
        assert result.exit_code != 0
        assert "Error" in result.stdout

def test_plugin_info_success():
    """Should show detailed info for a plugin."""
    with patch("ipa_core.plugins.discovery.get_plugin_details") as mock_details:
        mock_details.return_value = {
            "name": "my_plugin",
            "category": "asr",
            "version": "0.1.0",
            "author": "Me",
            "description": "My special plugin",
            "entry_point": "pkg.mod:Class"
        }
        result = runner.invoke(app, ["plugin", "info", "asr", "my_plugin"])
        assert result.exit_code == 0
        assert "my_plugin" in result.stdout
        assert "ASR" in result.stdout
        assert "My special plugin" in result.stdout

def test_plugin_validate_cli():
    """Should report validation status for plugins."""
    with patch("ipa_core.plugins.discovery.iter_plugin_entry_points") as mock_iter, \
         patch("ipa_core.plugins.registry.validate_plugin") as mock_val:
        
        from unittest.mock import MagicMock
        ep = MagicMock()
        ep.name = "asr.test_asr"
        ep.load.return_value = object # fake class
        
        mock_iter.return_value = [("asr", "test_asr", ep)]
        mock_val.return_value = (False, ["Missing transcribe"])
        
        result = runner.invoke(app, ["plugin", "validate"])
        assert result.exit_code == 0
        assert "INVALID" in result.stdout
        assert "Missing transcribe" in result.stdout

