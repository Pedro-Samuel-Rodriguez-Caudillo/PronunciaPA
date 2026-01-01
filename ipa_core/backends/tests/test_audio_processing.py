import pytest
import numpy as np
import sys
from unittest.mock import patch, MagicMock

# Mock librosa before importing the module that uses it
mock_librosa = MagicMock()
sys.modules["librosa"] = mock_librosa
sys.modules["librosa.feature"] = MagicMock()

from ipa_core.backends.audio_processing import LibrosaFeatureExtractor
from ipa_core.types import AudioInput

@pytest.mark.asyncio
async def test_librosa_extractor_shapes():
    """Test that it produces correct shapes using mocked librosa."""
    # Reset mock to ensure clean state
    mock_librosa.reset_mock()
    
    # Mock audio: 1 sec at 16k
    mock_librosa.load.return_value = (np.zeros(16000), 16000)
    
    # Mock spectrogram: (n_mels=80, time=100)
    mock_librosa.feature.melspectrogram.return_value = np.zeros((80, 100))
    mock_librosa.power_to_db.return_value = np.zeros((80, 100))
    
    extractor = LibrosaFeatureExtractor(sample_rate=16000, n_mels=80)
    audio_in: AudioInput = {"path": "dummy.wav", "sample_rate": 16000, "channels": 1}
    
    features = await extractor.extract(audio_in)
    
    # Expect (1, 80, 100) -> added batch dim
    assert features.shape == (1, 80, 100)
    mock_librosa.load.assert_called()
