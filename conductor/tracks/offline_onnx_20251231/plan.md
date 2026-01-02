# Plan: Offline ONNX Model Management & Inference

Enabling offline phonetic recognition through a modular ONNX-based architecture.

## Phase 1: Model Package Schema & Foundations [checkpoint: 552d288]
Define the data structures and file layouts required for swappable models.

- [x] **Task: TDD - Define Model Config Schema** [5ef6722]
    - Write unit tests for validating `config.json` structures (input/output shapes, sample rates).
    - Implement Pydantic models for the configuration in `ipa_core/plugins/models/schema.py`.
- [x] **Task: TDD - Local Storage Utilities** [5ef6722]
    - Write tests for directory creation and scanning.
    - Implement helper functions to locate models in the user's home directory (`~/.pronunciapa/models`).
- [ ] **Task: Conductor - User Manual Verification 'Model Package Schema & Foundations' (Protocol in workflow.md)**

## Phase 2: Feature Extraction & Preprocessing
Implement the audio-to-tensor pipeline with swappable dependencies.

- [x] **Task: TDD - Abstract Feature Extractor Port** [c629280]
    - Write tests for a generic `FeatureExtractor` interface.
    - Implement the base interface in `ipa_core/ports/features.py`.
- [x] **Task: TDD - Librosa Implementation** [c629280]
    - Write tests for Mel-spectrogram generation matching standard ASR expectations (e.g. Whisper or Wav2Vec2 requirements).
    - Implement `LibrosaFeatureExtractor` in `ipa_core/backends/audio_processing.py`.
- [ ] **Task: Conductor - User Manual Verification 'Feature Extraction & Preprocessing' (Protocol in workflow.md)**

## Phase 3: ONNX Inference Engine
Develop the runner that executes the models using ONNX Runtime.

- [ ] **Task: TDD - ONNX Session Wrapper**
    - Write tests for loading an ONNX file and inspecting its input/output nodes.
    - Implement `ONNXRunner` in `ipa_core/backends/onnx_engine.py`.
- [ ] **Task: TDD - Local ASR Plugin Implementation**
    - Write unit tests for an ASR plugin that coordinates feature extraction and ONNX inference.
    - Implement `ONNXASRPlugin` in `ipa_core/plugins/asr_onnx.py`.
- [ ] **Task: Conductor - User Manual Verification 'ONNX Inference Engine' (Protocol in workflow.md)**

## Phase 4: Model Manager CLI & Integration
Add user-facing tools to manage models and verify the full offline flow.

- [x] **Task: TDD - Model Management CLI Commands** [acdb293]
    - Write tests for `pronunciapa models list` and `pronunciapa models download` (with mock HTTP).
    - Implement CLI commands in `ipa_core/interfaces/cli.py`.
- [ ] **Task: TDD - End-to-End Offline Integration**
    - Write an integration test that uses a mock (small) ONNX model to transcribe a WAV file.
    - Ensure the pipeline can be configured to use the local ONNX plugin via the standard config.
- [ ] **Task: Conductor - User Manual Verification 'Model Manager CLI & Integration' (Protocol in workflow.md)**
