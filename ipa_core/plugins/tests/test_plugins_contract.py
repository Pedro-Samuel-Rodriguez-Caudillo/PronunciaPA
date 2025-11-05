"""Pruebas de contrato para resolución/descubrimiento de plugins (stubs)."""
from __future__ import annotations

import pytest

from ipa_core.plugins import discovery, registry


def test_discovery_available_plugins_shape() -> None:
    index = discovery.available_plugins()
    assert set(index.keys()) == {"asr", "textref", "comparator", "preprocessor"}


@pytest.mark.parametrize(
    "resolver",
    [
        registry.resolve_asr,
        registry.resolve_textref,
        registry.resolve_comparator,
        registry.resolve_preprocessor,
    ],
)
def test_resolvers_are_stubs(resolver) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(NotImplementedError):
        resolver("mock", {})

