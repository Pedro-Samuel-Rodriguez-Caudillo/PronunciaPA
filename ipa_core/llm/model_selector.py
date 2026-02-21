"""Selector de modelo LLM local basado en RAM disponible.

Detecta la RAM del sistema, mapea a un tier de modelo (1B / 3B / 7B) y
muestra una tabla de recomendaciones antes de pedir confirmación al usuario.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Tablas de recomendación
# ---------------------------------------------------------------------------

@dataclass
class ModelTier:
    """Descripción de un tier de modelo LLM local."""

    name: str                    # Etiqueta: "1B", "3B", "7B"
    min_ram_gb: float            # RAM mínima recomendada (GB)
    description: str
    suggested_models: list[str] = field(default_factory=list)
    piper_voice: str = "es_MX-claude-medium"
    quantization: str = "Q4_K_M"
    ctx_size: int = 2048


_TIERS: list[ModelTier] = [
    ModelTier(
        name="1B",
        min_ram_gb=2.0,
        description="Modelo ultraligero – retroalimentación básica, corre en hardware modesto.",
        suggested_models=[
            "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf",
            "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        ],
        ctx_size=2048,
    ),
    ModelTier(
        name="3B",
        min_ram_gb=4.0,
        description="Modelo balanceado – buena calidad de feedback con RAM moderada.",
        suggested_models=[
            "phi-3-mini-4k-instruct-q4.gguf",
            "gemma-2-2b-it-Q4_K_M.gguf",
        ],
        ctx_size=4096,
    ),
    ModelTier(
        name="7B",
        min_ram_gb=8.0,
        description="Modelo completo – feedback rico y ejemplos detallados.",
        suggested_models=[
            "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
            "mistral-7b-instruct-v0.3.Q4_K_M.gguf",
        ],
        ctx_size=8192,
    ),
]

# Tier de fallback cuando la RAM es muy baja
_STUB_TIER = ModelTier(
    name="stub",
    min_ram_gb=0.0,
    description="Sin modelo LLM – usa respuestas predefinidas (sin IA generativa).",
    suggested_models=[],
    ctx_size=0,
)


# ---------------------------------------------------------------------------
# Detección de RAM
# ---------------------------------------------------------------------------

def get_available_ram_gb() -> float:
    """Retornar la RAM disponible del sistema en GB.

    Usa ``psutil`` si está instalado; en caso contrario intenta leer
    ``/proc/meminfo`` en Linux, o devuelve 0.0 si no es posible.
    """
    try:
        import psutil  # type: ignore[import]
        return psutil.virtual_memory().available / (1024 ** 3)
    except ImportError:
        pass

    # Fallback: /proc/meminfo (Linux)
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    return kb / (1024 ** 2)
    except OSError:
        pass

    return 0.0


def get_total_ram_gb() -> float:
    """Retornar la RAM total del sistema en GB."""
    try:
        import psutil  # type: ignore[import]
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        pass

    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb / (1024 ** 2)
    except OSError:
        pass

    return 0.0


# ---------------------------------------------------------------------------
# Selección de tier
# ---------------------------------------------------------------------------

def select_tier(available_ram_gb: float) -> ModelTier:
    """Seleccionar el mejor tier dado la RAM disponible.

    Parámetros
    ----------
    available_ram_gb:
        RAM disponible en GB (resultado de :func:`get_available_ram_gb`).

    Retorna
    -------
    ModelTier
        Tier más exigente que cabe en la RAM disponible.
        Si no cabe ni el tier 1B, se devuelve :data:`_STUB_TIER`.
    """
    selected = _STUB_TIER
    for tier in _TIERS:
        if available_ram_gb >= tier.min_ram_gb:
            selected = tier
    return selected


# ---------------------------------------------------------------------------
# Visualización en consola
# ---------------------------------------------------------------------------

def print_tier_table(available_ram_gb: float, recommended: ModelTier) -> None:
    """Mostrar tabla de tiers en la consola con el recomendado resaltado."""
    print()
    print("=" * 70)
    print("  SELECCIÓN DE MODELO LLM LOCAL — PronunciaPA")
    print(f"  RAM disponible detectada: {available_ram_gb:.1f} GB")
    print("=" * 70)
    print(f"  {'TIER':<6}  {'MIN RAM':<9}  {'ESTADO':<12}  DESCRIPCIÓN")
    print("-" * 70)

    all_tiers = [_STUB_TIER] + _TIERS
    for tier in all_tiers:
        fits = available_ram_gb >= tier.min_ram_gb
        status = "✓ RECOM." if tier.name == recommended.name else ("✓ OK" if fits else "✗ Req.")
        min_label = f"{tier.min_ram_gb:.0f} GB" if tier.min_ram_gb > 0 else "–"
        marker = " >>>" if tier.name == recommended.name else "    "
        print(f"{marker} {tier.name:<6}  {min_label:<9}  {status:<12}  {tier.description}")

    print("=" * 70)

    if recommended.name != "stub":
        print(f"\n  Modelos sugeridos para tier {recommended.name}:")
        for m in recommended.suggested_models:
            print(f"    • {m}")
    else:
        print("\n  RAM insuficiente para modelos generativos.")
        print("  Se usará el adaptador 'stub' con respuestas predefinidas.")

    print()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def recommend_model(
    *,
    interactive: bool = False,
    ram_override_gb: Optional[float] = None,
) -> ModelTier:
    """Recomendar un tier de modelo y opcionalmente pedir confirmación.

    Parámetros
    ----------
    interactive:
        Si es ``True`` muestra la tabla y pide confirmación por stdin.
    ram_override_gb:
        Sobreescribir la detección automática de RAM (útil para tests).

    Retorna
    -------
    ModelTier
        Tier seleccionado (el recomendado o el elegido por el usuario).
    """
    available = ram_override_gb if ram_override_gb is not None else get_available_ram_gb()
    recommended = select_tier(available)

    if not interactive:
        return recommended

    print_tier_table(available, recommended)

    # Opciones disponibles
    valid = {t.name.lower(): t for t in ([_STUB_TIER] + _TIERS)}
    tier_names = list(valid.keys())

    prompt = (
        f"  Elige un tier [{'/'.join(tier_names)}] "
        f"o pulsa ENTER para aceptar '{recommended.name}': "
    )
    try:
        choice = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelado. Usando recomendación por defecto.")
        return recommended

    if not choice:
        return recommended

    if choice in valid:
        chosen = valid[choice]
        print(f"  Seleccionado: tier {chosen.name}")
        return chosen

    print(f"  Opción '{choice}' no reconocida. Usando recomendación: {recommended.name}")
    return recommended


def get_runtime_config(tier: ModelTier) -> dict:
    """Generar configuración de runtime para el tier seleccionado.

    Retorna un dict compatible con ``RuntimeSpec.params`` de :mod:`ipa_core.packs.schema`.
    """
    if tier.name == "stub":
        return {"kind": "stub", "params": {}}

    suggested = tier.suggested_models[0] if tier.suggested_models else "model.gguf"
    return {
        "kind": "llama_cpp",
        "params": {
            "model_path": f"models/{suggested}",
            "n_ctx": tier.ctx_size,
            "n_gpu_layers": 0,
            "temperature": 0.3,
            "top_p": 0.9,
        },
    }


__all__ = [
    "ModelTier",
    "get_available_ram_gb",
    "get_total_ram_gb",
    "select_tier",
    "recommend_model",
    "get_runtime_config",
    "print_tier_table",
    "_TIERS",
    "_STUB_TIER",
]
