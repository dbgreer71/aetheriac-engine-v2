"""
TTL LRU Cache implementation for AE v2.

This module provides a thread-safe TTL LRU cache for caching
frequently accessed data with time-based expiration.
"""

import time
import threading
from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict


class TTLRUCache:
    """Thread-safe TTL LRU cache implementation."""

    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 300):
        """
        Initialize TTL LRU cache.

        Args:
            maxsize: Maximum number of items in cache
            ttl_seconds: Time-to-live in seconds for cached items
        """
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if not expired, None otherwise
        """
        with self.lock:
            if key not in self.cache:
                return None

            value, timestamp = self.cache[key]
            current_time = time.time()

            # Check if item has expired
            if current_time - timestamp > self.ttl_seconds:
                del self.cache[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """
        Set item in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            current_time = time.time()

            # Remove if already exists
            if key in self.cache:
                del self.cache[key]

            # Add new item
            self.cache[key] = (value, current_time)

            # Evict oldest if cache is full
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """
        Delete item from cache.

        Args:
            key: Cache key

        Returns:
            True if item was deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all items from cache."""
        with self.lock:
            self.cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self.lock:
            return len(self.cache)

    def cleanup_expired(self) -> int:
        """
        Remove expired items from cache.

        Returns:
            Number of items removed
        """
        with self.lock:
            current_time = time.time()
            expired_keys = []

            for key, (_, timestamp) in self.cache.items():
                if current_time - timestamp > self.ttl_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]

            return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            current_time = time.time()
            expired_count = 0

            for _, timestamp in self.cache.values():
                if current_time - timestamp > self.ttl_seconds:
                    expired_count += 1

            return {
                "size": len(self.cache),
                "maxsize": self.maxsize,
                "ttl_seconds": self.ttl_seconds,
                "expired_count": expired_count,
                "utilization": (
                    len(self.cache) / self.maxsize if self.maxsize > 0 else 0.0
                ),
            }


# Global cache instance
_cache: Optional[TTLRUCache] = None
_cache_lock = threading.Lock()


def get_cache() -> Optional[TTLRUCache]:
    """Get global cache instance."""
    global _cache
    return _cache


def init_cache(maxsize: int = 1000, ttl_seconds: int = 300) -> TTLRUCache:
    """
    Initialize global cache instance.

    Args:
        maxsize: Maximum number of items in cache
        ttl_seconds: Time-to-live in seconds for cached items

    Returns:
        Initialized cache instance
    """
    global _cache
    with _cache_lock:
        if _cache is None:
            _cache = TTLRUCache(maxsize=maxsize, ttl_seconds=ttl_seconds)
        return _cache


def clear_cache() -> None:
    """Clear global cache."""
    global _cache
    with _cache_lock:
        if _cache is not None:
            _cache.clear()


def cache_get(key: str) -> Optional[Any]:
    """
    Get item from global cache.

    Args:
        key: Cache key

    Returns:
        Cached value if not expired, None otherwise
    """
    cache = get_cache()
    if cache is None:
        return None
    return cache.get(key)


def cache_set(key: str, value: Any) -> None:
    """
    Set item in global cache.

    Args:
        key: Cache key
        value: Value to cache
    """
    cache = get_cache()
    if cache is not None:
        cache.set(key, value)
