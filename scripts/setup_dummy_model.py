import json
from pathlib import Path

def create_dummy_wav2vec2(model_dir: Path):
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. vocab.json
    vocab = {
        "<pad>": 0, "<s>": 1, "</s>": 2, "<unk>": 3, "|": 4,
        "e": 5, "t": 6, "a": 7, "o": 8, "n": 9, "i": 10, "h": 11, "s": 12, "r": 13 
    }
    (model_dir / "vocab.json").write_text(json.dumps(vocab), encoding="utf-8")
    
    # 2. config.json
    config = {
        "model_name": "dummy-wav2vec2",
        "sample_rate": 16000,
        "n_mels": 80,
        "labels": list(vocab.keys()), 
        "input_shape": [1, -1],
        "output_shape": [1, -1, len(vocab)],
        "blank_id": 0
    }
    (model_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
    
    # 3. model.onnx (Empty file)
    (model_dir / "model.onnx").write_text("NOT_A_VALID_ONNX_FILE", encoding="utf-8")
    print(f"Dummy model created at {model_dir}")

if __name__ == "__main__":
    home = Path.home()
    dest = home / ".pronunciapa" / "models" / "wav2vec2-base-960h"
    create_dummy_wav2vec2(dest)