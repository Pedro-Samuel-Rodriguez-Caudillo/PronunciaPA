"""Contract tests for TextRefProvider plugins."""
from __future__ import annotations

import pytest
from ipa_core.ports.textref import TextRefProvider


class TextRefContract:
    """Base class for TextRefProvider contract tests."""

    @pytest.fixture
    def provider(self) -> TextRefProvider:
        """Should return an instance of the provider being tested."""
        raise NotImplementedError("Subclasses must implement the `provider` fixture.")

    @pytest.mark.asyncio
    async def test_setup_teardown(self, provider: TextRefProvider):
        """Verify setup and teardown lifecycle."""
        await provider.setup()
        await provider.teardown()

    @pytest.mark.asyncio
    async def test_to_ipa_structure(self, provider: TextRefProvider):
        """Verify that to_ipa returns the expected structure."""
        await provider.setup()
        try:
            result = await provider.to_ipa("hola", lang="es")
            
            assert isinstance(result, dict)
            assert "tokens" in result
            assert isinstance(result["tokens"], list)
            for t in result["tokens"]:
                assert isinstance(t, str)
            if "meta" in result:
                assert isinstance(result["meta"], dict)
        finally:
            await provider.teardown()

    @pytest.mark.asyncio
    async def test_to_ipa_empty_text(self, provider: TextRefProvider):
        """Verify that to_ipa handles empty text gracefully."""
        await provider.setup()
        try:
            result = await provider.to_ipa("", lang="es")
            assert "tokens" in result
            assert result["tokens"] == []
        finally:
            await provider.teardown()
