import pytest
import json
from pathlib import Path
from ipa_core.testing.benchmark import DatasetLoader, MetricsCalculator

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

def test_metrics_calculator_per():
    """Should correctly calculate average PER."""
    calc = MetricsCalculator()
    # (S + D + I) / N
    # Sample 1: ref=["a", "b"], hyp=["a", "c"] -> S=1, D=0, I=0, N=2 -> PER=0.5
    # Sample 2: ref=["x"], hyp=["x"] -> PER=0.0
    # Avg PER = (0.5 + 0.0) / 2 = 0.25
    
    results = [
        {"ref": ["a", "b"], "hyp": ["a", "c"], "per": 0.5},
        {"ref": ["x"], "hyp": ["x"], "per": 0.0}
    ]
    
    summary = calc.calculate_summary(results)
    assert summary["avg_per"] == 0.25
    assert summary["min_per"] == 0.0
    assert summary["max_per"] == 0.5

def test_metrics_calculator_rtf():
    """Should correctly calculate average RTF."""
    calc = MetricsCalculator()
    # RTF = proc_time / audio_duration
    # Sample 1: proc=1.0, dur=10.0 -> RTF=0.1
    # Sample 2: proc=2.0, dur=10.0 -> RTF=0.2
    # Avg RTF = 0.15
    
    results = [
        {"proc_time": 1.0, "audio_duration": 10.0},
        {"proc_time": 2.0, "audio_duration": 10.0}
    ]
    
    summary = calc.calculate_summary(results)
    
    assert summary["avg_rtf"] == pytest.approx(0.15)