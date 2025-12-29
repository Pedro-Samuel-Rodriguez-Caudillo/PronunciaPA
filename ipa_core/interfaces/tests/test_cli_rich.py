"""Tests for rich output in the CLI."""
from __future__ import annotations
import pytest
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app

runner = CliRunner()

def test_compare_table_output(monkeypatch) -> None:
    """Verifica que el comando compare genera una tabla por defecto."""
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    # manual_test.wav fue creado en tracks anteriores
    result = runner.invoke(app, ["compare", "--audio", "manual_test.wav", "--text", "hola"])
    assert result.exit_code == 0
    assert "Referencia" in result.output
    assert "Hipótesis" in result.output
    assert "Operación" in result.output

def test_compare_json_output(monkeypatch) -> None:
    """Verifica que el comando compare genera JSON con el flag --format json."""
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    result = runner.invoke(app, ["compare", "--audio", "manual_test.wav", "--text", "hola", "--format", "json"])
    assert result.exit_code == 0
    # Rich print_json output usually contains "per"
    assert '"per":' in result.output

def test_compare_aligned_output(monkeypatch) -> None:
    """Verifica que el comando compare genera texto alineado con el flag --format aligned."""
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    result = runner.invoke(app, ["compare", "--audio", "manual_test.wav", "--text", "hola", "--format", "aligned"])
    assert result.exit_code == 0
    assert "REF:" in result.output
    assert "HYP:" in result.output
