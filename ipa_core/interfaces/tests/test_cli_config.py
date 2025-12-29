"""Pruebas de integración del CLI con la configuración."""
from __future__ import annotations
import os
import pytest
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app

runner = CliRunner()

def test_cli_works_with_no_config(monkeypatch) -> None:
    """Verifica que el CLI funciona sin archivo de configuración (usa defaults)."""
    monkeypatch.delenv("PRONUNCIAPA_CONFIG", raising=False)
    # Mock de existencia de archivos para forzar defaults
    with monkeypatch.context() as mp:
        mp.setattr("pathlib.Path.exists", lambda _: False)
        # Usamos un audio que existe (manual_test.wav) y el stub
        # Pero Allosaurus no está instalado, así que usaremos el stub manualmente
        monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
        result = runner.invoke(app, ["transcribe", "--audio", "manual_test.wav"])
        
        assert result.exit_code == 0
        assert "IPA (es): h o l a" in result.output


def test_cli_handles_malformed_config(tmp_path, monkeypatch) -> None:
    """Verifica que el CLI muestra un error amigable con YAML malformado."""
    bad_cfg = tmp_path / "bad_config.yaml"
    bad_cfg.write_text("version: 'not-an-int'\nbackend: {name: 123}")
    
    monkeypatch.setenv("PRONUNCIAPA_CONFIG", str(bad_cfg))
    
    result = runner.invoke(app, ["transcribe", "--audio", "test.wav"])
    assert result.exit_code == 1
    assert "Error en la configuración" in result.output
    # Pydantic 2 might show the error message without the exact bracket format
    assert "Input should be a valid integer" in result.output
    assert "Input should be a valid string" in result.output

def test_cli_handles_missing_env_config(monkeypatch) -> None:
    """Verifica error claro si PRONUNCIAPA_CONFIG apunta a nada."""
    monkeypatch.setenv("PRONUNCIAPA_CONFIG", "missing_file.yaml")
    
    result = runner.invoke(app, ["transcribe", "--audio", "test.wav"])
    assert result.exit_code == 1
    assert "Error: Archivo PRONUNCIAPA_CONFIG no encontrado" in result.output
