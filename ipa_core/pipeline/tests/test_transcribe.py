import pytest
from unittest.mock import AsyncMock, MagicMock
from ipa_core.errors import ValidationError
from ipa_core.pipeline.transcribe import transcribe
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider

@pytest.fixture
def mock_pre():
    m = MagicMock(spec=Preprocessor)
    m.process_audio = AsyncMock(return_value={"audio": {"path": "dummy.wav"}})
    m.normalize_tokens = AsyncMock(side_effect=lambda t: {"tokens": t})
    return m

@pytest.fixture
def mock_asr():
    m = MagicMock(spec=ASRBackend)
    m.transcribe = AsyncMock()
    return m

@pytest.fixture
def mock_textref():
    m = MagicMock(spec=TextRefProvider)
    m.to_ipa = AsyncMock()
    return m

@pytest.mark.asyncio
async def test_transcribe_asr_tokens(mock_pre, mock_asr, mock_textref):
    """Test path where ASR returns tokens directly."""
    mock_asr.transcribe.return_value = {"tokens": ["a", "b"], "meta": {}}
    
    result = await transcribe(mock_pre, mock_asr, mock_textref, audio={"path": "in.wav"})
    
    assert result == ["a", "b"]
    mock_pre.process_audio.assert_called_once()
    mock_asr.transcribe.assert_called_once()
    mock_pre.normalize_tokens.assert_called_once_with(["a", "b"])
    mock_textref.to_ipa.assert_not_called()

@pytest.mark.asyncio
async def test_transcribe_asr_raw_text(mock_pre, mock_asr, mock_textref):
    """Test path where ASR returns raw text requiring TextRef."""
    mock_asr.transcribe.return_value = {"raw_text": "hello", "meta": {}}
    mock_textref.to_ipa.return_value = {"tokens": ["h", "e", "l", "l", "o"], "meta": {}}
    
    with pytest.raises(ValidationError):
        await transcribe(mock_pre, mock_asr, mock_textref, audio={"path": "in.wav"}, lang="en")

    mock_textref.to_ipa.assert_not_called()

@pytest.mark.asyncio
async def test_transcribe_empty(mock_pre, mock_asr, mock_textref):
    """Test path where ASR returns nothing useful."""
    mock_asr.transcribe.return_value = {"meta": {}}

    with pytest.raises(ValidationError):
        await transcribe(mock_pre, mock_asr, mock_textref, audio={"path": "in.wav"})
