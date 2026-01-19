"""Sistema de cache para TextRef providers.

Evita recalcular transcripciones texto→IPA para textos repetidos,
mejorando el rendimiento del sistema.
"""
from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

from ipa_core.types import TextRefResult


T = TypeVar("T")


@dataclass
class CacheEntry:
    """Entrada individual del cache.
    
    Atributos
    ---------
    result : TextRefResult
        Resultado cacheado.
    created_at : float
        Timestamp de creación.
    hits : int
        Número de veces que se ha accedido.
    """
    result: TextRefResult
    created_at: float = field(default_factory=time.time)
    hits: int = 0
    
    def access(self) -> TextRefResult:
        """Registrar un acceso y retornar el resultado."""
        self.hits += 1
        return self.result


@dataclass
class CacheStats:
    """Estadísticas del cache.
    
    Atributos
    ---------
    hits : int
        Número de cache hits.
    misses : int
        Número de cache misses.
    size : int
        Número de entradas actuales.
    max_size : int
        Capacidad máxima.
    """
    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Tasa de aciertos como porcentaje."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": self.size,
            "max_size": self.max_size,
            "hit_rate": round(self.hit_rate, 4),
        }


class TextRefCache:
    """Cache LRU in-memory para resultados de TextRef.
    
    Parámetros
    ----------
    max_size : int
        Número máximo de entradas en el cache.
    ttl_seconds : float | None
        Tiempo de vida de las entradas en segundos.
        Si es None, las entradas no expiran.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats(max_size=max_size)
    
    @staticmethod
    def _make_key(text: str, lang: str, provider: str) -> str:
        """Generar clave única para una entrada.
        
        Usa SHA256 truncado para mantener claves cortas.
        """
        raw = f"{provider}:{lang}:{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Verificar si una entrada ha expirado."""
        if self._ttl is None:
            return False
        age = time.time() - entry.created_at
        return age > self._ttl
    
    def _evict_oldest(self) -> None:
        """Eliminar la entrada más antigua (LRU)."""
        if self._cache:
            self._cache.popitem(last=False)
            self._stats.size -= 1
    
    def get(
        self,
        text: str,
        lang: str,
        provider: str,
    ) -> Optional[TextRefResult]:
        """Obtener resultado del cache si existe.
        
        Parámetros
        ----------
        text : str
            Texto original.
        lang : str
            Código de idioma.
        provider : str
            Nombre del provider.
            
        Retorna
        -------
        TextRefResult | None
            Resultado cacheado o None si no existe/expiró.
        """
        key = self._make_key(text, lang, provider)
        entry = self._cache.get(key)
        
        if entry is None:
            self._stats.misses += 1
            return None
        
        if self._is_expired(entry):
            del self._cache[key]
            self._stats.size -= 1
            self._stats.misses += 1
            return None
        
        # Mover al final (más reciente) para LRU
        self._cache.move_to_end(key)
        self._stats.hits += 1
        return entry.access()
    
    def set(
        self,
        text: str,
        lang: str,
        provider: str,
        result: TextRefResult,
    ) -> None:
        """Almacenar resultado en el cache.
        
        Parámetros
        ----------
        text : str
            Texto original.
        lang : str
            Código de idioma.
        provider : str
            Nombre del provider.
        result : TextRefResult
            Resultado a cachear.
        """
        key = self._make_key(text, lang, provider)
        
        # Si ya existe, actualizar y mover al final
        if key in self._cache:
            self._cache[key] = CacheEntry(result=result)
            self._cache.move_to_end(key)
            return
        
        # Evictar si estamos al límite
        while len(self._cache) >= self._max_size:
            self._evict_oldest()
        
        self._cache[key] = CacheEntry(result=result)
        self._stats.size += 1
    
    async def get_or_compute(
        self,
        text: str,
        lang: str,
        provider: str,
        compute_fn: Callable[[], Awaitable[TextRefResult]],
    ) -> TextRefResult:
        """Obtener del cache o computar y cachear.
        
        Parámetros
        ----------
        text : str
            Texto a procesar.
        lang : str
            Código de idioma.
        provider : str
            Nombre del provider.
        compute_fn : Callable
            Función async que computa el resultado si no está en cache.
            
        Retorna
        -------
        TextRefResult
            Resultado (del cache o recién computado).
        """
        cached = self.get(text, lang, provider)
        if cached is not None:
            return cached
        
        # Computar y cachear
        result = await compute_fn()
        self.set(text, lang, provider, result)
        return result
    
    def invalidate(
        self,
        text: str,
        lang: str,
        provider: str,
    ) -> bool:
        """Invalidar una entrada específica.
        
        Retorna
        -------
        bool
            True si la entrada existía y fue eliminada.
        """
        key = self._make_key(text, lang, provider)
        if key in self._cache:
            del self._cache[key]
            self._stats.size -= 1
            return True
        return False
    
    def clear(self) -> int:
        """Limpiar todo el cache.
        
        Retorna
        -------
        int
            Número de entradas eliminadas.
        """
        count = len(self._cache)
        self._cache.clear()
        self._stats.size = 0
        return count
    
    def get_stats(self) -> CacheStats:
        """Obtener estadísticas del cache."""
        self._stats.size = len(self._cache)
        return self._stats
    
    def __len__(self) -> int:
        """Número de entradas en el cache."""
        return len(self._cache)
    
    def __contains__(self, key: tuple[str, str, str]) -> bool:
        """Verificar si una entrada existe."""
        text, lang, provider = key
        cache_key = self._make_key(text, lang, provider)
        return cache_key in self._cache


# Instancia global del cache (singleton)
_global_cache: Optional[TextRefCache] = None


def get_global_cache(
    max_size: int = 1000,
    ttl_seconds: Optional[float] = None,
) -> TextRefCache:
    """Obtener o crear el cache global.
    
    Parámetros
    ----------
    max_size : int
        Tamaño máximo (solo usado en la primera llamada).
    ttl_seconds : float | None
        TTL (solo usado en la primera llamada).
        
    Retorna
    -------
    TextRefCache
        Instancia global del cache.
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = TextRefCache(max_size=max_size, ttl_seconds=ttl_seconds)
    return _global_cache


def reset_global_cache() -> None:
    """Resetear el cache global (útil para tests)."""
    global _global_cache
    _global_cache = None


__all__ = [
    "CacheEntry",
    "CacheStats",
    "TextRefCache",
    "get_global_cache",
    "reset_global_cache",
]
