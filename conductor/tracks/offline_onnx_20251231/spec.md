# Specification: Offline ONNX Model Management & Inference

## Overview
Enable PronunciaPA to operate completely offline by implementing a generic "ONNX Model Runner" architecture. This system allows users to download standardized model packages, manage them locally, and execute inference using the ONNX Runtime. The design emphasizes modularity, allowing the underlying model to be swapped without modifying the application code.

## Functional Requirements

### 1. Model Package Format
Define a standard filesystem structure for PronunciaPA models:
*   `model.onnx`: The core inference graph.
*   `config.json`: Metadata including input/output tensor shapes, sample rate requirements, and label/vocab maps.
*   `tokenizer.json` / `vocab.txt`: (Optional) Model-specific token-to-IPA mapping.

### 2. Local Model Manager
*   **Directory Management:** Standardize local storage path (e.g., `~/.pronunciapa/models/`).
*   **Discovery:** Automatically scan the local directory for valid model packages.
*   **Download Utility:** A CLI/API helper to download models from a remote URL, verify SHA256 integrity, and unpack them into the local store.

### 3. Audio Feature Extraction (Preprocessing)
*   **Implementation:** Utilize `librosa` for initial robust implementation of STFT and Mel-spectrogram generation.
*   **Abstraction:** Design an interface for feature extraction so that the dependency can be replaced with a lightweight NumPy/SciPy implementation in the future.

### 4. ONNX Inference Engine
*   **Session Management:** Load models into `onnxruntime` sessions.
*   **Standard Interface:** Implement a `LocalASRPlugin` that satisfies the existing ASR port, acting as a bridge between the Microkernel and the ONNX session.

## Non-Functional Requirements
*   **Offline First:** Once a model is downloaded, no internet connection should be required for transcription.
*   **Modularity:** Swapping `model.onnx` and `config.json` should be sufficient to change the transcription logic (e.g., changing from a Spanish model to an English one).
*   **Performance:** Aim for RTF (Real-Time Factor) < 1.0 on standard CPU hardware.

## Acceptance Criteria
*   [ ] A defined `ModelPackage` schema exists.
*   [ ] User can run a command to download a model to their local machine.
*   [ ] The application can list available local models.
*   [ ] ASR Pipeline successfully uses a locally stored `.onnx` file to produce IPA tokens.
*   [ ] The system operates correctly without an active internet connection (after initial download).

## Out of Scope
*   Training or fine-tuning models.
*   Conversion of models from PyTorch/TensorFlow to ONNX (this track assumes `.onnx` files are provided).
