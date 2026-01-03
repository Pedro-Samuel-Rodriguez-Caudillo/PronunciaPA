# Plan: Real ONNX Model Integration

Objective: Integrate a functional, production-grade ONNX model (Wav2Vec2/Silero) to enable real speech-to-IPA transcription, replacing the current stubs.

## Phase 1: Enhanced Tokenization
Upgrade the plugin to support standard HuggingFace/Wav2Vec2 vocabulary formats.

- [x] **Task: TDD - Vocab.json Support** [cd30d74]
    - Update `ONNXASRPlugin` to load labels from a `vocab.json` (dict of "token": id) file, not just a simple list.
    - Handle special tokens (pad/blank/unk) more robustly.

## Phase 2: Model Configuration & Assets
Configure the system to download and use a real pre-trained model.

- [x] **Task: Select & Configure Model** [8b23152]
    - Choose a lightweight, open-license ONNX model (e.g., a quantized Wav2Vec2-XLS-R or Silero model).
    - Create the corresponding `config.json` defining its input shapes and sample rates.
    - Update `configs/local.yaml` to point to this model by default.

## Phase 3: End-to-End Verification
Prove functionality with real audio.

- [ ] **Task: Integration & Manual Test**
    - Record a real `manual_test.wav`.
    - Run `pronunciapa transcribe` and verify recognizable IPA output.
    - **Deliverable:** A successful transcription log.
- [ ] **Task: Conductor - User Manual Verification 'Real ONNX Model Integration' (Protocol in workflow.md)**
