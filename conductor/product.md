# Product Guide - PronunciaPA

## Initial Concept
Reconocimiento fonético (ASR + IPA) con CLI, API HTTP y un frontend listo para que cualquier persona pruebe su pronunciación.

## Vision
PronunciaPA is an open-source, community-driven platform designed to help language learners achieve correct pronunciation in any language. By providing real-time phonetic feedback and a modular architecture, it aims to become a universal engine for pronunciation study that anyone can extend and integrate into their own educational tools.

## Target Users
*   **Language Learners:** Individuals seeking precise, real-time feedback on their phonetic accuracy.
*   **Educational Tool Developers:** Creators who want to integrate robust ASR-to-IPA capabilities into their own applications.
*   **Language Communities:** Groups interested in adding support for their specific languages or dialects to a shared phonetic ecosystem.

## Core Goals
*   **Real-time Phonetic Feedback:** Transform spoken audio into IPA tokens and compare them against a reference to provide immediate, actionable feedback.
*   **Microkernel Architecture:** Maintain a highly modular core where ASR, IPA translation, and comparison logic are decoupled, allowing for easy expansion.
*   **Language Extensibility:** Empower the open-source community to add support for new languages by developing dedicated language plugins.
*   **Universal Accessibility:** Provide multiple interfaces (CLI, HTTP API, Web) to ensure the technology is accessible to developers and end-users alike.

## Key Features
*   **ASR to IPA Pipeline:** Efficiently convert recorded audio or files into precise IPA phonetic transcriptions.
*   **Pronunciation Comparison:** Align and compare user-generated IPA tokens against reference transcriptions using algorithms like Levenshtein distance.
*   **Detailed Error Highlighting:** Visually pinpoint specific phonetic discrepancies to guide the user's improvement.
*   **Offline First Operation:** Manage and execute downloaded phonetic models locally using ONNX, ensuring privacy and reliability without an internet connection.
*   **Plugin System:** A robust mechanism for adding new languages, ASR backends (like Allosaurus), and Text-to-IPA providers (like Epitran or eSpeak).

## Future Roadmap
*   **Custom Deep Learning Models:** Research and implementation of proprietary Deep Learning models to improve accuracy and adaptability beyond existing third-party ASR backends.
