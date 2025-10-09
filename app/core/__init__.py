"""
Core module for Flask application initialization.
"""

from .database import init_database_with_id_normalization
from .security import init_security, ensure_directories_exist
from .middleware import init_middleware, setup_health_check, setup_system_initialization
from .extensions import init_extensions, init_error_handling, init_context_processors

__all__ = [
    'init_database_with_id_normalization',
    'init_security',
    'ensure_directories_exist',
    'init_middleware',
    'setup_health_check',
    'setup_system_initialization',
    'init_extensions',
    'init_error_handling',
    'init_context_processors'
]
