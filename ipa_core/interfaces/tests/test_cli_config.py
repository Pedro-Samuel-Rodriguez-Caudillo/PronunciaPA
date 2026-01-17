"""Pruebas de integración del CLI con la configuración."""
from __future__ import annotations
import os
import pytest
from tests.utils.audio import write_sine_wave
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app

runner = CliRunner()

def test_cli_works_with_no_config(monkeypatch, tmp_path) -> None:
    """Verifica que el CLI funciona sin archivo de configuración (usa defaults)."""
    monkeypatch.delenv("PRONUNCIAPA_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    wav_path = write_sine_wave(tmp_path / "no_config.wav")
    # Usamos un audio temporal válido y el stub
    # Pero Allosaurus no está instalado, así que usaremos el stub manualmente
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    result = runner.invoke(app, ["transcribe", "--audio", wav_path])
    
    assert result.exit_code == 0
    assert "IPA (es): h o l a" in result.output


def test_cli_handles_malformed_config(tmp_path, monkeypatch) -> None:
    """Verifica que el CLI muestra un error amigable con YAML malformado."""
    bad_cfg = tmp_path / "bad_config.yaml"
    bad_cfg.write_text("version: 'not-an-int'\nbackend: {name: 123}")
    
    monkeypatch.setenv("PRONUNCIAPA_CONFIG", str(bad_cfg))
    
    wav_path = write_sine_wave(tmp_path / "malformed.wav")
    result = runner.invoke(app, ["transcribe", "--audio", wav_path])
    assert result.exit_code == 1
    assert "Error en la configuración" in result.output
    # Pydantic 2 might show the error message without the exact bracket format
    assert "Input should be a valid integer" in result.output
    assert "Input should be a valid string" in result.output

def test_cli_handles_missing_env_config(monkeypatch, tmp_path) -> None:
    """Verifica error claro si PRONUNCIAPA_CONFIG apunta a nada."""
    monkeypatch.setenv("PRONUNCIAPA_CONFIG", "missing_file.yaml")

    wav_path = write_sine_wave(tmp_path / "missing_config.wav")
    result = runner.invoke(app, ["transcribe", "--audio", wav_path])
    assert result.exit_code == 1
    assert "Error: Archivo PRONUNCIAPA_CONFIG no encontrado" in result.output

def test_cli_transcribe_with_config_path(tmp_path) -> None:
    """Verifica que --config se respeta en CLI."""
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "version: 1\n"
        "backend:\n"
        "  name: stub\n"
        "  params:\n"
        "    stub_tokens: ['x','y']\n"
        "textref: {name: 'grapheme'}\n"
        "comparator: {name: 'levenshtein'}\n"
        "preprocessor: {name: 'basic'}\n"
    )
    wav_path = write_sine_wave(tmp_path / "config_audio.wav")
    result = runner.invoke(app, ["transcribe", "--config", str(cfg_path), "--audio", wav_path])
    assert result.exit_code == 0
    assert "IPA (es): x y" in result.output
