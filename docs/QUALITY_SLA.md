# SLAs de Calidad — PronunciaPA
**Versión:** 1.0  
**Fecha:** 2026-03-10  
**Norma:** ISO/IEC 25010:2023 §8 (Características de Calidad del Producto)

> Estos valores son los umbrales mínimos aceptables. Un test que falla contra estos valores significa que el **software no cumple el estándar de calidad**, no que el test está mal.

---

## §8.1 Corrección Funcional

| Métrica | Umbral mínimo | Justificación |
|---------|--------------|--------------|
| Phone Error Rate (PER) — pronunciación idéntica | = 0.0 | Por definición matemática |
| PER — pronunciación completamente distinta | > 0.5 | Un sistema que clasifica como "igual" audio completamente diferente es inútil |
| PER — rango de valores posibles | [0.0, 1.0] | Invariante del algoritmo de Levenshtein normalizado |
| Tokens IPA no vacíos tras transcripción con audio válido | len(tokens) ≥ 1 | El sistema debe producir algún resultado con audio que contiene voz |
| `CompareResult` contiene campos obligatorios | per, ops, alignment, meta siempre presentes | Contrato de la API |

---

## §8.4 Eficiencia de Rendimiento

| Métrica | Umbral | Entorno | Herramienta |
|---------|--------|---------|-------------|
| Tiempo total de `execute_pipeline()` en modo stub | < 2 s | CPU, sin GPU | `@pytest.mark.performance` |
| Latencia `/v1/transcribe` p95 modo stub | < 2 000 ms | Localhost | `@pytest.mark.performance` |
| Latencia `/health` | < 500 ms | Localhost, sin modelos cargados | `@pytest.mark.performance` |
| Tiempo de setup de Kernel (stub) | < 500 ms | — | `@pytest.mark.performance` |

---

## §8.3 Confiabilidad

| Métrica | Umbral | Descripción |
|---------|--------|------------|
| Kernel setup/teardown idempotente | 3 ciclos sin error | Crea y destruye el Kernel 3 veces seguidas |
| Pipeline con audio de silencio | No lanza excepción no manejada | Debe retornar error descriptivo a la capa superior |
| Plugin ausente en registry | No lanza `KeyError` desnudo | Debe lanzar excepción del dominio con mensaje útil |

---

## §8.5 Seguridad

| Amenaza | Comportamiento esperado | Referencia |
|---------|------------------------|-----------|
| Path traversal en `audio_path` (`../../../etc/passwd`) | `ValueError` o HTTP 422 antes de acceder al FS | OWASP A01 |
| Archivo de audio de 0 bytes | Error descriptivo, no `ZeroDivisionError` o crash de numpy | OWASP A05 |
| Texto de referencia con null bytes (`\x00`) | No crash, error descriptivo | OWASP A03 |
| Archivo de audio sin extensión WAV/MP3/OGG | Rechazado con mensaje claro, no stack trace | OWASP A05 |

---

## §8.6 Usabilidad (API HTTP)

| Situación | Código HTTP esperado | Body esperado |
|-----------|---------------------|--------------|
| Request bien formado | 200 / 201 | Schema Pydantic válido |
| Audio inválido o corrupto | 422 | `detail` con descripción legible |
| Texto de referencia vacío | 422 | `detail` con descripción legible |
| Endpoint inexistente | 404 | Body estándar FastAPI |
| Error interno inesperado | 500 | Solo admisible si el input era válido (bug real) |

---

## §8.6 Usabilidad (CLI)

| Situación | Exit code esperado |
|-----------|-------------------|
| Comando ejecutado correctamente | 0 |
| Argumento inválido | 1 (mensaje de error en stderr) |
| Archivo no encontrado | 2 (mensaje legible) |
| Error interno | 1 con traceback legible |

---

## §8.9 Portabilidad

| Plataforma | Estado mínimo requerido |
|-----------|------------------------|
| Python 3.10 en Windows 11 | Suite L1/L2/L3 pasa completamente |
| Python 3.10 en Ubuntu 22.04 | Suite L1/L2/L3 pasa completamente |
| Flutter Android | L4 journeys UJ-01..UJ-04 completan |
| Flutter iOS | L4 journeys UJ-01..UJ-04 completan (cuando CI/emulador disponible) |

---

## Cobertura de Tests

| Métrica | Umbral mínimo |
|---------|--------------|
| Cobertura de código (`ipa_core/`) | ≥ 80 % (backstop) |
| Cobertura de requisitos RF-01..RF-13 | ≥ 95 % (criterio primario) |
| Atributos QA-01..QA-08 con test | 100 % |
