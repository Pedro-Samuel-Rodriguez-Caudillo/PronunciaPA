# Specification: MK-6 Estructura de Paquetes

## Overview
Reorganizar la estructura del proyecto `ipa_core` para alinearse con una arquitectura Microkernel estricta. El objetivo es mantener `ipa_core` ligero y portátil (para uso futuro en móvil/web), moviendo implementaciones pesadas a plugins y separando las interfaces de consumo (API) del núcleo lógico.

## Functional Requirements
1.  **Refactorización del Core (`ipa_core`):**
    *   Mantener `kernel/`, `ports/`, `types.py`, `errors.py`.
    *   Mantener implementaciones ligeras/stubs (`StubASR`, `Levenshtein`, `BasicPreprocessor`) para desarrollo y testing.
    *   **Mover** el CLI actual a `ipa_core/interfaces/cli.py` (o mantenerlo minimalista).
2.  **Extracción de Plugins Pesados:**
    *   Crear una estructura para plugins externos (simulada dentro del monorepo por ahora o preparada para extracción).
    *   **Mover** `ipa_core/backends/asr_allosaurus.py` fuera del núcleo ligero. Propuesta: mover a `plugins/allosaurus/ipa_plugin_allosaurus/`.
    *   **Decisión:** Mover `asr_allosaurus.py` a un directorio raíz `plugins/allosaurus/` para demostrar la separación.
3.  **Separación de API:**
    *   Mover el código de la API HTTP (`ipa_core/api/http.py`) a una ubicación que demuestre que es un consumidor, no parte del core. Ubicación: `ipa_server/main.py`.

## Refined Scope (Actionable)
1.  Consolidar el núcleo en `ipa_core`:
    *   `ipa_core.kernel`
    *   `ipa_core.ports`
    *   `ipa_core.plugins`
2.  Mover implementaciones "built-in" ligeras a `ipa_core.defaults` (o carpetas equivalentes).
3.  Mover `AllosaurusASR` a un nuevo directorio raíz `plugins/allosaurus`.
4.  Actualizar `pyproject.toml` para reflejar estos cambios.

## Acceptance Criteria
- `ipa_core` no debe importar `allosaurus` directamente.
- `AllosaurusASR` se carga dinámicamente vía el mecanismo de plugins (entry points).
- Los tests unitarios del core pasan sin tener `allosaurus` instalado.
- La estructura de carpetas refleja claramente: Core vs Plugins vs Interfaces.

## Out of Scope
- Crear paquetes PyPI separados y publicarlos.
- Reescribir toda la API HTTP (solo mover archivos).
