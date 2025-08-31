"""
Performance-Optimierungen für Scandy

Dieses Modul enthält Tools zur Optimierung von Datenbankabfragen,
Caching-Mechanismen und Performance-Monitoring.
"""

import time
import logging
from functools import wraps
from typing import Dict, Any, List, Optional, Callable
from flask import g
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Optimiert Datenbankabfragen"""

    @staticmethod
    def optimize_find_query(collection: str, query: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Optimiert eine MongoDB-Find-Abfrage

        Args:
            collection: Collection-Name
            query: Abfrage
            **kwargs: Zusätzliche Parameter

        Returns:
            Optimierte Abfrage-Parameter
        """
        optimized = {
            'filter': query,
            'limit': kwargs.get('limit', 100),  # Standard-Limit
            'batch_size': kwargs.get('batch_size', 50)
        }

        # Füge Projektion hinzu wenn nicht vorhanden
        if 'projection' not in kwargs and collection in ['tickets', 'tools', 'workers']:
            optimized['projection'] = QueryOptimizer.get_projection_for_collection(collection)

        # Füge Sortierung hinzu wenn nicht vorhanden
        if 'sort' not in kwargs:
            optimized['sort'] = QueryOptimizer.get_default_sort_for_collection(collection)

        return optimized

    @staticmethod
    def get_projection_for_collection(collection: str) -> Dict[str, Any]:
        """
        Gibt optimierte Projektionen für Collections zurück

        Args:
            collection: Collection-Name

        Returns:
            Projektion
        """
        projections = {
            'tickets': {
                '_id': 1, 'title': 1, 'status': 1, 'priority': 1,
                'created_by': 1, 'created_at': 1, 'updated_at': 1,
                'ticket_number': 1, 'category': 1, 'assigned_to': 1
            },
            'tools': {
                '_id': 1, 'name': 1, 'barcode': 1, 'status': 1,
                'category': 1, 'location': 1, 'created_at': 1
            },
            'workers': {
                '_id': 1, 'firstname': 1, 'lastname': 1, 'barcode': 1,
                'department': 1, 'created_at': 1
            }
        }
        return projections.get(collection, {})

    @staticmethod
    def get_default_sort_for_collection(collection: str) -> List[tuple]:
        """
        Gibt Standard-Sortierung für Collections zurück

        Args:
            collection: Collection-Name

        Returns:
            Sortierung
        """
        sorts = {
            'tickets': [('updated_at', -1)],
            'tools': [('name', 1)],
            'workers': [('lastname', 1), ('firstname', 1)],
            'lendings': [('lent_at', -1)],
            'consumable_usages': [('used_at', -1)]
        }
        return sorts.get(collection, [('_id', -1)])

    @staticmethod
    def batch_process(items: List[Any], batch_size: int = 50) -> List[List[Any]]:
        """
        Teilt eine Liste in Batches auf

        Args:
            items: Zu verarbeitende Items
            batch_size: Batch-Größe

        Returns:
            Liste von Batches
        """
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

class CacheManager:
    """Einfaches Caching-System für häufige Abfragen"""

    def __init__(self):
        self.cache = {}
        self.expiration_times = {}
        self.default_ttl = 300  # 5 Minuten

    def get(self, key: str) -> Optional[Any]:
        """
        Holt einen Wert aus dem Cache

        Args:
            key: Cache-Schlüssel

        Returns:
            Cached value oder None
        """
        if key in self.cache:
            if time.time() < self.expiration_times.get(key, 0):
                logger.debug(f"Cache hit: {key}")
                return self.cache[key]
            else:
                # Cache expired
                del self.cache[key]
                del self.expiration_times[key]

        logger.debug(f"Cache miss: {key}")
        return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """
        Speichert einen Wert im Cache

        Args:
            key: Cache-Schlüssel
            value: Zu cachender Wert
            ttl: Time-to-live in Sekunden
        """
        if ttl is None:
            ttl = self.default_ttl

        self.cache[key] = value
        self.expiration_times[key] = time.time() + ttl
        logger.debug(f"Cached: {key} (TTL: {ttl}s)")

    def clear(self, pattern: str = None) -> None:
        """
        Leert den Cache

        Args:
            pattern: Pattern zum Löschen (optional)
        """
        if pattern:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
                del self.expiration_times[key]
            logger.info(f"Cleared cache entries matching: {pattern}")
        else:
            self.cache.clear()
            self.expiration_times.clear()
            logger.info("Cleared entire cache")

# Globaler Cache-Manager
cache_manager = CacheManager()

def cached_query(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator für gecachte Datenbankabfragen

    Args:
        ttl: Cache-Dauer in Sekunden
        key_prefix: Präfix für Cache-Schlüssel
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Erstelle Cache-Schlüssel
            cache_key = f"{key_prefix}_{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"

            # Prüfe Cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Führe Funktion aus
            result = func(*args, **kwargs)

            # Cache Ergebnis
            cache_manager.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator

def optimize_db_query(func: Callable):
    """
    Decorator für optimierte Datenbankabfragen

    Args:
        func: Zu dekorierende Funktion
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        # Sammle Performance-Daten
        if not hasattr(g, 'db_queries'):
            g.db_queries = []

        query_info = {
            'function': func.__name__,
            'start_time': start_time,
            'args': len(args),
            'kwargs': len(kwargs)
        }

        try:
            result = func(*args, **kwargs)

            execution_time = time.time() - start_time
            query_info['execution_time'] = execution_time
            query_info['success'] = True

            # Logge langsame Queries
            if execution_time > 1.0:
                logger.warning(f"Slow DB query: {func.__name__} took {execution_time:.2f}s")

            # Sammle Statistiken
            g.db_queries.append(query_info)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            query_info['execution_time'] = execution_time
            query_info['success'] = False
            query_info['error'] = str(e)

            logger.error(f"DB query failed: {func.__name__} - {str(e)}")
            g.db_queries.append(query_info)

            raise

    return wrapper

class IndexOptimizer:
    """Optimiert Datenbank-Indizes"""

    @staticmethod
    def ensure_indexes():
        """
        Stellt sicher, dass wichtige Indizes existieren
        """
        indexes = [
            # Tickets
            ('tickets', [('status', 1)]),
            ('tickets', [('created_by', 1)]),
            ('tickets', [('assigned_to', 1)]),
            ('tickets', [('category', 1)]),
            ('tickets', [('updated_at', -1)]),
            ('tickets', [('department', 1), ('status', 1)]),

            # Tools
            ('tools', [('barcode', 1)]),
            ('tools', [('status', 1)]),
            ('tools', [('category', 1)]),
            ('tools', [('deleted', 1)]),

            # Workers
            ('workers', [('barcode', 1)]),
            ('workers', [('department', 1)]),
            ('workers', [('deleted', 1)]),

            # Lendings
            ('lendings', [('tool_barcode', 1)]),
            ('lendings', [('worker_barcode', 1)]),
            ('lendings', [('lent_at', -1)]),
            ('lendings', [('returned_at', 1)]),

            # Consumables
            ('consumables', [('barcode', 1)]),
            ('consumables', [('deleted', 1)]),

            # Users
            ('users', [('username', 1)]),
            ('users', [('email', 1)]),
            ('users', [('role', 1)]),
        ]

        for collection, index_spec in indexes:
            try:
                mongodb.db[collection].create_index(index_spec)
                logger.info(f"Index erstellt: {collection} - {index_spec}")
            except Exception as e:
                logger.warning(f"Fehler beim Erstellen des Index {collection}.{index_spec}: {e}")

    @staticmethod
    def analyze_query_performance():
        """
        Analysiert die Performance von Datenbankabfragen
        """
        try:
            # Sammle Query-Statistiken
            stats = mongodb.db.command("serverStatus")['opcounters']

            logger.info("Database Query Statistics:")
            logger.info(f"  Insert: {stats['insert']}")
            logger.info(f"  Query: {stats['query']}")
            logger.info(f"  Update: {stats['update']}")
            logger.info(f"  Delete: {stats['delete']}")

        except Exception as e:
            logger.error(f"Fehler beim Analysieren der Query-Performance: {e}")

class ConnectionPoolOptimizer:
    """Optimiert die MongoDB-Verbindungspools"""

    @staticmethod
    def optimize_connection_pool():
        """
        Optimiert die MongoDB-Verbindungspool-Einstellungen
        """
        try:
            # Setze optimale Verbindungspool-Parameter
            if hasattr(mongodb, '_client'):
                # Max Pool Size
                mongodb._client._topology._settings._pool_options.max_pool_size = 10

                # Min Pool Size
                mongodb._client._topology._settings._pool_options.min_pool_size = 2

                # Max Idle Time
                mongodb._client._topology._settings._pool_options.max_idle_time_seconds = 300

                logger.info("MongoDB connection pool optimized")

        except Exception as e:
            logger.warning(f"Fehler beim Optimieren des Connection Pools: {e}")

# Performance-Monitoring für Requests
def monitor_request_performance():
    """
    Überwacht die Performance eines kompletten Requests
    """
    if not hasattr(g, 'request_start_time'):
        g.request_start_time = time.time()

    if not hasattr(g, 'db_queries'):
        g.db_queries = []

def get_request_performance_summary() -> Dict[str, Any]:
    """
    Gibt eine Zusammenfassung der Request-Performance zurück

    Returns:
        Performance-Statistiken
    """
    if not hasattr(g, 'request_start_time'):
        return {}

    total_time = time.time() - g.request_start_time
    db_queries = getattr(g, 'db_queries', [])

    summary = {
        'total_request_time': total_time,
        'db_query_count': len(db_queries),
        'db_query_time': sum(q.get('execution_time', 0) for q in db_queries),
        'slow_queries': [q for q in db_queries if q.get('execution_time', 0) > 1.0],
        'failed_queries': [q for q in db_queries if not q.get('success', True)]
    }

    # Logge Performance-Probleme
    if summary['db_query_time'] > total_time * 0.8:
        logger.warning(f"Request mostly DB time: {summary['db_query_time']:.2f}s of {total_time:.2f}s")

    if summary['slow_queries']:
        logger.warning(f"Request had {len(summary['slow_queries'])} slow queries")

    return summary

# Lazy Loading für teure Operationen
def lazy_load(func: Callable):
    """
    Decorator für Lazy Loading von Daten

    Args:
        func: Zu dekorierende Funktion
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Prüfe ob bereits geladen
        cache_key = f"lazy_{func.__name__}_{hash(str(args))}"
        cached = cache_manager.get(cache_key)

        if cached is not None:
            return cached

        # Lade Daten
        result = func(*args, **kwargs)

        # Cache für kurze Zeit
        cache_manager.set(cache_key, result, ttl=60)  # 1 Minute

        return result

    return wrapper
