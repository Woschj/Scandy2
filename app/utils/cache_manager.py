"""
Cache Manager für Scandy App
Implementiert einfaches In-Memory Caching für Performance-Optimierung
"""

import time
import threading
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Einfacher In-Memory Cache Manager"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CacheManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._cache: Dict[str, Dict[str, Any]] = {}
            self._initialized = True
    
    def get(self, key: str) -> Optional[Any]:
        """Holt einen Wert aus dem Cache"""
        try:
            if key in self._cache:
                cache_entry = self._cache[key]
                
                # Prüfe ob der Cache abgelaufen ist
                if time.time() < cache_entry['expires_at']:
                    return cache_entry['value']
                else:
                    # Cache abgelaufen, entferne ihn
                    del self._cache[key]
                    logger.debug(f"Cache expired for key: {key}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache value for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Setzt einen Wert im Cache mit TTL"""
        try:
            self._cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl_seconds,
                'created_at': time.time()
            }
            logger.debug(f"Cache set for key: {key} (TTL: {ttl_seconds}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache value for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Löscht einen Wert aus dem Cache"""
        try:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted for key: {key}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting cache value for key {key}: {e}")
            return False
    
    def clear(self) -> bool:
        """Löscht den gesamten Cache"""
        try:
            self._cache.clear()
            logger.info("Cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """Entfernt abgelaufene Cache-Einträge"""
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, cache_entry in self._cache.items():
                if current_time >= cache_entry['expires_at']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache entries: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Cache-Statistiken zurück"""
        try:
            current_time = time.time()
            active_entries = 0
            expired_entries = 0
            
            for cache_entry in self._cache.values():
                if current_time < cache_entry['expires_at']:
                    active_entries += 1
                else:
                    expired_entries += 1
            
            return {
                'total_entries': len(self._cache),
                'active_entries': active_entries,
                'expired_entries': expired_entries,
                'memory_usage_estimate': len(str(self._cache))
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}


# Globale Cache-Instanz
cache = CacheManager()


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator für Caching von Funktionen
    
    Args:
        ttl_seconds: Cache-TTL in Sekunden (Standard: 5 Minuten)
        key_prefix: Präfix für Cache-Keys
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Erstelle Cache-Key aus Funktionsname, Args und Kwargs
            cache_key = f"{key_prefix}{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Versuche aus Cache zu laden
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Cache miss, führe Funktion aus
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            
            # Speichere Ergebnis im Cache
            cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidiert alle Cache-Einträge die einem Pattern entsprechen
    
    Args:
        pattern: Pattern für Cache-Keys (einfache String-Übereinstimmung)
    
    Returns:
        Anzahl der invalidierten Einträge
    """
    try:
        import re
        pattern_regex = re.compile(pattern)
        invalidated_count = 0
        
        keys_to_delete = []
        for key in cache._cache.keys():
            if pattern_regex.search(key):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            cache.delete(key)
            invalidated_count += 1
        
        logger.info(f"Invalidated {invalidated_count} cache entries matching pattern: {pattern}")
        return invalidated_count
        
    except Exception as e:
        logger.error(f"Error invalidating cache pattern {pattern}: {e}")
        return 0
