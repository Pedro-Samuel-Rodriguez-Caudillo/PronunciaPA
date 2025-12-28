"""Tests para el formateo amigable de errores de validación."""
from __future__ import annotations
import pytest
from pydantic import ValidationError
from ipa_core.config.schema import AppConfig
from ipa_core.config.loader import format_validation_error

def test_format_validation_error_missing_field() -> None:
    """Verifica el formato para campos faltantes (si los hubiera, aunque ahora hay defaults)."""
    # Forzamos un error de tipo para probar el formateo
    try:
        AppConfig(version="not-a-number")
    except ValidationError as e:
        msg = format_validation_error(e)
        assert "version" in msg
        assert "integer" in msg.lower() # Pydantic 2 says 'integer' instead of 'number'


def test_format_validation_error_nested_field() -> None:
    """Verifica el formato para errores en campos anidados."""
    try:
        AppConfig(backend={"params": "not-a-dict"}) # 'name' is missing and 'params' is wrong type
    except ValidationError as e:
        msg = format_validation_error(e)
        assert "backend" in msg
        assert "params" in msg
        assert "dict" in msg.lower()
