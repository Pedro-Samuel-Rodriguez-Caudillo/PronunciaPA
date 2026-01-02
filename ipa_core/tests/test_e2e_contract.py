"""Prueba de contrato de extremo a extremo (CLI + Config + Kernel Stub)."""
from __future__ import annotations
import os
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app
from tests.utils.audio import write_sine_wave

runner = CliRunner()

def test_cli_transcribe_e2e(tmp_path) -> None:
    """Verifica que el CLI acepta una config y ejecuta transcribe."""
    config_content = """
version: 1
preprocessor: {name: 'basic'}
backend: {name: 'stub'}
textref: {name: 'grapheme'}
comparator: {name: 'levenshtein'}
"""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(config_content)
    
    # Simular que pasamos la config por variable de entorno
    os.environ["PRONUNCIAPA_CONFIG"] = str(cfg_file)
    try:
        wav_path = write_sine_wave(tmp_path / "e2e_transcribe.wav")
        result = runner.invoke(app, ["transcribe", "--audio", wav_path, "--json"])
        assert result.exit_code == 0
        assert '"tokens"' in result.stdout
    finally:
        del os.environ["PRONUNCIAPA_CONFIG"]

def test_cli_compare_e2e(tmp_path) -> None:
    """Verifica que el CLI acepta una config y ejecuta compare."""
    config_content = "version: 1\nbackend: {name: 'stub'}\ntextref: {name: 'grapheme'}\ncomparator: {name: 'levenshtein'}\npreprocessor: {name: 'basic'}"
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(config_content)
    
    os.environ["PRONUNCIAPA_CONFIG"] = str(cfg_file)
    try:
        wav_path = write_sine_wave(tmp_path / "e2e_compare.wav")
        result = runner.invoke(app, ["compare", "--audio", wav_path, "--text", "hola", "--format", "json"])
        assert result.exit_code == 0
        assert '"per"' in result.stdout
    finally:
        del os.environ["PRONUNCIAPA_CONFIG"]
