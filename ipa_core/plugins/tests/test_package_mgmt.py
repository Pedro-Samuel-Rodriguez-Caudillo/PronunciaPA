import pytest
import subprocess
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app
from unittest.mock import patch, MagicMock

runner = CliRunner()

@patch("subprocess.run")
def test_plugin_install_success_not_plugin(mock_run):
    """Should install via pip but warn if not a plugin."""
    mock_run.return_value = MagicMock(returncode=0)
    
    with patch("ipa_core.plugins.discovery.iter_plugin_entry_points") as mock_iter:
        mock_iter.return_value = [] # No plugins found after install
        
        result = runner.invoke(app, ["plugin", "install", "dummy-package"])
        
        assert result.exit_code == 0
        assert "Instalación de 'dummy-package' completada" in result.stdout
        assert "WARNING" in result.stdout
        assert "no parece registrar ningún plugin" in result.stdout
        mock_run.assert_called_once()

@patch("subprocess.run")
def test_plugin_install_fail(mock_run):
    """Should report error if pip fails."""
    # Simulate subprocess.run raising CalledProcessError when check=True
    mock_run.side_effect = subprocess.CalledProcessError(1, ["pip", "install"], stderr="Pip failed")
    
    result = runner.invoke(app, ["plugin", "install", "bad-package"])
    assert result.exit_code != 0
    assert "Error" in result.stdout
    assert "Pip failed" in result.stdout

@patch("subprocess.run")
def test_plugin_uninstall_cancel(mock_run):
    """Should not uninstall if user cancels."""
    result = runner.invoke(app, ["plugin", "uninstall", "any-package"], input="n\n")
    assert "Operación cancelada" in result.stdout
    mock_run.assert_not_called()

@patch("subprocess.run")
def test_plugin_uninstall_confirm(mock_run):
    """Should uninstall if user confirms."""
    mock_run.return_value = MagicMock(returncode=0)
    result = runner.invoke(app, ["plugin", "uninstall", "any-package"], input="y\n")
    assert "El paquete 'any-package' ha sido desinstalado" in result.stdout
    mock_run.assert_called_once()

def test_plugin_uninstall_protected():
    """Should refuse to uninstall protected packages."""
    result = runner.invoke(app, ["plugin", "uninstall", "ipa-core"], input="y\n")
    assert result.exit_code != 0
    assert "Error" in result.stdout
    assert "Cannot uninstall protected package" in result.stdout
