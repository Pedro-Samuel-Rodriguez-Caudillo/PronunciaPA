"""Pruebas de contrato para el CLI."""
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

def test_cli_help() -> None:
    """Verifica que el comando help funciona."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "transcribe" in result.stdout
    assert "compare" in result.stdout

def test_cli_transcribe_json(tmp_path) -> None:
    """Verifica el stub del comando transcribe con JSON."""
    wav_path = write_sine_wave(tmp_path / "transcribe.json.wav")
    result = runner.invoke(app, ["transcribe", "--audio", wav_path, "--lang", "es", "--json"])
    assert result.exit_code == 0
    assert '"tokens"' in result.stdout

def test_cli_transcribe_text(tmp_path) -> None:
    """Verifica el stub del comando transcribe con texto plano."""
    wav_path = write_sine_wave(tmp_path / "transcribe.text.wav")
    result = runner.invoke(app, ["transcribe", "--audio", wav_path, "--lang", "es"])
    assert result.exit_code == 0
    assert "IPA (es):" in result.stdout

def test_cli_transcribe_missing_input() -> None:
    """Verifica error cuando falta el audio."""
    result = runner.invoke(app, ["transcribe"])
    assert result.exit_code == 1
    assert "Error: Debes especificar --audio o --mic" in result.stdout

def test_cli_compare_json(tmp_path) -> None:
    """Verifica el stub del comando compare con JSON."""
    wav_path = write_sine_wave(tmp_path / "compare.json.wav")
    result = runner.invoke(app, ["compare", "--audio", wav_path, "--text", "hola", "--lang", "es", "--format", "json"])
    assert result.exit_code == 0
    assert '"per"' in result.stdout

def test_cli_compare_text(tmp_path) -> None:
    """Verifica el stub del comando compare con texto plano."""
    wav_path = write_sine_wave(tmp_path / "compare.text.wav")
    result = runner.invoke(app, ["compare", "--audio", wav_path, "--text", "hola", "--lang", "es"])
    assert result.exit_code == 0
    assert "PER:" in result.stdout
