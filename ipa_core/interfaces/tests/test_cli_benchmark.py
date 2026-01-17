import pytest
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app
from unittest.mock import patch, MagicMock, AsyncMock

runner = CliRunner()

def test_benchmark_command_file_not_found(tmp_path):
    """Should fail gracefully if dataset doesn't exist."""
    result = runner.invoke(app, ["benchmark", "--dataset", "ghost.jsonl"])
    assert result.exit_code != 0
    assert "no encontrado" in result.stdout or "Error" in result.stdout

def test_benchmark_command_execution(tmp_path):
    """Should run benchmark and print table."""
    # 1. Create dummy manifest
    manifest_path = tmp_path / "data.jsonl"
    manifest_path.write_text('{"audio": "a.wav", "text": "h"}\n', encoding="utf-8")
    
    # 2. Mock DatasetLoader
    with patch("ipa_core.testing.benchmark.DatasetLoader.load_manifest") as mock_load:
        mock_load.return_value = [{"audio": "a.wav", "text": "h"}]
        
        # 3. Mock Kernel and pipeline
        with patch("ipa_core.interfaces.cli._get_kernel") as mock_get_kernel:
            # Need to mock the Kernel object, specifically setup, teardown and run
            mock_kernel = MagicMock()
            mock_kernel.setup = AsyncMock()
            mock_kernel.teardown = AsyncMock()
            mock_kernel.run = AsyncMock()
            mock_get_kernel.return_value = mock_kernel
            
            mock_kernel.run.return_value = {
                "per": 0.1,
                "meta": {"duration": 1.0} 
            }
            
            # Need to mock audio helpers since file won't exist
            with patch("ipa_core.interfaces.cli.ensure_wav") as mock_ensure, \
                patch("ipa_core.interfaces.cli.to_audio_input") as mock_audio, \
                patch("ipa_core.interfaces.cli.wav_duration") as mock_duration:
                mock_ensure.return_value = ("a.wav", False)
                mock_audio.return_value = {"path": "a.wav", "sample_rate": 16000, "channels": 1}
                mock_duration.return_value = 1.0

                result = runner.invoke(app, ["benchmark", "--dataset", str(manifest_path)])
            
                if result.exit_code != 0:
                    print(result.output)
            
                assert result.exit_code == 0
                assert "Benchmark" in result.stdout
                assert "PER" in result.stdout
