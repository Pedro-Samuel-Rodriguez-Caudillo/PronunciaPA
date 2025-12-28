"""Tests para `EspeakTextRef`."""
from __future__ import annotations

import pytest

from ipa_core.errors import NotReadyError
from ipa_core.textref.espeak import EspeakTextRef


@pytest.mark.asyncio
async def test_espeak_produces_tokens_from_subprocess():
    from unittest.mock import patch, AsyncMock
    from ipa_core.textref.espeak import EspeakTextRef

    # Mock the process object
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"h o l a\n", b"")
    mock_proc.returncode = 0

    # Patch create_subprocess_exec
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        provider = EspeakTextRef(default_lang="es", binary="espeak")
        result = await provider.to_ipa("hola", lang="es")

        assert result["tokens"] == ["h", "o", "l", "a"]
        
        # Verify call arguments
        args = mock_exec.call_args[0]
        assert args[0] == "espeak"
        assert "-v" in args
        assert "--ipa=3" in args



def test_espeak_detects_binary_and_raises_when_missing(monkeypatch):
    monkeypatch.setenv("PRONUNCIAPA_ESPEAK_BIN", "")
    monkeypatch.setenv("ESPEAK_BIN", "")
    monkeypatch.setenv("PATH", "")
    with pytest.raises(NotReadyError):
        EspeakTextRef()
