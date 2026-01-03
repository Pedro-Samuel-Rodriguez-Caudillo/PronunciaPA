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

class MetricsCalculator:
    """Calcula métricas agregadas (PER, RTF) a partir de resultados individuales."""

    def calculate_summary(self, results: List[dict[str, Any]]) -> dict[str, float]:
        """Calcula promedios y extremos de PER y RTF.
        
        Parámetros
        ----------
        results : List[dict]
            Lista de diccionarios con 'per', 'proc_time' y 'audio_duration'.
            
        Retorna
        -------
        dict[str, float]
            Resumen con avg_per, min_per, max_per y avg_rtf.
        """
        if not results:
            return {"avg_per": 0.0, "min_per": 0.0, "max_per": 0.0, "avg_rtf": 0.0}

        pers = [r["per"] for r in results if "per" in r]
        
        rtfs = []
        for r in results:
            proc = r.get("proc_time")
            dur = r.get("audio_duration")
            if proc is not None and dur and dur > 0:
                rtfs.append(proc / dur)

        return {
            "avg_per": sum(pers) / len(pers) if pers else 0.0,
            "min_per": min(pers) if pers else 0.0,
            "max_per": max(pers) if pers else 0.0,
            "avg_rtf": sum(rtfs) / len(rtfs) if rtfs else 0.0
        }

__all__ = ["DatasetLoader", "MetricsCalculator"]
