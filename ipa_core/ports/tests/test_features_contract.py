import pytest
from ipa_core.ports.features import FeatureExtractor
from ipa_core.types import AudioInput
import numpy as np

class MockExtractor:
    """Mock implementation of FeatureExtractor."""
    async def extract(self, audio: AudioInput) -> np.ndarray:
        return np.zeros((1, 80, 100))

def test_feature_extractor_protocol():
    """Ensure MockExtractor satisfies the protocol."""
    extractor = MockExtractor()
    assert isinstance(extractor, FeatureExtractor)
    assert hasattr(extractor, "extract")
