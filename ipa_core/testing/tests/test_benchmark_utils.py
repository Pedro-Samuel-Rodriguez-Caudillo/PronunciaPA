import pytest
import json
from pathlib import Path
from ipa_core.testing.benchmark import DatasetLoader

def test_load_jsonl_manifest(tmp_path):
    """Should correctly load a list of samples from a JSONL file."""
    manifest_path = tmp_path / "manifest.jsonl"
    samples = [
        {"audio": "audio1.wav", "text": "hello"},
        {"audio": "audio2.wav", "text": "world"}
    ]
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")
            
    loader = DatasetLoader()
    loaded_samples = loader.load_manifest(manifest_path)
    
    assert len(loaded_samples) == 2
    assert loaded_samples[0]["audio"] == "audio1.wav"
    assert loaded_samples[1]["text"] == "world"

def test_load_manifest_file_not_found():
    """Should raise FileNotFoundError if manifest doesn't exist."""
    loader = DatasetLoader()
    with pytest.raises(FileNotFoundError):
        loader.load_manifest(Path("ghost.jsonl"))

def test_load_manifest_malformed_json(tmp_path):
    """Should raise ValueError for malformed JSON lines."""
    manifest_path = tmp_path / "bad.jsonl"
    with open(manifest_path, "w") as f:
        f.write('{"audio": "valid"}\n')
        f.write('{"audio": "invalid", "text": "missing closing brace"\n')
        
    loader = DatasetLoader()
    with pytest.raises(ValueError, match="Error parsing manifest"):
        loader.load_manifest(manifest_path)
