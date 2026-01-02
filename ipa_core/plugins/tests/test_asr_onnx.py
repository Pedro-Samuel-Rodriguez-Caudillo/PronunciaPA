import pytest
import numpy as np
from ipa_core.plugins.asr_onnx import ONNXASRPlugin

def test_ctc_greedy_decode_basic():
    """Should remove blanks and repeats."""
    labels = ["blank", "a", "b", "c"]
    # Logits: (Time=5, Vocab=4)
    # 0: a (1)
    # 1: a (1) -> repeat
    # 2: blank (0)
    # 3: b (2)
    # 4: c (3)
    logits = np.zeros((5, 4))
    logits[0, 1] = 10
    logits[1, 1] = 10
    logits[2, 0] = 10
    logits[3, 2] = 10
    logits[4, 3] = 10
    
    tokens = ONNXASRPlugin._ctc_greedy_decode(logits, labels, blank_id=0)
    assert tokens == ["a", "b", "c"]

def test_ctc_greedy_decode_empty():
    """Should handle all blanks."""
    labels = ["blank", "a"]
    logits = np.zeros((3, 2))
    logits[:, 0] = 10
    tokens = ONNXASRPlugin._ctc_greedy_decode(logits, labels, blank_id=0)
    assert tokens == []
