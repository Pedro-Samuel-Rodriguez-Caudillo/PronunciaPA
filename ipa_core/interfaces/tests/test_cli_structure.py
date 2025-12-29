"""Tests for the CLI command structure."""
from __future__ import annotations
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app

runner = CliRunner()

def test_cli_help_shows_commands() -> None:
    """Verifica que los comandos principales aparecen en la ayuda."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "transcribe" in result.output
    assert "compare" in result.output
    assert "config" in result.output
    assert "plugin" in result.output

def test_config_command_exists() -> None:
    """Verifica que el comando config existe."""
    result = runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0

def test_plugin_command_exists() -> None:
    """Verifica que el comando plugin existe."""
    result = runner.invoke(app, ["plugin", "--help"])
    assert result.exit_code == 0
