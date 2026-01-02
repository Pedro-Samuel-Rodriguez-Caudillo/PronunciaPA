import pytest
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app
from unittest.mock import patch, AsyncMock

runner = CliRunner()

def test_models_list_empty():
    """Should inform when no models are found."""
    with patch("ipa_core.plugins.models.storage.scan_models") as mock_scan:
        mock_scan.return_value = []
        # Note: We assume the command group will be 'models'
        result = runner.invoke(app, ["models", "list"])
        # Expecting failure initially as command group doesn't exist # Passed the "fail first" criteria for TDD
        
        assert result.exit_code == 0
        assert "No se encontraron modelos locales" in result.stdout

def test_models_list_populated():
    """Should list found models."""
    with patch("ipa_core.plugins.models.storage.scan_models") as mock_scan:
        mock_scan.return_value = ["es-base", "en-fast"]
        result = runner.invoke(app, ["models", "list"])
        

        assert result.exit_code == 0
        assert "es-base" in result.stdout
        assert "en-fast" in result.stdout

def test_models_download_success():
    """Should call download_model successfully."""
    with patch("ipa_core.plugins.model_manager.ModelManager.download_model", new_callable=AsyncMock) as mock_dl:
        result = runner.invoke(app, ["models", "download", "http://example.com/model.zip", "my-model"])
        

        assert result.exit_code == 0
        assert "completada" in result.stdout
        mock_dl.assert_awaited_once()

def test_models_download_fail():
    """Should handle download errors gracefully."""
    with patch("ipa_core.plugins.model_manager.ModelManager.download_model", new_callable=AsyncMock) as mock_dl:
        mock_dl.side_effect = ValueError("Hash mismatch")
        result = runner.invoke(app, ["models", "download", "http://bad.com/model.zip", "bad-model"])
        

        assert result.exit_code != 0
        assert "Error" in result.stdout
        assert "Hash mismatch" in result.stdout
