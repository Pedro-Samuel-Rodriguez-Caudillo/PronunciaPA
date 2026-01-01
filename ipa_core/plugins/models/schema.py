"""Esquema de configuración para modelos ONNX.

Define la estructura esperada para config.json en los paquetes de modelos.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class ModelConfig(BaseModel):
    """Configuración de un modelo ASR ONNX."""
    model_name: str
    input_shape: List[int]
    output_shape: List[int]
    sample_rate: int
    labels: List[str]
    architecture: Optional[str] = "unknown"

    @field_validator("sample_rate")
    @classmethod
    def check_sample_rate(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("sample_rate must be positive")
        return v
