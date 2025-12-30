# Specification: MK-7 Plan de Pruebas

## Overview
Definir e implementar una estrategia de pruebas por capas para PronunciaPA, asegurando la calidad del microkernel y sus plugins. Se establecerán suites reutilizables para contratos de plugins y se medirá el rendimiento base.

## Functional Requirements
1.  **Shared Contract Test Suite:**
    *   Crear `ipa_core.testing.contracts` con tests genéricos para `ASRBackend`, `TextRefProvider`, etc.
    *   Refactorizar los tests existentes de plugins para usar esta suite compartida.
2.  **Kernel Integration Tests:**
    *   Consolidar pruebas que verifiquen la orquestación completa (`Kernel.run`) usando stubs controlados.
3.  **Performance Benchmarking:**
    *   Implementar un script/test que mida el Real-Time Factor (RTF) del pipeline usando el ASR Stub y Allosaurus (si está disponible).
    *   Reportar métricas básicas en la salida del test.
4.  **E2E Smoke Tests:**
    *   Verificar que `ipa_server` y `cli` arrancan y responden a un comando básico (smoke test).

## Non-Functional Requirements
- **Reusabilidad:** La suite de contratos debe ser importable por plugins externos.
- **Métricas:** Los tests de performance deben fallar si el RTF excede un umbral definido (e.g., 1.0 para stubs).

## Acceptance Criteria
- Existe un paquete `ipa_core.testing` usable por terceros.
- `AllosaurusASR` pasa la suite de contrato compartida.
- Se genera un reporte de latencia al correr `pytest --benchmark` (o similar).
- Cobertura de código mantenida o aumentada.

## Out of Scope
- Pruebas de carga masiva (concurrencia HTTP).
- Pruebas de UI (Frontend).
