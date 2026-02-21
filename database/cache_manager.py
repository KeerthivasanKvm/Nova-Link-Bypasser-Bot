"""
Cache Manager
=============
In-memory cache for frequently accessed data.
"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from functools import wraps

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL"""
    value: Any
    expiry: float
    access_count: int = 0


class CacheManager:
    """
    In-memory cache manager with TTL support.
    Reduces Firebase reads for frequently accessed data.
    """
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache manager.
        
        Args:
            default_ttl: Default TTL in seconds (5 minutes)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        
        # Start cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start cache cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("🗄️ Cache manager started")
    
    async def stop(self) -> None:
        """Stop cache cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("🗄️ Cache manager stopped")
    
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of expired entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    async def _cleanup_expired(self) -> None:
        """Remove expired entries"""
        async with self._lock:
            now = time.time()
            expired = [
                key for key, entry in self._cache.items()
                if entry.expiry < now
            ]
            for key in expired:
                del self._cache[key]
            
            if expired:
                logger.debug(f"Cleaned up {len(expired)} expired cache entries")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry:
                if entry.expiry > time.time():
                    entry.access_count += 1
                    self._hits += 1
                    return entry.value
                else:
                    # Expired
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
        """
        ttl = ttl or self._default_ttl
        expiry = time.time() + ttl
        
        async with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                expiry=expiry
            )
    
    async def delete(self, key: str) -> bool:
        """
        Delete entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get from cache or set using factory function.
        
        Args:
            key: Cache key
            factory: Function to create value if not in cache
            ttl: TTL in seconds
            
        Returns:
            Cached or newly created value
        """
        # Try to get from cache
        value = await self.get(key)
        if value is not None:
            return value
        
        # Create new value
        value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
        
        # Store in cache
        await self.set(key, value, ttl)
        
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            'entries': len(self._cache),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.1f}%"
        }
    
    async def invalidate_user(self, user_id: int) -> None:
        """
        Invalidate all cache entries for a user.
        
        Args:
            user_id: User ID to invalidate
        """
        async with self._lock:
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(f"user:{user_id}")
            ]
            for key in keys_to_delete:
                del self._cache[key]
            
            if keys_to_delete:
                logger.debug(f"Invalidated {len(keys_to_delete)} cache entries for user {user_id}")


# Global cache instance
_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get or create cache manager instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Cache TTL in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            result = await cache.get(cache_key)
            if result is not None:
                return result
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache (sync version)
            # Note: This won't work with async cache, use async version
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
