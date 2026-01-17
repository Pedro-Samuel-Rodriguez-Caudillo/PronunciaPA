"""Tests for rich output in the CLI."""
from __future__ import annotations
import pytest
from typer.testing import CliRunner
from tests.utils.audio import write_sine_wave
from ipa_core.interfaces.cli import app

runner = CliRunner()

@pytest.fixture(autouse=True)
def _isolate_cli_config(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PRONUNCIAPA_CONFIG", raising=False)
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    monkeypatch.setenv("PRONUNCIAPA_TEXTREF", "grapheme")

def test_compare_table_output(monkeypatch, tmp_path) -> None:
    """Verifica que el comando compare genera una tabla por defecto."""
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    wav_path = write_sine_wave(tmp_path / "compare.table.wav")
    result = runner.invoke(app, ["compare", "--audio", wav_path, "--text", "hola"])
    assert result.exit_code == 0
    assert "Referencia" in result.output
    assert "Hipótesis" in result.output
    assert "Operación" in result.output

def test_compare_json_output(monkeypatch, tmp_path) -> None:
    """Verifica que el comando compare genera JSON con el flag --format json."""
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    wav_path = write_sine_wave(tmp_path / "compare.json.wav")
    result = runner.invoke(app, ["compare", "--audio", wav_path, "--text", "hola", "--format", "json"])
    assert result.exit_code == 0
    # Rich print_json output usually contains "per"
    assert '"per":' in result.output

def test_compare_aligned_output(monkeypatch, tmp_path) -> None:
    """Verifica que el comando compare genera texto alineado con el flag --format aligned."""
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    wav_path = write_sine_wave(tmp_path / "compare.aligned.wav")
    result = runner.invoke(app, ["compare", "--audio", wav_path, "--text", "hola", "--format", "aligned"])
    assert result.exit_code == 0
    assert "REF:" in result.output
    assert "HYP:" in result.output
