# Plan de Pruebas — PronunciaPA
**Versión:** 1.0  
**Fecha:** 2026-03-10  
**Normas:** ISO/IEC/IEEE 29119-3:2021 · ISO/IEC 25010:2023 · IEEE 1012:2016 · ISO/IEC 12207:2017

---

## 1.객Objetivo

Definir la estrategia, niveles, criterios de entrada/salida y métricas de calidad para las pruebas de PronunciaPA. **Los tests rigen la calidad del software; el código debe satisfacer los tests, no al revés.**

---

## 2. Alcance

### 2.1 En scope

| Componente | Módulo |
|-----------|--------|
| Motor de evaluación fonética | `ipa_core/` |
| API HTTP | `ipa_server/` |
| Interfaz de línea de comandos | `ipa_core/interfaces/` |
| Cliente móvil Flutter | `pronunciapa_client/` |
| Sistema de plugins | `ipa_core/plugins/` |
| Packs de idioma | `ipa_core/packs/` |

### 2.2 Fuera de scope

- Modelos preentrenados de terceros (Allosaurus, eSpeak — validados por sus fabricantes)
- Infraestructura DevOps (Docker, CI/CD *deployment mechanics*)
- Frontend React (ola posterior)

---

## 3. Niveles de Prueba (ISO/IEC/IEEE 29119)

### Nivel 1 — Pruebas Unitarias (L1)

| Aspecto | Definición |
|---------|-----------|
| **Scope** | Función/clase/protocolo aislado con stubs para dependencias externas |
| **Responsable** | Desarrollador de la unidad |
| **Herramientas** | `pytest`, `unittest.mock`, `hypothesis` |
| **Entorno** | Sin modelos reales (`PRONUNCIAPA_ASR=stub`) |
| **Criterio de entrada** | Interfaz documentada (Protocol/TypedDict), stubs definidos |
| **Criterio de salida** | 100 % de tests L1 pasan; sin warnings de tipo (`mypy`) |

Módulos cubiertos: `ipa_core/compare/`, `ipa_core/ports/`, `ipa_core/pipeline/`, `ipa_core/packs/`, `ipa_core/phonology/`, `ipa_core/textref/`, `ipa_core/normalization/`, `ipa_core/config/`

### Nivel 2 — Pruebas de Integración (L2)

| Aspecto | Definición |
|---------|-----------|
| **Scope** | Interacción entre dos o más módulos; pipeline extremo a extremo en modo stub |
| **Herramientas** | `pytest`, fixtures de `conftest.py`, `tests/utils/audio.py` |
| **Criterio de entrada** | Todos los L1 pasan |
| **Criterio de salida** | Pipeline `audio → IPA → PER` completo sin errores; kernel setup/teardown limpio |

Módulos cubiertos: `ipa_core/pipeline/`, `ipa_core/kernel/`, `ipa_core/services/`, `ipa_core/plugins/`

### Nivel 3 — Pruebas de Sistema (L3)

| Aspecto | Definición |
|---------|-----------|
| **Scope** | Producto completo: CLI + API HTTP accesibles externamente |
| **Herramientas** | `pytest`, `httpx`, `CliRunner` (Typer) |
| **Criterio de entrada** | Todos los L2 pasan; servidor levantable en modo stub |
| **Criterio de salida** | Todos los endpoints y comandos CLI documentados responden correctamente |

Módulos cubiertos: `ipa_server/`, `ipa_core/interfaces/`

### Nivel 4 — Pruebas E2E / Aceptación (L4)

| Aspecto | Definición |
|---------|-----------|
| **Scope** | Flujos de usuario completos descritos en `conductor/product.md` |
| **Herramientas** | Flutter `integration_test`, scripts manuales |
| **Criterio de entrada** | Todos los L3 pasan; device/emulador disponible |
| **Criterio de salida** | Los journeys de usuario descritos en §6 se completan sin errores |

---

## 4. Atributos de Calidad Probados (ISO/IEC 25010:2023)

| Atributo | Característica ISO 25010 | Módulos afectados | Nivel de prueba |
|---------|--------------------------|-------------------|-----------------|
| Corrección funcional | §8.1 Functional Suitability | pipeline, compare, packs | L1, L2 |
| Precisión fonética | §8.1.2 Functional Correctness | compare, phonology, textref | L1 |
| Rendimiento temporal | §8.4 Performance Efficiency | pipeline, ipa_server | L2, L3 |
| Seguridad | §8.5 Security | ipa_server, audio inputs | L3 |
| Confiabilidad | §8.3 Reliability | kernel, pipeline | L2 |
| Compatibilidad | §8.2 Compatibility | plugins, packs | L2 |
| Usabilidad | §8.6 Usability | interfaces/cli, ipa_server API | L3 |
| Portabilidad | §8.9 Portability | Flutter client | L4 |

---

## 5. Criterios de Entrada y Salida por Nivel (IEEE 1012)

### L1 — Entrada
- Función/protocolo tiene firma documentada
- Stubs/mocks para dependencias externas están disponibles
- Comportamiento esperado confirmado con el equipo (protocolo de especificación)

### L1 — Salida
- Todos los tests L1 pasan (`pytest -m unit`)
- Cobertura de código ≥ 80 % en módulos cubiertos
- Sin errores mypy en código nuevo

### L2 — Entrada
- Todos los L1 pasan
- Fixtures de integración disponibles (`conftest.py`, `write_sine_wave`)
- Kernel se levanta en modo stub sin errores

### L2 — Salida
- Pipeline completo `audio → IPA → PER` retorna resultado sin excepción
- `CompareResult` contiene todos los campos requeridos (per, ops, alignment, meta)
- Kernel setup/teardown N veces sin memory leaks detectables

### L3 — Entrada
- Todos los L2 pasan
- API levantable con `PRONUNCIAPA_ASR=stub`
- Todos los endpoints documentados en `docs/api_contracts.md`

### L3 — Salida
- Todos los endpoints retornan HTTP correcto (200/201/422/404 según corresponde)
- Schemas de respuesta cumplen modelos Pydantic de `ipa_server/models.py`
- Inputs inválidos retornan 422, nunca 500

### L4 — Entrada
- Todos los L3 pasan
- Device/emulador disponible
- User journeys documentados en `conductor/product.md`

### L4 — Salida
- Journeys verificados manualmente o por scripting Flutter integration_test
- SLAs de rendimiento de `docs/QUALITY_SLA.md` verificados

---

## 6. User Journeys Bajo Prueba

| ID | Journey | Actor | Nivel |
|----|---------|-------|-------|
| UJ-01 | Graba audio → recibe score de pronunciación | Language Learner | L4 |
| UJ-02 | Instala plugin ASR → lo usa en pipeline | Developer | L3 |
| UJ-03 | Consulta tutorial de símbolo IPA | Language Learner | L3 |
| UJ-04 | Practica drill de par mínimo /p/-/b/ | Language Learner | L3 |
| UJ-05 | CLI transcribe archivo WAV | Developer | L3 |
| UJ-06 | CLI compara transcripción contra texto de referencia | Developer | L3 |

---

## 7. Trazabilidad hacia Requisitos

Ver [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md). Cada test debe tener marcado el ID de requisito que cubre.

---

## 8. Herramientas

| Herramienta | Versión | Uso |
|-------------|---------|-----|
| `pytest` | ≥ 8.3 | Runner principal |
| `pytest-asyncio` | ≥ 0.23 | Tests async (`asyncio_mode=auto`) |
| `pytest-cov` | ≥ 4.1 | Cobertura de código |
| `httpx` | ≥ 0.27 | Cliente HTTP para L3 |
| `hypothesis` | ≥ 6.100 | Property-based testing (PER, tokenización) |
| `unittest.mock` | stdlib | Stubs/mocks para L1 |

---

## 9. Organización de Marcadores pytest

```
pytest -m unit          → L1 (unitarios)
pytest -m integration   → L2 (integración)
pytest -m system        → L3 (sistema)
pytest -m e2e           → L4 (end-to-end)
pytest -m performance   → Atributo rendimiento (ISO 25010 §8.4)
pytest -m security      → Atributo seguridad  (ISO 25010 §8.5)
pytest -m reliability   → Atributo confiabilidad (ISO 25010 §8.3)
pytest -m flutter       → Tests de cliente móvil
pytest -m "not slow"    → Excluir tests > 5 s
```

---

## 10. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Kernel singleton contamina tests | Alta | Alto | Fixture `reset_kernel_singleton` autouse en conftest |
| Tests dependen de modelos externos | Media | Alto | Todo L1/L2/L3 corre con `PRONUNCIAPA_ASR=stub` |
| Cambio de `asyncio_mode` rompe suite | Baja | Alto | Mantener `asyncio_mode = "auto"` en pyproject.toml |
| Coverage < 80 % después del rehacimiento | Media | Medio | Verificar con `make test-quality-report` antes de merge |

---

## 11. Protocolo de Especificación de Tests

Antes de escribir cualquier test nuevo se siguen estos pasos:

1. **Identificar** función/endpoint: nombre, módulo, firma
2. **Mostrar inputs concretos** del código real
3. **Proponer ≥ 3 opciones de salida esperada** — incluyendo el comportamiento actual (posiblemente incorrecto) y el ideal
4. **Confirmar con el equipo** qué salida debe producir el sistema
5. **Escribir el test** assertando EXACTAMENTE lo confirmado

> Este protocolo garantiza que los tests especifican **calidad deseada**, no calidad accidental del código actual.
