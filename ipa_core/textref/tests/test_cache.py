"""Tests para el sistema de cache de TextRef."""
from __future__ import annotations

import asyncio
import time
import pytest

from ipa_core.textref.cache import (
    CacheEntry,
    CacheStats,
    TextRefCache,
    get_global_cache,
    reset_global_cache,
)
from ipa_core.types import TextRefResult


class TestCacheEntry:
    """Tests para CacheEntry."""
    
    def test_creation(self) -> None:
        """Verifica creación de entrada."""
        result: TextRefResult = {"tokens": ["a", "b"], "meta": {}}
        entry = CacheEntry(result=result)
        assert entry.result == result
        assert entry.hits == 0
    
    def test_access_increments_hits(self) -> None:
        """Verifica que access incrementa hits."""
        result: TextRefResult = {"tokens": ["a"], "meta": {}}
        entry = CacheEntry(result=result)
        entry.access()
        entry.access()
        assert entry.hits == 2


class TestCacheStats:
    """Tests para CacheStats."""
    
    def test_hit_rate_zero(self) -> None:
        """Hit rate es 0 sin accesos."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0
    
    def test_hit_rate_calculation(self) -> None:
        """Hit rate se calcula correctamente."""
        stats = CacheStats(hits=75, misses=25)
        assert stats.hit_rate == 0.75
    
    def test_to_dict(self) -> None:
        """Conversión a diccionario."""
        stats = CacheStats(hits=10, misses=5, size=15, max_size=100)
        d = stats.to_dict()
        assert d["hits"] == 10
        assert d["misses"] == 5
        assert "hit_rate" in d


class TestTextRefCache:
    """Tests para TextRefCache."""
    
    @pytest.fixture
    def cache(self) -> TextRefCache:
        """Cache con configuración por defecto."""
        return TextRefCache(max_size=10)
    
    def test_set_and_get(self, cache: TextRefCache) -> None:
        """Set y get funcionan correctamente."""
        result: TextRefResult = {"tokens": ["h", "e", "l", "l", "o"], "meta": {}}
        cache.set("hello", "en", "espeak", result)
        
        retrieved = cache.get("hello", "en", "espeak")
        assert retrieved is not None
        assert retrieved["tokens"] == ["h", "e", "l", "l", "o"]
    
    def test_get_missing(self, cache: TextRefCache) -> None:
        """Get retorna None si no existe."""
        result = cache.get("nonexistent", "en", "espeak")
        assert result is None
    
    def test_lru_eviction(self) -> None:
        """Evicción LRU cuando se alcanza max_size."""
        cache = TextRefCache(max_size=3)
        
        for i in range(5):
            cache.set(f"text{i}", "en", "test", {"tokens": [str(i)], "meta": {}})
        
        # Solo deben quedar las 3 más recientes
        assert len(cache) == 3
        assert cache.get("text0", "en", "test") is None
        assert cache.get("text1", "en", "test") is None
        assert cache.get("text4", "en", "test") is not None
    
    def test_ttl_expiration(self) -> None:
        """Entradas expiran después del TTL."""
        cache = TextRefCache(max_size=10, ttl_seconds=0.1)
        cache.set("hello", "en", "test", {"tokens": ["h"], "meta": {}})
        
        # Inmediatamente debe existir
        assert cache.get("hello", "en", "test") is not None
        
        # Después del TTL debe expirar
        time.sleep(0.15)
        assert cache.get("hello", "en", "test") is None
    
    def test_invalidate(self, cache: TextRefCache) -> None:
        """Invalidación de entrada específica."""
        cache.set("hello", "en", "test", {"tokens": ["h"], "meta": {}})
        assert cache.invalidate("hello", "en", "test") is True
        assert cache.get("hello", "en", "test") is None
        assert cache.invalidate("hello", "en", "test") is False
    
    def test_clear(self, cache: TextRefCache) -> None:
        """Limpieza completa del cache."""
        for i in range(5):
            cache.set(f"text{i}", "en", "test", {"tokens": [str(i)], "meta": {}})
        
        count = cache.clear()
        assert count == 5
        assert len(cache) == 0
    
    def test_stats_tracking(self, cache: TextRefCache) -> None:
        """Estadísticas se rastrean correctamente."""
        cache.set("hello", "en", "test", {"tokens": ["h"], "meta": {}})
        cache.get("hello", "en", "test")  # Hit
        cache.get("world", "en", "test")  # Miss
        
        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
    
    @pytest.mark.asyncio
    async def test_get_or_compute_cache_hit(self, cache: TextRefCache) -> None:
        """get_or_compute retorna del cache si existe."""
        cache.set("hello", "en", "test", {"tokens": ["cached"], "meta": {}})
        
        compute_called = False
        async def compute() -> TextRefResult:
            nonlocal compute_called
            compute_called = True
            return {"tokens": ["computed"], "meta": {}}
        
        result = await cache.get_or_compute("hello", "en", "test", compute)
        assert result["tokens"] == ["cached"]
        assert compute_called is False
    
    @pytest.mark.asyncio
    async def test_get_or_compute_cache_miss(self, cache: TextRefCache) -> None:
        """get_or_compute computa y cachea si no existe."""
        async def compute() -> TextRefResult:
            return {"tokens": ["computed"], "meta": {}}
        
        result = await cache.get_or_compute("hello", "en", "test", compute)
        assert result["tokens"] == ["computed"]
        
        # Ahora debe estar en cache
        cached = cache.get("hello", "en", "test")
        assert cached is not None
        assert cached["tokens"] == ["computed"]
    
    def test_contains(self, cache: TextRefCache) -> None:
        """Operador in funciona."""
        cache.set("hello", "en", "test", {"tokens": ["h"], "meta": {}})
        assert ("hello", "en", "test") in cache
        assert ("world", "en", "test") not in cache


class TestGlobalCache:
    """Tests para el cache global."""
    
    def test_get_global_cache_singleton(self) -> None:
        """El cache global es un singleton."""
        reset_global_cache()
        cache1 = get_global_cache()
        cache2 = get_global_cache()
        assert cache1 is cache2
    
    def test_reset_global_cache(self) -> None:
        """Reset crea una nueva instancia."""
        reset_global_cache()
        cache1 = get_global_cache()
        reset_global_cache()
        cache2 = get_global_cache()
        assert cache1 is not cache2
