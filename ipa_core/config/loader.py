"""Carga/validación de configuración.

Este módulo carga la configuración desde un archivo YAML y permite
sobrescribir valores mediante variables de entorno con el prefijo
PRONUNCIAPA_.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import yaml
from pydantic import ValidationError
from ipa_core.config.schema import AppConfig


def format_validation_error(exc: ValidationError) -> str:
    """Transforma un ValidationError de Pydantic en un mensaje amigable.

    Parámetros
    ----------
    exc : ValidationError
        La excepción capturada.

    Retorna
    -------
    str
        Resumen formateado de los errores.
    """
    lines = ["Error en la configuración:"]
    for error in exc.errors():
        # loc suele ser una tupla ('seccion', 'campo')
        loc = " -> ".join(str(p) for p in error["loc"])
        msg = error["msg"]
        lines.append(f"  - [{loc}]: {msg}")
    return "\n".join(lines)


def load_config(path: str | None = None) -> AppConfig:

    """Carga YAML desde un path o busca en rutas por defecto.

    Prioridad:
    1. `path` (explícito)
    2. Variable de entorno `PRONUNCIAPA_CONFIG`
    3. `./config.yaml`
    4. `./configs/local.yaml`
    5. Valores por defecto (si no hay archivos)

    Parámetros
    ----------
    path : str, opcional
        Ruta al archivo YAML.

    Retorna
    -------
    AppConfig
        Configuración validada.
    """
    p: Path | None = None

    # 1. Path explícito
    if path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {path}")
    else:
        # 2. Variable de entorno
        env_path = os.environ.get("PRONUNCIAPA_CONFIG")
        if env_path:
            p = Path(env_path)
            if not p.exists():
                # Si se especifica por entorno y no existe, fallamos
                raise FileNotFoundError(f"Archivo PRONUNCIAPA_CONFIG no encontrado: {env_path}")
        else:
            # 3 & 4. Candidatos locales
            for candidate in ["config.yaml", "configs/local.yaml"]:
                cp = Path(candidate)
                if cp.exists():
                    p = cp
                    break

    # Cargar datos
    data: dict[str, Any] = {}
    if p:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    # Aplicar sobrescrituras de variables de entorno (Simplificado)
    # PRONUNCIAPA_BACKEND_NAME -> data['backend']['name']
    for env_var, value in os.environ.items():
        if env_var.startswith("PRONUNCIAPA_") and env_var != "PRONUNCIAPA_CONFIG":
            parts = env_var[len("PRONUNCIAPA_") :].lower().split("_")
            # Manejo básico: SECTION_KEY o SECTION_SUB_KEY
            if len(parts) >= 2:
                section = parts[0]
                key = parts[-1]
                target = data
                # Navegar por secciones
                for part in parts[:-1]:
                    if part not in target or not isinstance(target[part], dict):
                        target[part] = {}
                    target = target[part]
                target[key] = value

    return AppConfig(**data)