"""Integration tests for the CLI `ipa run` command."""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ipa_core.api.cli import app
from ipa_core.backends.null_backend import NullASRBackend
from ipa_core.compare.levenshtein import LevenshteinComparator
from ipa_core.plugins import PLUGIN_GROUPS
from ipa_core.textref.nop import NoopTextRef


def test_cli_run_generates_reports(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
plugins:
  asr_backend: null
  textref: noop
  comparator: levenshtein
"""
    )

    metadata_path = tmp_path / "metadata.csv"
    metadata_path.write_text(
        "audio_path,text,lang\nfile.wav,Texto de prueba,es\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "reports"

    def fake_loader(group: str, name: str):
        mapping = {
            PLUGIN_GROUPS["asr"].entrypoint_group: {"null": NullASRBackend},
            PLUGIN_GROUPS["textref"].entrypoint_group: {"noop": NoopTextRef},
            PLUGIN_GROUPS["comparator"].entrypoint_group: {
                "levenshtein": LevenshteinComparator
            },
        }
        try:
            return mapping[group][name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Plugin no disponible en pruebas: {group}::{name}") from exc

    monkeypatch.setattr("ipa_core.kernel.load_plugin", fake_loader)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(config_path),
            "--input",
            str(metadata_path),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output

    json_path = output_dir / "report.json"
    csv_path = output_dir / "report.csv"
    assert json_path.exists()
    assert csv_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["procesados"] == 1
    assert "per_global" in payload
    assert payload["detalles"]

    csv_text = csv_path.read_text(encoding="utf-8")
    assert "audio_path" in csv_text
    assert "Reporte CSV generado en" in result.output
