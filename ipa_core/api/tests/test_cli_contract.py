"""Pruebas de contrato para la CLI (stubs).

Objetivo: confirmar existencia de la función y el contrato.
"""
from __future__ import annotations

import pytest

from ipa_core.api import cli


def test_cli_compare_exists_and_is_stub() -> None:
    assert hasattr(cli, "cli_compare")
    with pytest.raises(NotImplementedError):
        cli.cli_compare(audio="/tmp/a.wav", text="hola", lang="es")

