import pytest
import json
from ipa_core.plugins.asr_onnx import ONNXASRPlugin
from ipa_core.plugins.models.schema import ModelConfig

def test_load_labels_from_vocab_json(tmp_path):
    """Should load labels from a dict in vocab.json and sort by ID."""
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    
    # Wav2Vec2 style vocab: "char": id
    vocab = {
        "<pad>": 0,
        "<s>": 1,
        "</s>": 2,
        "<unk>": 3,
        "a": 4,
        "b": 5
    }
    (model_dir / "vocab.json").write_text(json.dumps(vocab), encoding="utf-8")
    (model_dir / "model.onnx").touch()
    
    config = {
        "model_name": "test",
        "sample_rate": 16000,
        "n_mels": 80,
        "labels": [], # Empty in config, should load from vocab.json
        "input_shape": [1, 80, 100],
        "output_shape": [1, 100, 6]
    }
    (model_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
    
    plugin = ONNXASRPlugin(params={"model_dir": str(model_dir)})
    
    # We need to mock setup or extract the label loading logic. 
    # For now, let's test a helper method we will create: _load_labels
    
    # But wait, TDD: we write the test against the public API or internal method if complex
    # Let's assume setup() does it. We can't call setup() easily without mocking ONNX/Librosa.
    
    # Strategy: Mock internal dependencies to allow setup() to run far enough to load labels
    from unittest.mock import MagicMock, patch
    
    with patch("ipa_core.plugins.asr_onnx.LibrosaFeatureExtractor"), \
         patch("ipa_core.plugins.asr_onnx.ONNXRunner"):
         
        import asyncio
        asyncio.run(plugin.setup())
        
        # Expected behavior:
        # labels should be a list where index matches value
        # 0-><pad>, 1-><s>, 2-></s>, 3-><unk>, 4->a, 5->b
        expected = ["<pad>", "<s>", "</s>", "<unk>", "a", "b"]
        assert plugin._labels == expected

def test_resolve_blank_id_from_vocab():
    """Should correctly identify blank_id from <pad> if not specified."""
    # This logic might need to be added to the plugin
    pass
