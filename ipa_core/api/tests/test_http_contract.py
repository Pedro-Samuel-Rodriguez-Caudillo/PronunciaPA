"""Pruebas de contrato para la API HTTP (stub)."""
from __future__ import annotations

import pytest

from ipa_core.api import http


def test_http_get_app_stub() -> None:
    assert hasattr(http, "get_app")
    with pytest.raises(NotImplementedError):
        _ = http.get_app()

