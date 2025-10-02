#!/usr/bin/env bash

# Bootstrap de modelos y dependencias para el backend de PronunciaPA.
# Ejecuta este script desde la raíz del repositorio para preparar un entorno local.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[PronunciaPA] Instalando dependencias de Python (incluye FastAPI y plugins)..."
python -m pip install --upgrade pip
python -m pip install -e "${ROOT_DIR}"

if ! command -v espeak-ng >/dev/null 2>&1; then
  echo "[Aviso] 'espeak-ng' no está instalado. En sistemas Debian/Ubuntu ejecute:" >&2
  echo "        sudo apt-get update && sudo apt-get install -y espeak-ng" >&2
fi

echo "[PronunciaPA] Descargando el modelo Whisper IPA desde Hugging Face (necesita conexión a Internet)..."
python - <<'PY'
from transformers import pipeline

print("[Descarga] Creando pipeline 'automatic-speech-recognition' con el modelo neurlang/ipa-whisper-base...")
pipeline("automatic-speech-recognition", model="neurlang/ipa-whisper-base", chunk_length_s=1.0)
print("[Descarga] Modelo listo en el cache local de Hugging Face.")
PY

echo "[PronunciaPA] Instalación completada."
