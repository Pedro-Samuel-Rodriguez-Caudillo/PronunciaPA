"""Proveedor compartido del kernel HTTP.

Centraliza el cache singleton para que los routers no dependan entre si.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ipa_core.config import loader
from ipa_core.kernel.core import Kernel, create_kernel

logger = logging.getLogger("ipa_server")

_cached_kernel: Optional[Kernel] = None
_kernel_ready = False
_kernel_lock: Optional[asyncio.Lock] = None


def _get_kernel_lock() -> asyncio.Lock:
    """Lazy-init del lock dentro del event loop activo."""
    global _kernel_lock
    if _kernel_lock is None:
        _kernel_lock = asyncio.Lock()
    return _kernel_lock


async def get_or_create_kernel() -> Kernel:
    """Retorna un kernel caliente reutilizable para endpoints HTTP."""
    global _cached_kernel, _kernel_ready
    if _cached_kernel is not None and _kernel_ready:
        return _cached_kernel
    async with _get_kernel_lock():
        if _cached_kernel is not None and _kernel_ready:
            return _cached_kernel
        cfg = loader.load_config()
        _cached_kernel = create_kernel(cfg)
        await _cached_kernel.setup()
        _kernel_ready = True
        logger.info("Kernel singleton created and ready")
        return _cached_kernel


def get_kernel() -> Kernel:
    """Crea un kernel no cacheado para dependencias request-scoped."""
    cfg = loader.load_config()
    return create_kernel(cfg)


async def teardown_kernel_singleton() -> None:
    """Libera el kernel cacheado durante el apagado de la app."""
    global _cached_kernel, _kernel_ready
    if _cached_kernel is not None:
        try:
            await _cached_kernel.teardown()
            logger.info("Kernel singleton torn down")
        except Exception as exc:  # pragma: no cover
            logger.warning("Error tearing down kernel singleton: %s", exc)
        finally:
            _cached_kernel = None
            _kernel_ready = False


def peek_kernel() -> Optional[Kernel]:
    """Retorna el kernel cacheado si ya está listo, sin forzar inicialización."""
    if _cached_kernel is not None and _kernel_ready:
        return _cached_kernel
    return None