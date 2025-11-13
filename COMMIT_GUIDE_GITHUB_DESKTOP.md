# Guía de Commits con GitHub Desktop

## Proceso de Versionamiento

### Paso 1: Configuración Inicial
1. Abrir la aplicación GitHub Desktop
2. Verificar repositorio activo: **PronunciaPA**
3. Confirmar rama de trabajo: **feature/CWesternBurger/pipeline-transcribe-cli**

### Paso 2: Revisión de Cambios

El panel izquierdo muestra todos los archivos modificados:

```
Archivos modificados:
  • ipa_core/api/cli.py
  • ipa_core/api/tests/test_cli_contract.py

Archivos nuevos:
  • COMMIT_GUIDE_CWESTERNBURGER.md
  • COMMIT_GUIDE_GITHUB_DESKTOP.md
  • EXPLICACION_SIMPLE.md
  • RESUMEN_TRABAJO.md
  • TESTING_CWESTERNBURGER.md
  • scripts/tests/test_cli_transcribe_stub.py
  • scripts/tests/test_transcribe_stub.py
```

### Paso 3: Primer Commit - Implementación CLI

#### 3.1 Selección de archivos
Marcar únicamente:
- `ipa_core/api/cli.py`
- `ipa_core/api/tests/test_cli_contract.py`

Los demás archivos se incluirán en commits posteriores.

#### 3.2 Escribir el mensaje del commit
En la parte inferior izquierda verás:

**Summary (required):**
```
Implementar función cli_transcribe con tokens de ejemplo para pruebas
```

**Description (opcional pero recomendado):**
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

#### 3.3 Confirmación del commit
Hacer clic en el botón "Commit to feature/CWesternBurger/pipeline-transcribe-cli"

Primer commit completado.

### Paso 4: Segundo Commit - Suite de Pruebas

Los archivos restantes permanecen sin versionar.

#### 4.1 Selección de archivos
Marcar únicamente:
- `scripts/tests/test_cli_transcribe_stub.py`
- `scripts/tests/test_transcribe_stub.py`

#### 4.2 Escribir el mensaje
**Summary:**
```
Agregar scripts de prueba para validar el pipeline de transcripción
```

**Description:**
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

#### 4.3 Confirmación del commit
Hacer clic en "Commit to feature/CWesternBurger/pipeline-transcribe-cli"

Segundo commit completado.

### Paso 5: Tercer Commit - Documentación

#### 5.1 Selección de archivos de documentación
Marcar los siguientes archivos:
- `COMMIT_GUIDE_CWESTERNBURGER.md`
- `COMMIT_GUIDE_GITHUB_DESKTOP.md`
- `EXPLICACION_SIMPLE.md`
- `RESUMEN_TRABAJO.md`
- `TESTING_CWESTERNBURGER.md`

#### 5.2 Escribir el mensaje
**Summary:**
```
Agregar documentación completa de testing, commits y explicación del trabajo
```

**Description:**
```
Se crearon 5 archivos de documentación para facilitar el entendimiento
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

4. RESUMEN_TRABAJO.md:
   - Resumen detallado de toda la implementación
   - Conceptos técnicos y patrones utilizados
   - Integración con otras ramas del sprint

5. EXPLICACION_SIMPLE.md:
   - Explicación en lenguaje claro de qué es el proyecto
   - Qué tarea se asignó y por qué
   - Cómo funcionan todas las partes

Ref: Sprint 01 - CWesternBurger - pipeline-transcribe-cli
```

#### 5.3 Confirmación del commit
Hacer clic en "Commit to feature/CWesternBurger/pipeline-transcribe-cli"

Tercer commit completado.

### Paso 6: Sincronización con Repositorio Remoto

Una vez finalizados todos los commits:

1. Localizar el botón "Push origin" en la parte superior (indicará el número de commits pendientes)
2. Hacer clic en "Push origin"
3. Aguardar la finalización del proceso de sincronización

Los cambios han sido publicados en el repositorio remoto.

## Representación Visual de la Interfaz

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Desktop                                    ⚙ ▼  │
├─────────────────────────────────────────────────────────┤
│  Current Repository: PronunciaPA                        │
│  Current Branch: feature/CWesternBurger/pipeline-...    │
├───────────────────┬─────────────────────────────────────┤
│                   │                                     │
│  Changes (7)      │  Diff View                         │
│                   │                                     │
│  [x] cli.py       │  @@ -43,7 +43,15 @@                │
│  [x] test_cli...  │  + return ["ˈo", "l", "a"]        │
│  [ ] test_trans...│                                     │
│  [ ] TESTING...   │                                     │
│  [ ] RESUMEN...   │                                     │
│                   │                                     │
├───────────────────┴─────────────────────────────────────┤
│  Summary (required)                                     │
│  feat(cli): implement cli_transcribe stub              │
│                                                         │
│  Description                                            │
│  - Remove NotImplementedError from cli_transcribe      │
│  - Return example IPA tokens...                        │
│                                                         │
│  [Commit to feature/CWesternBurger/pipeline-...]       │
└─────────────────────────────────────────────────────────┘
```

## Lista de Verificación

Antes de realizar commits:
- [ ] Confirmar rama de trabajo: **feature/CWesternBurger/pipeline-transcribe-cli**
- [ ] Validar ejecución exitosa de pruebas automatizadas
- [ ] Verificar selección correcta de archivos por commit
- [ ] Asegurar mensajes descriptivos y profesionales

Después de sincronización:
- [ ] Validar commits en repositorio remoto
- [ ] Considerar creación de Pull Request según cronograma del sprint

## Buenas Prácticas para Mensajes de Commit

### Mensajes apropiados (en español)
```
Implementar función cli_transcribe con tokens de ejemplo para pruebas
Agregar scripts de prueba para validar el pipeline de transcripción
Agregar documentación completa de testing, commits y explicación del trabajo
```

### Mensajes inadecuados
```
cambios
update
fix stuff
arreglos varios
commit
```

### Características de mensajes apropiados
```
✓ Describe QUÉ se hizo (no cómo)
✓ Usa verbos en infinitivo (Implementar, Agregar, Corregir)
✓ Es específico y claro
✓ Menciona los archivos/componentes principales
✓ En español para este proyecto

Estructura recomendada:
[Título corto pero descriptivo]

[Descripción detallada con:
- Qué se cambió
- Por qué se cambió
- Qué archivos se afectaron
- Resultado esperado]
```

---

## 🔍 Ver tus commits en GitHub

Después de hacer push:

1. Ve a https://github.com/Pedro-Samuel-Rodriguez-Caudillo/PronunciaPA
2. Click en el dropdown de branches (arriba a la izquierda)
3. Selecciona: **feature/CWesternBurger/pipeline-transcribe-cli**
4. Click en **"commits"** para ver tu historial
5. Deberías ver tus 3 commits con los mensajes que escribiste

---

## 🚀 Crear Pull Request (cuando estés listo)

**NO lo hagas todavía** - espera a que ricardo840 y Pedro-Samuel terminen.

Cuando llegue el momento:

1. En GitHub Desktop, click en **"Branch"** → **"Create Pull Request"**
2. O ve a GitHub.com y verás un botón verde: **"Compare & pull request"**
3. Escribe un título descriptivo
4. Agrega descripción explicando tus cambios
5. Click en **"Create pull request"**

---

## ❓ Preguntas Frecuentes

### P: ¿Puedo deshacer un commit?
**R:** Sí, en GitHub Desktop:
- Click derecho en el commit → **"Revert this commit"**
- O en el menú: **History** → click derecho → **Undo commit** (si aún no hiciste push)

### P: ¿Qué pasa si me equivoco en el mensaje?
**R:** Si aún NO hiciste push:
- Click derecho en el commit → **"Amend commit"**
- Edita el mensaje
- Click en **"Amend last commit"**

### P: ¿Puedo hacer un solo commit grande en vez de 3?
**R:** Sí, pero NO es recomendado. Es mejor separar:
- Código fuente (commit 1)
- Tests (commit 2)
- Documentación (commit 3)

Esto hace que el historial sea más claro.

### P: ¿Cuándo hago push?
**R:** Después de hacer todos tus commits. GitHub Desktop te mostrará un botón "Push origin" con un número indicando cuántos commits hay por subir.

---

## 📞 ¿Necesitas ayuda?

Si algo no funciona:
1. Verifica que estés en la rama correcta
2. Asegúrate de que GitHub Desktop esté actualizado
3. Si ves conflictos, consulta antes de resolverlos

---

**¡Hacer commits con GitHub Desktop es fácil!** 🎉

Solo recuerda:
1. Seleccionar archivos relacionados
2. Escribir mensajes descriptivos
3. Hacer push cuando termines

¡Buena suerte! 🚀
