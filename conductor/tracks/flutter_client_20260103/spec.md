# Specification: Cross-Platform Client (Flutter)

## Overview
A single codebase application for Windows, Android, and iOS that serves as the user interface for PronunciaPA. It communicates with the backend via HTTP API.

## Functional Requirements

### 1. Audio Capture
*   **Permissions:** Request microphone permissions on all platforms.
*   **Format:** Record audio in a format compatible with the backend (WAV/PCM 16kHz preferred).
*   **UI:** Simple "Push to Talk" or "Toggle Record" button.

### 2. Transcription & Comparison
*   **Transcribe:** Send audio to `/v1/transcribe` and display the raw IPA.
*   **Compare:** Allow user to input a "Reference Text" (or select from a list). Send audio + text to `/v1/compare`.
*   **Feedback:** Display the returned PER score and the aligned IPA tokens.

### 3. Visuals
*   **Style:** Material Design 3.
*   **Color Coding:**
    *   **Match:** Green
    *   **Substitution:** Orange/Yellow
    *   **Deletion/Insertion:** Red

## Non-Functional Requirements
*   **Responsiveness:** UI must adapt to both Desktop (landscape, mouse) and Mobile (portrait, touch).
*   **Architecture:** Use a scalable pattern (e.g., Provider or Riverpod + Repository Pattern).

## Acceptance Criteria
*   [ ] App compiles and runs on Windows.
*   [ ] User can record audio.
*   [ ] User sees IPA transcription returned from the local server.
*   [ ] User sees a color-coded comparison against a reference text.
