# Guía de Contribución y Ramas

Objetivo
- Trabajo en 2 días con ramas por persona y por feature.

Ramas
- feature/<owner>/<kebab-feature>
  - Ej: `feature/ricardo840/audio-io-asr-stub`
  - Ej: `feature/CWesternBurger/pipeline-transcribe-cli`
  - Ej: `feature/Pedro-Samuel-Rodriguez-Caudillo/preprocessor-basic`
- docs/<topic>: documentación (opcional)
- chore/<topic>: mantenimiento

Commits (Conventional Commits recomendado)
- `feat: ...`, `docs: ...`, `chore: ...`, `refactor: ...`, `test: ...`
- Incluir referencia de owner y alcance en el cuerpo si aplica.

Flujo sugerido
1) Crear rama desde `master` actualizada.
2) Commits pequeños y descriptivos (1 feature por PR).
3) PR con checklist de DoD y pruebas manuales (si aplica).
4) Revisión cruzada por otro miembro del equipo.
5) Merge squash o rebase según preferencia del repositorio.

Lineamientos
- No romper contratos existentes ni tests en `master`.
- Implementaciones reales en ramas de feature; `master` puede contener docs.
- Evitar dependencias externas no necesarias en el MVP.

Naming
- Personas: `ricardo840`, `CWesternBurger`, `Pedro-Samuel-Rodriguez-Caudillo`.
- Features: usar nombres cortos, en kebab-case.
