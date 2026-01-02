import pytest
import json
import numpy as np
from unittest.mock import MagicMock, patch
from ipa_core.config.schema import AppConfig
from ipa_core.kernel.core import create_kernel
from ipa_core.pipeline.transcribe import transcribe as transcribe_pipeline

@pytest.mark.asyncio
async def test_offline_transcription_flow(tmp_path):
    """
    Test E2E offline transcription using a mock ONNX model and mocked ONNX Runtime.
    Verifies that the configuration system, plugin loader, feature extractor,
    and ONNX runner work together to produce tokens.
    """
    # 1. Setup Mock Model structure on disk
    model_dir = tmp_path / "models" / "test_model"
    model_dir.mkdir(parents=True)
    (model_dir / "model.onnx").touch() # Dummy file, we mock the runner
    
    config_data = {
        "model_name": "test_model",
        "sample_rate": 16000,
        "n_mels": 80,
        "labels": ["_", "h", "o", "l", "a"],
        "input_shape": [-1, 80, -1],
        "output_shape": [-1, -1, 5],
        "blank_id": 0
    }
    (model_dir / "config.json").write_text(json.dumps(config_data), encoding="utf-8")

    # 2. Mock AppConfig
    # We construct the config object directly to bypass loading from file
    app_config = AppConfig(
        version=1,
        preprocessor={"name": "basic"},
        backend={
            "name": "onnx", # Matches default registry name
            "params": {
                "model_name": "test_model",
                "model_dir": str(model_dir),
                "n_mels": 80
            }
        },
        textref={"name": "grapheme"}, 
        comparator={"name": "levenshtein"},
        options={"lang": "es"}
    )

    # 3. Mock ONNX Runtime
    # We mock the 'ort' module inside onnx_engine
    mock_ort = MagicMock()
    mock_session = MagicMock()
    mock_ort.InferenceSession.return_value = mock_session
    
    # Define logits for "h o l a" (indices 1, 2, 3, 4)
    # Shape: (batch=1, time=5, vocab=5)
    # Frame 0->h, 1->o, 2->l, 3->a, 4->blank
    logits = np.zeros((1, 5, 5), dtype=np.float32)
    logits[0, 0, 1] = 100.0 # h
    logits[0, 1, 2] = 100.0 # o
    logits[0, 2, 3] = 100.0 # l
    logits[0, 3, 4] = 100.0 # a
    logits[0, 4, 0] = 100.0 # blank
    
    mock_session.run.return_value = [logits]
    mock_session.get_inputs.return_value = [MagicMock(name="input")]
    mock_session.get_outputs.return_value = [MagicMock(name="output")]

    # Patch 'ort' where it is imported in onnx_engine
    # AND patch 'librosa' in audio_processing
    mock_librosa = MagicMock()
    # Mock return of librosa.load
    mock_librosa.load.return_value = (np.zeros(16000, dtype=np.float32), 16000)
    # Mock return of melspectrogram: shape (n_mels=80, time=50)
    mock_librosa.feature.melspectrogram.return_value = np.zeros((80, 50), dtype=np.float32)
    mock_librosa.power_to_db.return_value = np.zeros((80, 50), dtype=np.float32) # Pass through

    with patch("ipa_core.backends.onnx_engine.ort", mock_ort), \
         patch("ipa_core.backends.audio_processing.librosa", mock_librosa):
        # 4. Create Kernel and Run
        kernel = create_kernel(app_config)
        await kernel.setup()
        
        try:
            # Dummy audio input complying with BasicPreprocessor requirements
            audio = {
                "path": "dummy.wav",
                "sample_rate": 16000,
                "channels": 1
            }
            
            tokens = await transcribe_pipeline(kernel.pre, kernel.asr, kernel.textref, audio=audio, lang="es")
            
            # 5. Assertions
            assert tokens == ["h", "o", "l", "a"]
            
        finally:
            await kernel.teardown()
