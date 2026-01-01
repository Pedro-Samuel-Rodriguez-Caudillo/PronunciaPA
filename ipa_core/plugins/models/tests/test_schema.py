import pytest
from ipa_core.plugins.models.schema import ModelConfig

def test_model_config_validation_valid():
    """Test valid model configuration."""
    valid_config = {
        "model_name": "test_model",
        "input_shape": [1, 16000],
        "output_shape": [1, 100],
        "sample_rate": 16000,
        "labels": ["a", "b", "c"],
        "architecture": "wav2vec2"
    }
    config = ModelConfig(**valid_config)
    assert config.model_name == "test_model"
    assert config.sample_rate == 16000
    assert len(config.labels) == 3

def test_model_config_validation_invalid_sr():
    """Test validation fails for invalid sample rate."""
    invalid_config = {
        "model_name": "bad_sr",
        "sample_rate": -1,
        "labels": ["a"]
    }
    with pytest.raises(ValueError):
        ModelConfig(**invalid_config)

def test_model_config_validation_missing_fields():
    """Test validation fails for missing required fields."""
    # Missing labels
    invalid_config = {
        "model_name": "missing_labels",
        "sample_rate": 16000
    }
    with pytest.raises(ValueError):
        ModelConfig(**invalid_config)
