"""Tests para pipeline con modos y niveles de evaluación."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock

from ipa_core.pipeline.transcribe import (
    transcribe,
    transcribe_audio,
    transcribe_text,
    prepare_comparison,
)
from ipa_core.phonology.representation import PhonologicalRepresentation
from ipa_core.errors import ValidationError
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider


@pytest.fixture
def mock_pre() -> MagicMock:
    m = MagicMock(spec=Preprocessor)
    m.process_audio = AsyncMock(return_value={"audio": {"path": "dummy.wav"}})
    m.normalize_tokens = AsyncMock(side_effect=lambda t: {"tokens": t})
    return m


@pytest.fixture
def mock_asr() -> MagicMock:
    m = MagicMock(spec=ASRBackend)
    m.transcribe = AsyncMock(return_value={"tokens": ["k", "a", "s", "a"]})
    return m


@pytest.fixture
def mock_textref() -> MagicMock:
    m = MagicMock(spec=TextRefProvider)
    m.to_ipa = AsyncMock(return_value={"tokens": ["k", "a", "s", "a"]})
    return m


class TestTranscribeAudio:
    """Tests para transcribe_audio."""
    
    @pytest.mark.asyncio
    async def test_returns_phonetic(self, mock_pre: MagicMock, mock_asr: MagicMock) -> None:
        """Retorna representación fonética."""
        result = await transcribe_audio(mock_pre, mock_asr, audio={"path": "test.wav"})
        assert isinstance(result, PhonologicalRepresentation)
        assert result.level == "phonetic"
    
    @pytest.mark.asyncio
    async def test_empty_tokens_raises(self, mock_pre: MagicMock, mock_asr: MagicMock) -> None:
        """Error si ASR no retorna tokens."""
        mock_asr.transcribe.return_value = {"tokens": []}
        with pytest.raises(ValidationError):
            await transcribe_audio(mock_pre, mock_asr, audio={"path": "test.wav"})


class TestTranscribeText:
    """Tests para transcribe_text."""
    
    @pytest.mark.asyncio
    async def test_returns_phonemic(self, mock_textref: MagicMock) -> None:
        """Retorna representación fonémica."""
        result = await transcribe_text(mock_textref, text="casa", lang="es")
        assert isinstance(result, PhonologicalRepresentation)
        assert result.level == "phonemic"
    
    @pytest.mark.asyncio
    async def test_empty_tokens_raises(self, mock_textref: MagicMock) -> None:
        """Error si TextRef no retorna tokens."""
        mock_textref.to_ipa.return_value = {"tokens": []}
        with pytest.raises(ValidationError):
            await transcribe_text(mock_textref, text="casa", lang="es")


class TestPrepareComparison:
    """Tests para prepare_comparison."""
    
    @pytest.mark.asyncio
    async def test_phonemic_level(
        self, 
        mock_pre: MagicMock, 
        mock_asr: MagicMock, 
        mock_textref: MagicMock,
    ) -> None:
        """En nivel fonémico, ambas representaciones son fonémicas."""
        target, observed = await prepare_comparison(
            target_text="casa",
            observed_audio={"path": "test.wav"},
            pre=mock_pre,
            asr=mock_asr,
            textref=mock_textref,
            lang="es",
            evaluation_level="phonemic",
        )
        assert target.level == "phonemic"
        assert observed.level == "phonemic"
    
    @pytest.mark.asyncio
    async def test_phonetic_level_no_pack(
        self, 
        mock_pre: MagicMock, 
        mock_asr: MagicMock, 
        mock_textref: MagicMock,
    ) -> None:
        """En nivel fonético sin pack, usa aproximación."""
        target, observed = await prepare_comparison(
            target_text="casa",
            observed_audio={"path": "test.wav"},
            pre=mock_pre,
            asr=mock_asr,
            textref=mock_textref,
            lang="es",
            evaluation_level="phonetic",
        )
        assert target.level == "phonetic"
        assert observed.level == "phonetic"


class TestLegacyTranscribe:
    """Tests para transcribe() legado."""
    
    @pytest.mark.asyncio
    async def test_returns_tokens(
        self, 
        mock_pre: MagicMock, 
        mock_asr: MagicMock, 
        mock_textref: MagicMock,
    ) -> None:
        """Retorna lista de tokens."""
        result = await transcribe(
            mock_pre, mock_asr, mock_textref,
            audio={"path": "test.wav"},
        )
        assert result == ["k", "a", "s", "a"]
