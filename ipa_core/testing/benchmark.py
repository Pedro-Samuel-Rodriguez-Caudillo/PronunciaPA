"""Utilidades para la ejecución de benchmarks y medición de calidad."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, List

class DatasetLoader:
    """Carga conjuntos de datos de prueba desde archivos de manifiesto."""

    def load_manifest(self, path: Path) -> List[dict[str, Any]]:
        """Carga un archivo JSONL donde cada línea es un ejemplo de prueba.
        
        Parámetros
        ----------
        path : Path
            Ruta al archivo .jsonl
            
        Retorna
        -------
        List[dict]
            Lista de diccionarios con la información de cada muestra.
            
        Lanza
        -----
        FileNotFoundError
            Si el archivo no existe.
        ValueError
            Si hay errores de formato JSON.
        """
        if not path.exists():
            raise FileNotFoundError(f"Manifiesto no encontrado: {path}")
            
        samples = []
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    samples.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"Error parsing manifest at line {i}: {e}") from e
                    
        return samples

__all__ = ["DatasetLoader"]
