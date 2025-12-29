"""Pruebas de contrato para el CLI."""
from __future__ import annotations
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app

runner = CliRunner()

def test_cli_help() -> None:
    """Verifica que el comando help funciona."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "transcribe" in result.stdout
    assert "compare" in result.stdout

def test_cli_transcribe_json() -> None:
    """Verifica el stub del comando transcribe con JSON."""
    result = runner.invoke(app, ["transcribe", "--audio", "test.wav", "--lang", "es", "--json"])
    assert result.exit_code == 0
    assert '"tokens"' in result.stdout

def test_cli_transcribe_text() -> None:
    """Verifica el stub del comando transcribe con texto plano."""
    result = runner.invoke(app, ["transcribe", "--audio", "test.wav", "--lang", "es"])
    assert result.exit_code == 0
    assert "IPA (es):" in result.stdout

def test_cli_transcribe_missing_input() -> None:
    """Verifica error cuando falta el audio."""
    result = runner.invoke(app, ["transcribe"])
    assert result.exit_code == 1
    assert "Error: Debes especificar --audio o --mic" in result.stdout

def test_cli_compare_json() -> None:
    """Verifica el stub del comando compare con JSON."""
    result = runner.invoke(app, ["compare", "--audio", "test.wav", "--text", "hola", "--lang", "es", "--format", "json"])
    assert result.exit_code == 0
    assert '"per"' in result.stdout

def test_cli_compare_text() -> None:
    """Verifica el stub del comando compare con texto plano."""
    result = runner.invoke(app, ["compare", "--audio", "test.wav", "--text", "hola", "--lang", "es"])
    assert result.exit_code == 0
    assert "PER:" in result.stdout
