"""Pruebas de contrato para configuración (stubs)."""
from __future__ import annotations

import pytest

from ipa_core.config import loader, schema


def test_app_config_keys() -> None:
    ac = schema.AppConfig(  # type: ignore[call-arg]
        version=1,
        preprocessor={"name": "default", "params": {}},
        backend={"name": "mock", "params": {}},
        textref={"name": "mock", "params": {}},
        comparator={"name": "mock", "params": {}},
        options={"lang": "es", "output": "json"},
    )
    assert set(ac.keys()) >= {"version", "backend", "textref", "comparator", "preprocessor", "options"}


def test_loader_is_stub() -> None:
    with pytest.raises(NotImplementedError):
        _ = loader.load_config("config/ipa_kernel.yaml")

