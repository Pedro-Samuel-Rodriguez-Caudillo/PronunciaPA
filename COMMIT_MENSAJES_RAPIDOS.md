# Mensajes de Commit - Referencia Rápida

## Commits Requeridos para la Rama

### COMMIT 1: Implementación de CLI

**Archivos a incluir:**
- `ipa_core/api/cli.py`
- `ipa_core/api/tests/test_cli_contract.py`

**Título:**
```
Implementar función cli_transcribe con tokens de ejemplo para pruebas
```

**Descripción:**
```
Se modificó la función cli_transcribe en ipa_core/api/cli.py para que:
- Ya no lance NotImplementedError
- Retorne una lista de tokens IPA de ejemplo ["ˈo", "l", "a"]
- Documente los flags esperados para el futuro (--audio, --lang, --config, etc.)

Se agregó prueba en test_cli_contract.py que verifica:
- La función cli_transcribe existe
- Retorna una lista de strings
- No lanza excepciones

Ref: Sprint 01 - CWesternBurger - pipeline-transcribe-cli
```

### COMMIT 2: Suite de Pruebas

**Archivos a incluir:**
- `scripts/tests/test_cli_transcribe_stub.py`
- `scripts/tests/test_transcribe_stub.py`

**Título:**
```
Agregar scripts de prueba para validar el pipeline de transcripción
```

**Descripción:**
```
Se crearon dos archivos de prueba en scripts/tests/:

1. test_cli_transcribe_stub.py:
   - Verifica que cli_transcribe existe y funciona
   - Valida que retorna una lista de tokens
   - Confirma que no lanza errores

2. test_transcribe_stub.py:
   - Prueba el pipeline completo con componentes stub
   - Incluye BasicPreprocessor para normalización
   - Incluye StubASR para simular reconocimiento de voz
   - Incluye StubTextRef para conversión texto a IPA
   - Valida flujo con tokens y con raw_text

Todas las pruebas pasan exitosamente.

Ref: Sprint 01 - CWesternBurger - pipeline-transcribe-cli
```

### COMMIT 3: Documentación Técnica

**Archivos a incluir:**
- `COMMIT_GUIDE_CWESTERNBURGER.md`
- `COMMIT_GUIDE_GITHUB_DESKTOP.md`
- `COMMIT_MENSAJES_RAPIDOS.md`
- `EXPLICACION_SIMPLE.md`
- `RESUMEN_TRABAJO.md`
- `TESTING_CWESTERNBURGER.md`

**Título:**
```
Agregar documentación completa de testing, commits y explicación del trabajo
```

**Descripción:**
```
Se crearon 6 archivos de documentación para facilitar el entendimiento
y uso del código implementado:

1. TESTING_CWESTERNBURGER.md:
   - Guía de cómo ejecutar las pruebas
   - Resultados esperados
   - Solución de problemas comunes

2. COMMIT_GUIDE_CWESTERNBURGER.md:
   - Guía de commits desde línea de comandos
   - Mensajes sugeridos con formato Conventional Commits

3. COMMIT_GUIDE_GITHUB_DESKTOP.md:
   - Guía paso a paso para hacer commits desde GitHub Desktop
   - Instrucciones visuales y detalladas

4. COMMIT_MENSAJES_RAPIDOS.md:
   - Mensajes de commit listos para copiar y pegar
   - Versión rápida de la guía

5. RESUMEN_TRABAJO.md:
   - Resumen detallado de toda la implementación
   - Conceptos técnicos y patrones utilizados
   - Integración con otras ramas del sprint

6. EXPLICACION_SIMPLE.md:
   - Explicación en lenguaje claro de qué es el proyecto
   - Qué tarea se asignó y por qué
   - Cómo funcionan todas las partes

Ref: Sprint 01 - CWesternBurger - pipeline-transcribe-cli
```

## Procedimiento en GitHub Desktop

1. Abrir aplicación GitHub Desktop
2. Verificar rama activa: `feature/CWesternBurger/pipeline-transcribe-cli`
3. Para cada commit:
   - Seleccionar únicamente los archivos correspondientes
   - Copiar el contenido de "Título" al campo "Summary"
   - Copiar el contenido de "Descripción" al campo "Description"
   - Confirmar con "Commit to feature/CWesternBurger/pipeline-transcribe-cli"
4. Al finalizar los 3 commits:
   - Hacer clic en "Push origin"
   - Aguardar finalización de sincronización

## Lista de Verificación

Antes de sincronizar:
- [ ] Tres commits completados
- [ ] Cada commit incluye título y descripción
- [ ] Mensajes redactados en español
- [ ] Pruebas automatizadas ejecutadas exitosamente

## Verificación en Repositorio Remoto

Posterior a la sincronización:
1. Acceder a: https://github.com/Pedro-Samuel-Rodriguez-Caudillo/PronunciaPA
2. Seleccionar rama: `feature/CWesternBurger/pipeline-transcribe-cli`
3. Navegar a historial de commits
4. Verificar presencia de los 3 commits con mensajes completos
