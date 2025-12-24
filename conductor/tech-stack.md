# Technology Stack - PronunciaPA

## Backend
*   **Language:** Python >= 3.9 (utilizing strict type hints)
    *   *Note (2025-12-24): Lowered from 3.11 to 3.9 to match the execution environment.*
*   **API Framework:** FastAPI
*   **Web Server:** Uvicorn
*   **Phonetic Processing:**
    *   **ASR:** Allosaurus (as primary backend)
    *   **Text-to-IPA:** Epitran, eSpeak-ng
    *   **Comparison:** Custom Levenshtein-based alignment logic
*   **Audio Handling:** Sounddevice, NumPy, Pydub, ffmpeg

## Frontend
*   **Environment:** Node.js (Vite)
*   **Language:** TypeScript
*   **Styling:** Tailwind CSS v4
*   **Communication:** Fetch API (interacting with the FastAPI backend)

## Infrastructure & DevOps
*   **Containerization:** Docker, Docker Compose
*   **Automation:** Makefile (for testing and deployment tasks)
*   **Version Control:** Git

## Testing & Quality
*   **Python Testing:** Pytest (including coverage analysis)
*   **Linter/Formatter:** (To be defined in style guides)
*   **Type Checking:** Mypy (recommended)
