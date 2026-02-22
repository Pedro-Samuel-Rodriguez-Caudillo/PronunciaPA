#!/usr/bin/env bash
# PronunciaPA — Instalación completa para Linux / macOS
# ──────────────────────────────────────────────────────
# Uso:
#   bash scripts/install.sh            # instalación interactiva
#   bash scripts/install.sh --minimal  # solo dependencias Python sin modelos
#   bash scripts/install.sh --full     # Python + Allosaurus + CMU Dict
#
# Lo que hace:
#   1. Detecta OS y Python
#   2. Crea virtualenv en .venv/ (opcional, recomendado)
#   3. Instala dependencias Python con pip
#   4. Verifica eSpeak-NG e indica cómo instalarlo
#   5. Descarga corpus CMU Dict de NLTK (si se pide)
#   6. Copia configs/local.example.yaml → configs/local.yaml (si no existe)
#   7. Muestra comando de inicio del servidor

set -euo pipefail

# ── Colores ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[info]${NC} $*"; }
ok()      { echo -e "${GREEN}[ok]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC} $*"; }
error()   { echo -e "${RED}[error]${NC} $*" >&2; }
header()  { echo -e "\n${BOLD}$*${NC}"; }

# ── Flags ────────────────────────────────────────────────────────────────────
MINIMAL=false
FULL=false
SKIP_VENV=false

for arg in "$@"; do
  case $arg in
    --minimal)   MINIMAL=true ;;
    --full)      FULL=true ;;
    --no-venv)   SKIP_VENV=true ;;
    -h|--help)
      echo "Uso: $0 [--minimal|--full] [--no-venv]"
      echo "  --minimal  Solo pip install -e '.[dev]' sin modelos"
      echo "  --full     Incluye Allosaurus, CMU Dict, client Ollama"
      echo "  --no-venv  No crear virtualenv (usar Python del sistema)"
      exit 0
      ;;
  esac
done

# ── Detectar Python ──────────────────────────────────────────────────────────
header "1. Verificando Python"

PYTHON=""
for cmd in python3.11 python3.10 python3.9 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    VER=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=${VER%.*}; MINOR=${VER#*.}
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
      PYTHON="$cmd"; ok "Usando $cmd ($VER)"; break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  error "Python 3.9+ no encontrado. Instala desde https://python.org"
  exit 1
fi

# ── Virtualenv ───────────────────────────────────────────────────────────────
header "2. Entorno virtual"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"

if [ "$SKIP_VENV" = true ]; then
  warn "Saltando creación de virtualenv (--no-venv)"
  PIP="pip"
  PYTHON_BIN="$PYTHON"
else
  if [ -d "$VENV" ]; then
    ok "Virtualenv ya existe en .venv/"
  else
    info "Creando virtualenv en .venv/ ..."
    "$PYTHON" -m venv "$VENV"
    ok "Virtualenv creado"
  fi
  PIP="$VENV/bin/pip"
  PYTHON_BIN="$VENV/bin/python"
fi

# ── Instalar dependencias Python ─────────────────────────────────────────────
header "3. Instalando dependencias Python"

EXTRAS="dev"
if [ "$FULL" = true ]; then
  EXTRAS="dev,speech,asr,ollama,cmudict"
  info "Modo --full: instalando Allosaurus + speech + CMU Dict + Ollama client"
elif [ "$MINIMAL" = false ]; then
  # interactivo
  echo ""
  echo "  [1] Mínimo  — pip install -e '.[dev]'          (solo stub, más rápido)"
  echo "  [2] Estándar — pip install -e '.[dev,speech]'  (eSpeak + audio processing)"
  echo "  [3] Completo — pip install -e '.[dev,speech,asr,ollama,cmudict]'"
  echo ""
  read -rp "Elige [1/2/3, default=2]: " CHOICE
  case "${CHOICE:-2}" in
    1) EXTRAS="dev" ;;
    3) EXTRAS="dev,speech,asr,ollama,cmudict" ;;
    *) EXTRAS="dev,speech" ;;
  esac
fi

info "Ejecutando: pip install -e '.[$EXTRAS]'"
"$PIP" install --upgrade pip -q
"$PIP" install -e "$REPO_ROOT/.[$EXTRAS]"
ok "Dependencias Python instaladas"

# ── eSpeak-NG ────────────────────────────────────────────────────────────────
header "4. Verificando eSpeak-NG"

if command -v espeak-ng &>/dev/null || command -v espeak &>/dev/null; then
  ESPEAK_BIN=$(command -v espeak-ng 2>/dev/null || command -v espeak)
  ok "eSpeak-NG encontrado: $ESPEAK_BIN"
else
  warn "eSpeak-NG NO encontrado. Es necesario para TextRef y TTS."
  echo ""
  OS="$(uname -s)"
  case "$OS" in
    Linux)
      if command -v apt-get &>/dev/null; then
        echo -e "  ${BOLD}sudo apt install espeak-ng${NC}"
      elif command -v dnf &>/dev/null; then
        echo -e "  ${BOLD}sudo dnf install espeak-ng${NC}"
      elif command -v pacman &>/dev/null; then
        echo -e "  ${BOLD}sudo pacman -S espeak-ng${NC}"
      else
        echo "  Instala espeak-ng desde el gestor de paquetes de tu distro."
      fi
      ;;
    Darwin)
      echo -e "  ${BOLD}brew install espeak-ng${NC}"
      ;;
    *)
      echo "  Descarga desde: https://github.com/espeak-ng/espeak-ng/releases"
      ;;
  esac
  echo ""
fi

# ── CMU Dict (NLTK) ──────────────────────────────────────────────────────────
if echo "$EXTRAS" | grep -q "cmudict"; then
  header "5. Descargando CMU Dict (NLTK)"
  "$PYTHON_BIN" -c "import nltk; nltk.download('cmudict', quiet=False)" \
    && ok "CMU Dict descargado" \
    || warn "No se pudo descargar CMU Dict (ejecuta: python -c \"import nltk; nltk.download('cmudict')\")"
fi

# ── Configuración local ───────────────────────────────────────────────────────
header "6. Configuración"

LOCAL_YAML="$REPO_ROOT/configs/local.yaml"
EXAMPLE_YAML="$REPO_ROOT/configs/local.example.yaml"

if [ -f "$LOCAL_YAML" ]; then
  ok "configs/local.yaml ya existe (no se sobreescribe)"
elif [ -f "$EXAMPLE_YAML" ]; then
  cp "$EXAMPLE_YAML" "$LOCAL_YAML"
  ok "Copiado configs/local.example.yaml → configs/local.yaml"
  info "Edita configs/local.yaml para ajustar tu configuración"
else
  warn "configs/local.example.yaml no encontrado"
fi

# ── Resumen final ─────────────────────────────────────────────────────────────
header "Instalación completada"
echo ""
echo -e "${BOLD}Iniciar el servidor:${NC}"
echo ""
if [ "$SKIP_VENV" = false ]; then
  echo "  source .venv/bin/activate"
fi
echo "  # Modo desarrollo (sin modelos):"
echo "  PRONUNCIAPA_ASR=stub PRONUNCIAPA_TEXTREF=grapheme \\"
echo "    uvicorn ipa_server.main:get_app --reload --port 8000"
echo ""
echo "  # Modo con Allosaurus + eSpeak:"
echo "  uvicorn ipa_server.main:get_app --reload --port 8000"
echo ""
echo -e "${BOLD}Frontend React:${NC}"
echo "  cd frontend && npm install && npm run dev"
echo ""
echo -e "${BOLD}Más información:${NC} BENCHMARK.md, configs/local.example.yaml"
echo ""
