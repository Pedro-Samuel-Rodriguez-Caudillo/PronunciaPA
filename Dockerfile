# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    UVICORN_WORKERS=2 \
    PORT=8000

WORKDIR /app

# Opcional: habilitar dependencias de audio/ASR
ARG WITH_SPEECH=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY ipa_core /app/ipa_core
COPY config /app/config
COPY scripts /app/scripts

# Instalar dependencias del proyecto
RUN if [ "$WITH_SPEECH" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
        espeak-ng \
        ffmpeg \
        && rm -rf /var/lib/apt/lists/* \
      && pip install --no-cache-dir -e .[dev,speech]; \
    else \
      pip install --no-cache-dir -e .[dev]; \
    fi

EXPOSE 8000

CMD ["uvicorn", "ipa_server.main:get_app", "--host", "0.0.0.0", "--port", "8000"]

