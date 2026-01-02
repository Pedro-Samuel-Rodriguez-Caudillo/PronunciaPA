import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
from ipa_core.backends.onnx_engine import ONNXRunner

def test_onnx_runner_init_fails_if_no_file():
    """Should raise FileNotFoundError if model doesn't exist."""
    mock_ort = MagicMock()
    with patch("ipa_core.backends.onnx_engine.ort", mock_ort):
        with pytest.raises(FileNotFoundError):
            ONNXRunner(Path("non_existent.onnx"))

def test_onnx_runner_execution():
    """Should call session.run with correct inputs."""
    mock_ort = MagicMock()
    mock_session = MagicMock()
    mock_ort.InferenceSession.return_value = mock_session
    
    mock_input = MagicMock()
    mock_input.name = "input_node"
    mock_session.get_inputs.return_value = [mock_input]
    
    mock_output = MagicMock()
    mock_output.name = "output_node"
    mock_session.get_outputs.return_value = [mock_output]
    
    # Mock output tensor
    mock_session.run.return_value = [np.array([1, 2, 3])]

    with patch("ipa_core.backends.onnx_engine.ort", mock_ort):
        # Need to mock Path.exists too
        with patch("pathlib.Path.exists", return_value=True):
            runner = ONNXRunner(Path("fake.onnx"))
            feats = np.array([[1.0]], dtype=np.float32)
            result = runner.run(feats)
            
            assert np.array_equal(result, [1, 2, 3])
            mock_session.run.assert_called_once_with(["output_node"], {"input_node": feats})
