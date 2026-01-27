"""Tests for the Ollama LLM adapter."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from ipa_core.llm.ollama import OllamaAdapter


class TestOllamaAdapterInit:
    """Test OllamaAdapter initialization (no external dependencies)."""

    def test_default_params(self):
        """Should use default parameters when none provided."""
        adapter = OllamaAdapter()
        assert adapter._base_url == "http://localhost:11434"
        assert adapter._model == "tinyllama"
        assert adapter._temperature == 0.7
        assert adapter._num_ctx == 4096
        assert adapter._timeout == 120

    def test_custom_params(self):
        """Should accept custom parameters."""
        params = {
            "base_url": "http://custom:8080",
            "model": "phi3:mini",
            "temperature": 0.5,
            "num_ctx": 2048,
            "timeout": 60,
        }
        adapter = OllamaAdapter(params)
        assert adapter._base_url == "http://custom:8080"
        assert adapter._model == "phi3:mini"
        assert adapter._temperature == 0.5
        assert adapter._num_ctx == 2048
        assert adapter._timeout == 60

    def test_env_override(self):
        """Should use OLLAMA_HOST env var if set."""
        with patch.dict("os.environ", {"OLLAMA_HOST": "http://env:9999"}):
            adapter = OllamaAdapter()
            assert adapter._base_url == "http://env:9999"

    def test_params_override_env(self):
        """Explicit params should override env var."""
        with patch.dict("os.environ", {"OLLAMA_HOST": "http://env:9999"}):
            adapter = OllamaAdapter({"base_url": "http://explicit:8080"})
            assert adapter._base_url == "http://explicit:8080"


# Note: Async tests for setup() and complete() require aiohttp.
# They are skipped if aiohttp is not installed.
# To run full tests: pip install aiohttp
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@pytest.mark.skipif(not HAS_AIOHTTP, reason="aiohttp not installed")
class TestOllamaAdapterAsync:
    """Async tests for OllamaAdapter (require aiohttp)."""

    @pytest.mark.asyncio
    async def test_setup_fails_when_server_unreachable(self):
        """Should raise NotReadyError when Ollama is not running."""
        from ipa_core.errors import NotReadyError
        
        adapter = OllamaAdapter({"base_url": "http://localhost:99999"})
        
        with pytest.raises(NotReadyError, match="Cannot connect to Ollama"):
            await adapter.setup()

    @pytest.mark.asyncio
    async def test_complete_fails_when_server_unreachable(self):
        """Should raise ValidationError when server is down."""
        from ipa_core.errors import ValidationError
        
        adapter = OllamaAdapter({
            "base_url": "http://localhost:99999",
            "timeout": 1
        })
        
        with pytest.raises(ValidationError, match="Ollama request failed"):
            await adapter.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_teardown_is_noop(self):
        """Teardown should complete without error."""
        adapter = OllamaAdapter()
        # Should not raise
        await adapter.teardown()
