import pytest
from unittest.mock import MagicMock, patch
from ipa_plugin_allosaurus.backend import AllosaurusASR
from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.testing.contracts.asr import ASRContract

@pytest.fixture
def mock_recognizer():
    return MagicMock()

@pytest.fixture
def mock_read_recognizer(mock_recognizer):
    with patch("ipa_plugin_allosaurus.backend.read_recognizer", return_value=mock_recognizer) as m:
        yield m

class TestAllosaurusASR(ASRContract):
    
    @pytest.fixture
    def backend(self, mock_read_recognizer, mock_recognizer):
        # We return an instance that is already mocked
        # Note: ASRContract tests will use this
        mock_recognizer.recognize.return_value = "a b c"
        return AllosaurusASR()

    @pytest.mark.asyncio
    async def test_allosaurus_setup_lazy_load(self, mock_read_recognizer, mock_recognizer):
        asr = AllosaurusASR()
        assert asr._recognizer is None
        
        await asr.setup()
        
        assert asr._recognizer == mock_recognizer
        mock_read_recognizer.assert_called_once()

    @pytest.mark.asyncio
    async def test_allosaurus_transcribe_mapping(self, mock_read_recognizer, mock_recognizer):
        asr = AllosaurusASR()
        mock_recognizer.recognize.return_value = "a b c"
        
        result = await asr.transcribe({"path": "test.wav"}, lang="es")
        
        # check lang mapping es -> spa
        mock_recognizer.recognize.assert_called_with("test.wav", "spa")
        assert result["tokens"] == ["a", "b", "c"]
        assert result["meta"]["backend"] == "allosaurus"

    @pytest.mark.asyncio
    async def test_allosaurus_validation_error(self, mock_read_recognizer):
        asr = AllosaurusASR()
        with pytest.raises(ValidationError):
            await asr.transcribe({}) # Missing path

    def test_allosaurus_init_params(self):
        asr = AllosaurusASR(params={"lang": "fr", "model_dir": "/tmp"})
        assert asr._default_lang == "fr"
        assert asr._model_dir == "/tmp"