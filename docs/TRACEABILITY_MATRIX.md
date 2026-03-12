# Matriz de Trazabilidad — Requisitos ↔ Tests
**Versión:** 1.0  
**Fecha:** 2026-03-10  
**Norma:** ISO/IEC/IEEE 29119-3 §7.3 (Test Design Specification)

> La cobertura de calidad se mide por **requisitos funcionales cubiertos**, no por porcentaje de código.  
> Target: ≥ 95 % de RF-01..RF-13 (core) trazados con estado ✅ antes de cada release.

---

## Fuentes de Requisitos

| Fuente | Descripción |
|--------|------------|
| [`conductor/product.md`](../conductor/product.md) | Requisitos funcionales del motor (RF-01..RF-06) |
| [`conductor/business-model.md`](../conductor/business-model.md) | Requisitos del producto (RF-07..RF-20) |
| [`docs/api_contracts.md`](api_contracts.md) | Contratos HTTP de la API |

---

## Tabla de Trazabilidad

| ID Req | Descripción | Archivo de Test :: nombre del test | Nivel | Marker | Estado |
|--------|-------------|-----------------------------------|-------|--------|--------|
| **RF-01** | ASR convierte audio a tokens IPA | `ipa_core/pipeline/tests/test_runner.py::test_execute_pipeline_raises_when_asr_returns_no_tokens` | L1 | `unit`,`functional` | ✅ implementado y pasando |
| **RF-02** | Comparador calcula PER (Levenshtein) entre tokens IPA | `ipa_core/compare/tests/test_levenshtein.py::test_per_is_zero_for_identical_pronunciation`, `ipa_core/compare/tests/test_levenshtein.py::test_per_for_single_substitution_uses_articulatory_similarity_band`, `ipa_core/compare/tests/test_levenshtein.py::test_per_is_one_for_completely_different_sequences` | L1 | `unit`,`functional` | ✅ implementado y pasando |
| **RF-03** | Detalles de errores fonéticos visibles (alignment) | `ipa_core/compare/tests/test_levenshtein.py::test_compare_rejects_empty_reference_and_hypothesis`, `ipa_core/compare/tests/test_levenshtein.py::test_ops_include_eq_and_sub_in_order` | L1 | `unit`,`functional` | ✅ implementado y pasando |
| **RF-04** | Operación offline — sin conexión a internet | `ipa_core/pipeline/tests/test_runner.py::test_execute_pipeline_uses_custom_comparator_and_scales_score_to_100` | L2 | `integration`,`functional` | ✅ implementado y pasando |
| **RF-05** | Benchmark mide PER y RTF | — | L2 | `performance` | ⏳ pendiente |
| **RF-06** | Sistema de plugins permite agregar backends | — | L2 | `integration` | ⏳ pendiente |
| **RF-07** | Usuario graba audio y recibe feedback IPA preciso | `ipa_server/tests/test_pipeline_api.py::test_transcribe_returns_transcription_response_schema`, `ipa_server/tests/test_pipeline_api.py::test_compare_returns_score_and_alignment_payload` | L3 | `system`,`functional` | ✅ implementado y pasando |
| **RF-08** | Tutorial interactivo de símbolos IPA disponible | — | L3 | `system` | ⏳ pendiente |
| **RF-09** | Audio de referencia TTS disponible por sonido | — | L3 | `system` | ⏳ pendiente |
| **RF-10** | Drills de práctica disponibles (aislado, sílaba, palabra) | — | L3 | `system` | ⏳ pendiente |
| **RF-11** | Pares mínimos disponibles para distinción auditiva | — | L1 | `unit` | ⏳ pendiente |
| **RF-12** | Soporte multilingüe (≥ es, en) | — | L1 | `unit` | ⏳ pendiente |
| **RF-13** | Operación offline básica | — | L2 | `integration` | ⏳ pendiente |
| **RF-14** | Dashboard de métricas de grupo (B2B Team) | — | — | — | 🔵 fuera de scope v1 |
| **RF-15** | Reportes exportables de progreso | — | — | — | 🔵 fuera de scope v1 |
| **RF-16** | Contenido personalizado (Business) | — | — | — | 🔵 fuera de scope v1 |
| **RF-17** | API de integración LMS | — | L3 | `system` | ⏳ pendiente |
| **RF-18** | White-label | — | — | — | 🔵 fuera de scope v1 |
| **RF-19** | SSO/SAML | — | — | — | 🔵 fuera de scope v1 |
| **RF-20** | Soporte prioritario SLA | — | — | — | 🔵 fuera de scope v1 |

---

## Atributos de Calidad No-Funcionales (ISO 25010)

| ID | Atributo | SLA | Archivo de Test :: nombre | Marker | Estado |
|----|---------|-----|--------------------------|--------|--------|
| **QA-01** | Rendimiento — `execute_pipeline()` < 2 s | Pipeline stub completo termina en < 2 s | `ipa_server/tests/test_nonfunctional_quality.py::test_execute_pipeline_finishes_under_two_seconds_in_stub_mode` | `performance` | ✅ implementado y pasando |
| **QA-02** | Rendimiento — Latencia API p95 < 2 s | `/v1/transcribe` stub | — | `performance` | ⏳ pendiente |
| **QA-03** | Seguridad — Path traversal rechazado | No procesable `../../../etc/passwd` ni rutas externas arbitrarias | `ipa_server/tests/test_nonfunctional_quality.py::test_feedback_rejects_client_supplied_external_prompt_path_before_fs_use` | `security` | ✅ implementado y pasando |
| **QA-04** | Seguridad — Input 0 bytes rechazado | Error descriptivo, no crash | `ipa_server/tests/test_nonfunctional_quality.py::test_compare_empty_audio_returns_descriptive_validation_without_traceback` | `security` | ✅ implementado y pasando |
| **QA-05** | Confiabilidad — Kernel idempotente | Setup/teardown × 3 sin error | `ipa_server/tests/test_nonfunctional_quality.py::test_kernel_singleton_survives_three_create_destroy_cycles` | `reliability` | ✅ implementado y pasando |
| **QA-06** | Confiabilidad — Audio silencio no crashea | Error descriptivo | `ipa_core/pipeline/tests/test_runner.py::test_execute_pipeline_blocks_on_no_speech_quality_issue` | `reliability`,`functional` | ✅ implementado y pasando |
| **QA-07** | Usabilidad — Inputs inválidos retornan 422 | No 500 | `ipa_server/tests/test_pipeline_api.py::test_compare_rejects_invalid_audio_with_422_not_500`, `ipa_server/tests/test_pipeline_api.py::test_quick_compare_returns_descriptive_validation_error_when_asr_has_no_tokens`, `ipa_server/tests/test_pipeline_api.py::test_feedback_rejects_missing_prompt_path_immediately` | `system`,`usability` | ✅ implementado y pasando |
| **QA-08** | Usabilidad — CLI retorna exit code 0 en uso correcto | `result.exit_code == 0` | — | `system` | ⏳ pendiente |
| **QA-09** | Rendimiento — Latencia `/health` < 500 ms | `GET /health` en modo stub | `ipa_server/tests/test_nonfunctional_quality.py::test_health_endpoint_responds_within_500ms` | `performance` | ✅ implementado y pasando |
| **QA-10** | Confiabilidad — Plugin faltante produce error claro | `plugin_not_found` con detalle legible | `ipa_server/tests/test_nonfunctional_quality.py::test_missing_plugin_returns_clear_client_error` | `reliability` | ✅ implementado y pasando |

---

## Leyenda de Estado

| Símbolo | Significado |
|---------|------------|
| ✅ | Test implementado y pasando |
| ❌ | Test implementado pero fallando (bug a corregir en código) |
| ⏳ | Pendiente de implementar |
| 🔵 | Fuera de scope del release actual |

---

## Cobertura Actual

```
RF Core (RF-01..RF-13):    4 implementados
    - pasando:              4
    - fallando:             0

QA No-funcional:          8 implementados
    - pasando:              8
    - fallando:             0
    - pendientes:           2

Objetivo pre-release:     RF Core ≥ 95 % cubiertos
                                                    QA Non-functional 100 % implementados y pasando
```

> Esta tabla se actualiza automáticamente conforme se implementan y pasan los tests.  
> Cada test nuevo debe referenciar el ID de requisito en su docstring.
