# Plan: Cross-Platform Client (Flutter)

Objective: Build a unified frontend for Desktop (Windows) and Mobile (Android/iOS) using Flutter that interacts with the PronunciaPA backend.

## Phase 1: Project Scaffolding
Initialize the Flutter environment and structure.

- [ ] **Task: Create Flutter Project**
    - Run `flutter create pronunciapa_client`.
    - Configure for Windows and Android/iOS targets.
    - Set up project structure (clean architecture: domain, data, presentation).

## Phase 2: Core UI Components
Implement the essential visual elements using Material Design 3.

- [ ] **Task: Recorder Widget**
    - Create a widget with a recording button and visualization (waveform or simple timer).
- [ ] **Task: IPA Display & Diff**
    - Create a widget to display the IPA transcription strings.
    - Implement a visual diff viewer (Green/Red highlighting) for comparison results.

## Phase 3: Backend Integration
Connect the UI to the `ipa_server`.

- [ ] **Task: API Client**
    - Implement a service to POST audio to `http://localhost:8000/v1/transcribe` and `/v1/compare`.
    - Handle loading states and errors.
- [ ] **Task: End-to-End Flow**
    - Wire up the Recorder -> API -> Diff View flow.
    - **Deliverable:** A functional app where you can speak and see the score.

## Phase 4: Packaging
Prepare the app for distribution (basic build).

- [ ] **Task: Build Windows Executable**
    - Run `flutter build windows` and verify the artifact runs.
- [ ] **Task: Conductor - User Manual Verification 'Flutter Client' (Protocol in workflow.md)**
