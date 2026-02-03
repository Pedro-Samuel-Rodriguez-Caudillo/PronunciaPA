# Solución al Problema de Descarga de Modelos - Resumen de Implementación

## 🔍 Problema Identificado

La aplicación no funcionaba porque la configuración por defecto (`configs/local.yaml`) asumía que todos los modelos estaban instalados, pero en una instalación nueva faltaban:

1. **Allosaurus ASR** - Backend obligatorio para reconocimiento fonético
2. **eSpeak-NG** - Binario del sistema para conversión texto→IPA
3. **Ollama + TinyLlama** - LLM opcional para feedback inteligente
4. **Modelos Piper TTS** - Síntesis de voz (opcional)

Cada componente faltante generaba `NotReadyError` (HTTP 503), haciendo que la aplicación no funcionara.

---

## ✅ Solución Implementada

### 1. **Sistema de Fallback Automático** (`PRONUNCIAPA_STRICT_MODE`)

**Archivos modificados:**
- `ipa_core/config/schema.py` - Agregado campo `strict_mode: bool`
- `ipa_core/config/loader.py` - Lectura de variable `PRONUNCIAPA_STRICT_MODE`
- `ipa_core/plugins/registry.py` - Auto-fallback a stubs cuando `strict_mode=false`
- `ipa_core/kernel/core.py` - Propagación de strict_mode a todos los resolutores

**Comportamiento:**
- **`strict_mode: false`** (default): Si un componente falla, usa automáticamente fallbacks (stub/grapheme) y loguea warning
- **`strict_mode: true`**: Falla inmediatamente con error claro sobre qué falta

**Uso:**
```bash
# Modo flexible (desarrollo)
export PRONUNCIAPA_STRICT_MODE=false

# Modo estricto (producción)
export PRONUNCIAPA_STRICT_MODE=true
```

---

### 2. **Allosaurus como Dependencia Obligatoria**

**Archivo modificado:** `pyproject.toml`

**Cambios:**
- Movido `allosaurus>=1.0.0,<2` de `[speech]` a `dependencies` principales
- Movido `numpy>=1.26,<3` también (requerido por allosaurus)

**Razón:** Allosaurus es el único backend ASR que produce IPA directamente, es indispensable para el sistema.

**Impacto:** Ahora se instala automáticamente con `pip install -e .`

---

### 3. **Endpoint `/health` Mejorado con Diagnóstico**

**Archivo modificado:** `ipa_server/main.py`

**Antes:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "local_models": 2
}
```

**Ahora:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "strict_mode": false,
  "components": {
    "asr": {
      "name": "allosaurus",
      "ready": true,
      "output_type": "ipa"
    },
    "textref": {
      "name": "espeak",
      "ready": false,
      "error": "No se encontró 'espeak' ni 'espeak-ng'..."
    },
    "llm": {
      "name": "ollama",
      "ready": false,
      "error": "Ollama server not responding..."
    }
  },
  "language_packs": ["en-us"],
  "local_models": 1
}
```

**Beneficio:** Ahora es fácil ver qué componentes están listos y qué falta instalar.

---

### 4. **Nuevo Endpoint `/api/setup-status`**

**Archivo modificado:** `ipa_server/main.py`

**Propósito:** Retorna instrucciones específicas para el OS actual sobre cómo instalar cada componente faltante.

**Respuesta de ejemplo (Windows):**
```json
{
  "os": "Windows",
  "strict_mode": false,
  "checks": {
    "allosaurus": {
      "installed": true,
      "version": "1.0.2",
      "instructions": null
    },
    "espeak": {
      "installed": false,
      "instructions": {
        "url": "https://github.com/espeak-ng/espeak-ng/releases",
        "description": "Descargar e instalar eSpeak NG para Windows",
        "env_var": "PRONUNCIAPA_ESPEAK_BIN=C:\\Program Files\\eSpeak NG\\espeak-ng.exe"
      }
    },
    "ollama": {
      "installed": false,
      "running": false,
      "instructions": {
        "url": "https://ollama.ai/download",
        "commands": [
          "# Descargar e instalar Ollama",
          "ollama pull tinyllama",
          "ollama serve"
        ],
        "description": "Instalar Ollama para soporte de LLM"
      }
    },
    "models_script": {
      "available": true,
      "instructions": {
        "command": "python scripts/download_models.py",
        "description": "Descargar modelos de Allosaurus y otros componentes"
      }
    }
  }
}
```

---

### 5. **Wizard de Configuración en Frontend**

**Archivos creados:**
- `frontend/src/wizard.ts` - Lógica del wizard con TypeScript vanilla
- Contenedor agregado a `frontend/public/index.html`

**Archivos modificados:**
- `frontend/src/main.ts` - Auto-verificación de health al cargar la página

**Flujo:**
1. Al cargar el frontend, consulta `/health`
2. Si detecta componentes no listos (`asr.ready=false` o `textref.ready=false`):
   - Muestra modal automáticamente con el wizard
3. El wizard consulta `/api/setup-status`
4. Renderiza checklist visual con:
   - ✅ Componentes instalados (verde)
   - ❌ Componentes faltantes (rojo) con instrucciones
   - Comandos copiables con botón "Copiar"
   - Links directos a descargas

**Características:**
- Detección automática del OS (Windows/Linux/macOS)
- Comandos específicos por plataforma
- Botones para copiar comandos al portapapeles
- Detección de rutas de instalación típicas (Windows)
- Cierre manual o automático cuando todo está listo

---

### 6. **Configuración Mínima sin Modelos**

**Archivo creado:** `configs/minimal.yaml`

**Contenido:**
```yaml
version: 1
strict_mode: false
backend:
  name: stub  # No requiere modelos
textref:
  name: grapheme  # No requiere eSpeak
```

**Uso:**
```bash
export PRONUNCIAPA_CONFIG=configs/minimal.yaml
uvicorn ipa_server.main:get_app --reload
```

**Beneficio:** Permite arrancar el sistema inmediatamente sin instalar nada extra, útil para desarrollo.

---

### 7. **Documentación Completa en README**

**Archivo modificado:** `README.md`

**Secciones agregadas:**
- **"Instalación Completa con Modelos de Producción"**
  - Instrucciones paso a paso para Windows/Linux/macOS
  - Instalación de eSpeak-NG por plataforma
  - Uso del script `download_models.py`
  - Configuración de Ollama (opcional)
- **"Modo Strict vs Flexible"**
  - Explicación de `PRONUNCIAPA_STRICT_MODE`
  - Casos de uso recomendados
- **"Wizard de Configuración Automático"**
  - Descripción de la interfaz visual
  - Funcionalidades del wizard

---

## 🚀 Cómo Usar la Solución

### Opción A: Arranque Rápido sin Modelos (Desarrollo)

```bash
# 1. Instalar dependencias básicas
pip install -e ".[dev]"

# 2. Usar configuración mínima
export PRONUNCIAPA_CONFIG=configs/minimal.yaml

# 3. Iniciar servidor
uvicorn ipa_server.main:get_app --reload --port 8000

# 4. Abrir frontend
cd frontend && npm install && npm run dev
```

**Resultado:** Sistema funcional con stubs, sin modelos pesados.

---

### Opción B: Instalación Completa con Wizard

```bash
# 1. Instalar dependencias completas
pip install -e ".[dev,speech]"

# 2. Iniciar servidor (con auto-fallback)
uvicorn ipa_server.main:get_app --reload --port 8000

# 3. Abrir frontend
cd frontend && npm install && npm run dev

# 4. Navegar a http://localhost:5173
# El wizard se mostrará automáticamente y te guiará
```

**Resultado:** El wizard detecta qué falta y muestra comandos específicos para instalar.

---

### Opción C: Instalación Manual Guiada

```bash
# 1. Instalar dependencias
pip install -e ".[dev,speech]"

# 2. Instalar eSpeak-NG
# Windows: Descargar desde GitHub releases
# Linux: sudo apt-get install espeak-ng
# macOS: brew install espeak-ng

# 3. Descargar modelos
python scripts/download_models.py

# 4. (Opcional) Instalar Ollama
# Descargar desde https://ollama.ai/download
ollama pull tinyllama
ollama serve

# 5. Iniciar servidor
uvicorn ipa_server.main:get_app --reload --port 8000
```

**Resultado:** Sistema completo con todos los componentes.

---

## 📊 Verificación del Estado

### Via API
```bash
# Ver estado de componentes
curl http://localhost:8000/health | jq '.components'

# Ver instrucciones de instalación
curl http://localhost:8000/api/setup-status | jq '.checks'
```

### Via Frontend
- Abrir `http://localhost:5173`
- Si hay problemas, el wizard aparecerá automáticamente
- Si todo está OK, verás "¡Sistema Listo!"

---

## 🎯 Beneficios de esta Solución

1. **✅ Sin bloqueos:** El sistema arranca aunque falten componentes (modo flexible)
2. **🔍 Diagnóstico claro:** Endpoints `/health` y `/api/setup-status` muestran exactamente qué falta
3. **🧙 Auto-ayuda:** El wizard en el frontend guía la instalación paso a paso
4. **🖥️ Multi-plataforma:** Instrucciones específicas para Windows/Linux/macOS
5. **📋 Copiable:** Comandos con botón de copiar para evitar errores
6. **🚀 Arranque rápido:** Configuración mínima permite desarrollo sin modelos
7. **🔒 Producción segura:** Modo strict falla rápido con errores claros

---

## 📝 Archivos Modificados

- `pyproject.toml` - Allosaurus como dependencia obligatoria
- `ipa_core/config/schema.py` - Campo `strict_mode`
- `ipa_core/config/loader.py` - Lectura de `PRONUNCIAPA_STRICT_MODE`
- `ipa_core/plugins/registry.py` - Auto-fallback logic
- `ipa_core/kernel/core.py` - Propagación de strict_mode
- `ipa_server/main.py` - Endpoints `/health` y `/api/setup-status` mejorados
- `frontend/src/wizard.ts` - Wizard de configuración (nuevo)
- `frontend/src/main.ts` - Auto-verificación de health
- `frontend/public/index.html` - Contenedor del wizard
- `README.md` - Documentación completa de instalación
- `configs/minimal.yaml` - Configuración mínima (nuevo)

---

## 🧪 Testing

```bash
# Ejecutar tests para verificar que todo funciona
python -m pytest -v

# Test específico del sistema de fallback
python -m pytest ipa_core/tests/ -k "registry" -v

# Test del servidor
python -m pytest ipa_server/tests/ -v
```

---

## 🐛 Troubleshooting

### "NotReadyError: Allosaurus no instalado"
```bash
# Solución
pip install allosaurus
python scripts/download_models.py
```

### "NotReadyError: No se encontró 'espeak' ni 'espeak-ng'"
```bash
# Windows: Descargar desde GitHub
# https://github.com/espeak-ng/espeak-ng/releases

# Linux
sudo apt-get install espeak-ng

# macOS
brew install espeak-ng
```

### "NotReadyError: Ollama server not responding"
```bash
# Instalar Ollama
# https://ollama.ai/download

# Descargar modelo
ollama pull tinyllama

# Iniciar servidor
ollama serve
```

### El wizard no aparece automáticamente
1. Abrir consola del navegador (F12)
2. Verificar errores de conexión
3. Verificar que el backend esté corriendo: `curl http://localhost:8000/health`

---

## 📚 Recursos Adicionales

- **eSpeak-NG Releases:** https://github.com/espeak-ng/espeak-ng/releases
- **Ollama Download:** https://ollama.ai/download
- **Allosaurus Docs:** https://github.com/xinjli/allosaurus
- **PronunciaPA Docs:** `docs/` folder

---

**Fecha de implementación:** 31 de enero de 2026  
**Versión:** 0.1.0
