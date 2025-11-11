"""Esqueleto de CLI.

Estado: Implementación pendiente (contratos del comando definidos).

TODO
----
- Validar existencia y formato básico del audio antes de invocar el `Kernel`.
- Combinar configuración de archivo (`--config`) con banderas siguiendo una
  precedencia clara y documentada.
- Producir salida `CompareResult` como JSON cuando se pida `--json`; en caso
  contrario, mostrar una tabla simple en consola.
"""
from __future__ import annotations

from typing import Optional

from ipa_core.config.loader import load_config
from ipa_core.kernel.core import Kernel, create_kernel
from ipa_core.types import CompareResult


def cli_compare(
    audio: str,
    text: str,
    *,
    lang: Optional[str] = None,
    config_path: Optional[str] = None,
    backend_name: Optional[str] = None,
    textref_name: Optional[str] = None,
    comparator_name: Optional[str] = None,
) -> CompareResult:
    """Contrato del comando `compare`.

    Implementación pendiente: validación de archivos y ejecución del kernel.
    """
    # Ejemplo de wiring esperado (sin implementar):
    # cfg = load_config(config_path or "config/ipa_kernel.yaml")
    # k = create_kernel(cfg)
    # return k.run(audio={"path": audio, "sample_rate": 0, "channels": 0}, text=text, lang=lang)
    raise NotImplementedError("CLI compare sin implementar (contrato únicamente)")


def cli_transcribe(
    audio: str,
    *,
    lang: Optional[str] = None,
    config_path: Optional[str] = None,
    backend_name: Optional[str] = None,
    textref_name: Optional[str] = None,
) -> list[str]:
    """Contrato del comando `transcribe`.

    Implementación pendiente: validación de archivo, carga de config y ejecución del pipeline.
    """
    raise NotImplementedError("CLI transcribe sin implementar (contrato únicamente)")
