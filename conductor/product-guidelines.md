# Product Guidelines - PronunciaPA

## Voice and Tone
*   **Technical & Precise:** All documentation, API responses, and UI labels must use accurate terminology from linguistics and software engineering. Avoid ambiguity.
*   **Professional & Direct:** Communication should be efficient and focused on the task at hand.
*   **Open-Source Collaborative:** Tone should be welcoming to technical contributors, emphasizing clarity in contribution guides and issue reporting.

## Visual Design Principles (Web Interface)
*   **Functional Minimalism:** Prioritize the clear presentation of phonetic data and alignment results. The UI should be a tool, not a distraction.
*   **Modern Aesthetic:** Utilize clean typography, a balanced color palette (suitable for data visualization), and plenty of whitespace to ensure a professional and contemporary feel.
*   **Data-Centric Visualization:** Phonetic tokens, comparison scores, and error highlights should be the focal point of the user experience.
*   **Responsive & Accessible:** Ensure the interface is usable across different devices and adheres to basic web accessibility standards.

## Engineering Standards
*   **Microkernel Integrity:** Strictly adhere to the core/plugin separation. Core logic should remain agnostic of specific backend implementations.
*   **Strict Typing:** Use Python type hints and TypeScript interfaces religiously to ensure code clarity and catch errors early.
*   **High Test Coverage:** Target >80% code coverage. Every new feature or plugin must include unit and integration tests.
*   **Documentation-Driven Development:** Maintain up-to-date READMEs for all sub-packages and clear docstrings for public APIs.
*   **Mandatory Code Reviews:** All contributions must pass through a review process to ensure adherence to architectural and quality standards.

## Community & Extensibility
*   **Language-First Growth:** Prioritize features and documentation that lower the barrier for contributors adding new languages.
*   **Plugin Standardization:** Maintain clear interfaces and templates for ASR and TextRef plugins to ensure consistency across the ecosystem.
