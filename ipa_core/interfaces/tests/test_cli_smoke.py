"""Smoke tests for the CLI."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner
from ipa_core.interfaces.cli import app

runner = CliRunner()


def test_cli_version_smoke():
    """Verify the CLI can be invoked and help is shown."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "PronunciaPA" in result.output


def test_cli_plugin_list_smoke():
    """Verify the plugin list command works."""
    result = runner.invoke(app, ["plugin", "list"])
    assert result.exit_code == 0
    assert "Plugins Registrados" in result.output


def test_cli_config_show_smoke():
    """Verify the config show command works."""
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert '"version"' in result.output
