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
            # 'tokens' is required by the pipeline (execute_pipeline raises
            # ValidationError if absent).  A backend returning only 'raw_text'
            # would pass this contract but hard-fail in production.
            assert "tokens" in result, "ASRResult MUST contain 'tokens' key"
            assert isinstance(result["tokens"], list)
            for t in result["tokens"]:
                assert isinstance(t, str)
            # 'raw_text' is optional but recommended for debuggability
            if "raw_text" in result:
                assert isinstance(result["raw_text"], str)
            # meta is required per port contract (backend/model/lang keys)
            assert "meta" in result, "ASRResult MUST contain 'meta' key"
            assert isinstance(result["meta"], dict)
            for required_meta_key in ("backend", "model", "lang"):
                assert required_meta_key in result["meta"], (
                    f"ASRResult.meta MUST contain '{required_meta_key}'"
                )
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
