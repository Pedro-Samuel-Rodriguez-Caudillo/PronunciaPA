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
from ipa_core.config.schema import AppConfig


def load_config(path: str) -> AppConfig:
    """Carga YAML desde `path` y aplica sobrescrituras de entorno.

    Parámetros
    ----------
    path : str
        Ruta al archivo YAML.

    Retorna
    -------
    AppConfig
        Configuración validada.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Archivo de configuración no encontrado: {path}")

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Aplicar sobrescrituras de variables de entorno (simplificado)
    # Patrón: PRONUNCIAPA_OPTIONS_LANG -> data['options']['lang']
    for env_var, value in os.environ.items():
        if env_var.startswith("PRONUNCIAPA_"):
            parts = env_var[len("PRONUNCIAPA_") :].lower().split("_")
            if len(parts) == 2:
                section, key = parts
                if section in data and isinstance(data[section], dict):
                    data[section][key] = value
                elif section not in data:
                    # Si no existe la sección, la creamos para que Pydantic la valide
                    data[section] = {key: value}

    return AppConfig(**data)