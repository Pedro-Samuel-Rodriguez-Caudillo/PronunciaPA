import shutil
from pathlib import Path
from ipa_core.plugins.models import storage

def test_get_model_dir(monkeypatch, tmp_path):
    """Ensure it returns the correct path and creates it if missing."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path)) # Windows support
    
    model_dir = storage.get_models_dir()
    expected = tmp_path / ".pronunciapa" / "models"
    
    assert model_dir == expected
    assert model_dir.exists()

def test_scan_models(monkeypatch, tmp_path):
    """Should find valid model directories containing config.json."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    
    base = tmp_path / ".pronunciapa" / "models"
    base.mkdir(parents=True)
    
    # Valid model
    (base / "model_a").mkdir()
    (base / "model_a" / "config.json").touch()
    (base / "model_a" / "model.onnx").touch()
    
    # Invalid model (no config)
    (base / "model_b").mkdir()
    
    # Random file
    (base / "file.txt").touch()
    
    models = storage.scan_models()
    assert "model_a" in models
    assert "model_b" not in models
    assert len(models) == 1
