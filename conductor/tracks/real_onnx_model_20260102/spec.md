# Specification: Real ONNX Model Integration

## Overview
Currently, the system uses "stubs" or mock models. This track integrates a real **CTC-based ASR model** (specifically targeting **Wav2Vec2** architecture compatibility) running via ONNX Runtime. This will allow the CLI to produce actual phonetic transcriptions from microphone input or WAV files.

## Functional Requirements

### 1. Tokenizer Compatibility
*   **Problem:** Current `ONNXASRPlugin` expects a simple list of labels. Real models (like Wav2Vec2) use a `vocab.json` dictionary mapping characters/phones to IDs.
*   **Requirement:** The plugin must detect `vocab.json` in the model directory and use it to build the label decoder.
*   **Handling:** It must correctly identify the "blank" token ID (usually 0 or `<pad>`) from the config or vocab.

### 2. Default Model Selection
*   **Target:** **facebook/wav2vec2-xls-r-300m** (or a smaller distilled variant) exported to ONNX.
*   **Reasoning:**
    *   **Multilingual:** Supports 128 languages (good for a pronunciation tool).
    *   **CTC Architecture:** Compatible with our existing greedy decoder logic (no Beam Search or Seq2Seq complexity needed yet).
    *   **Phonetic Potential:** Can be fine-tuned for IPA, but even the base character output is a good starting point for "grapheme-to-IPA" pipelines.
    *   *Alternative:* A specific **Silero** model if size is a major constraint (<50MB).

### 3. Configuration
*   The system should automatically attempt to download this default model if no local model is found when running `pronunciapa transcribe`.

## Non-Functional Requirements
*   **Performance:** Inference should remain near Real-Time (RTF ~1.0) on a standard CPU.
*   **Size:** Model download should ideally be under 500MB to be user-friendly.

## Acceptance Criteria
*   [ ] `ONNXASRPlugin` can load a standard Wav2Vec2 `vocab.json`.
*   [ ] A `pronunciapa transcribe --audio real_speech.wav` command outputs text/IPA that corresponds to the audio content (not random gibberish).
