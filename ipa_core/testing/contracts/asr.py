"""Contract tests for ASRBackend plugins."""
from __future__ import annotations

import pytest
from ipa_core.ports.asr import ASRBackend
from ipa_core.types import AudioInput


class ASRContract:
    """Base class for ASRBackend contract tests.
    
    Subclasses must implement the `get_backend` fixture.
    """

    @pytest.fixture
    def backend(self) -> ASRBackend:
        """Should return an instance of the backend being tested."""
        raise NotImplementedError("Subclasses must implement the `backend` fixture.")

    @pytest.mark.asyncio
    async def test_setup_teardown(self, backend: ASRBackend):
        """Verify setup and teardown lifecycle."""
        await backend.setup()
        await backend.teardown()

    @pytest.mark.asyncio
    async def test_transcribe_structure(self, backend: ASRBackend):
        """Verify that transcribe returns the expected structure."""
        await backend.setup()
        try:
            # We use a dummy audio input. Note: Real backends might fail if file doesn't exist.
            # Stubs should handle this or subclasses can override this test.
            audio: AudioInput = {"path": "dummy.wav", "sample_rate": 16000, "channels": 1}
            result = await backend.transcribe(audio, lang="es")
            
            assert isinstance(result, dict)
            # tokens is required by the contract implicitly if it's an ASRResult
            # Actually ASRResult is TypedDict(total=False), but tokens is the main output.
            assert "tokens" in result or "raw_text" in result
            if "tokens" in result:
                assert isinstance(result["tokens"], list)
                for t in result["tokens"]:
                    assert isinstance(t, str)
            if "meta" in result:
                assert isinstance(result["meta"], dict)
        finally:
            await backend.teardown()

    @pytest.mark.asyncio
    async def test_transcribe_no_lang(self, backend: ASRBackend):
        """Verify that transcribe works even if lang is None."""
        await backend.setup()
        try:
            audio: AudioInput = {"path": "dummy.wav", "sample_rate": 16000, "channels": 1}
            # Should not raise exception
            await backend.transcribe(audio, lang=None)
        finally:
            await backend.teardown()
