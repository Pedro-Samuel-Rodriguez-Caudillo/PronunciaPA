"""Esqueleto de CLI.

Estado: Implementación pendiente (contratos del comando definidos).

TODO (Issue #18)
----------------
- Validar existencia/formato de audio antes de orquestar el `Kernel`.
- Resolver configuración combinando `--config` con banderas (precedencia).
- Definir salida de contrato (`CompareResult`) o tabla según `--json`.
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
