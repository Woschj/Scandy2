"""
Extensions module for Flask application.

Handles Flask extensions initialization and configuration.
"""

import logging
import os
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress

logger = logging.getLogger(__name__)

# Global extension instances (lazy initialization)
limiter = None
compress = None


def get_limiter():
    """
    Get or create rate limiter instance (lazy initialization).

    Returns:
        Limiter: Flask-Limiter instance
    """
    global limiter
    if limiter is None:
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://"
        )
    return limiter


def init_extensions(app):
    """
    Initialize Flask extensions.

    Args:
        app: Flask application instance
    """
    # Initialize rate limiting
    get_limiter().init_app(app)
    logger.info("Rate limiter initialized")

    # Initialize compression
    Compress(app)
    logger.info("Compression initialized")

    # Initialize email system
    init_email_system(app)

    # Initialize session
    init_session(app)


def init_email_system(app):
    """
    Initialize email system.

    Args:
        app: Flask application instance
    """
    try:
        from app.utils.email_utils import init_mail
        init_mail(app)
        app.logger.info("Email system initialized")
    except Exception as e:
        app.logger.warning(f"Email system could not be initialized: {e}")


def init_session(app):
    """
    Initialize Flask-Session.

    Args:
        app: Flask application instance
    """
    from flask_session import Session

    # Session file permissions
    session_dir = app.config['SESSION_FILE_DIR']
    if os.path.exists(session_dir):
        try:
            # Set directory permissions
            os.chmod(session_dir, 0o755)  # rwxr-xr-x
            # Set owner to root for Gunicorn
            import pwd
            root_uid = pwd.getpwnam('root').pw_uid
            root_gid = pwd.getpwnam('root').pw_gid
            os.chown(session_dir, root_uid, root_gid)
            app.logger.info(f"Session directory permissions and owner set: {session_dir}")
        except Exception as e:
            app.logger.warning(f"Could not set session directory permissions: {e}")

    Session(app)
    logger.info("Session management initialized")


def init_error_handling(app):
    """
    Initialize error handling and logging.

    Args:
        app: Flask application instance
    """
    from app.utils.error_handler import handle_errors
    from app.utils.enhanced_error_handler import register_enhanced_error_handlers
    from app.utils.logger import init_app_logger
    from app.utils.filters import register_filters, status_color, priority_color

    # Initialize logging
    init_app_logger(app)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("\n=== APPLICATION START ===")

    # Register error handlers
    handle_errors(app)
    register_enhanced_error_handlers(app)

    # Register template filters
    register_filters(app)
    app.jinja_env.filters['status_color'] = status_color
    app.jinja_env.filters['priority_color'] = priority_color

    logger.info("Error handling and filters initialized")


def init_context_processors(app):
    """
    Initialize context processors for templates.

    Args:
        app: Flask application instance
    """
    from app.utils.context_processors import register_context_processors
    from app.utils.permissions import has_permission
    from flask import g

    register_context_processors(app)

    # System name context processor
    @app.context_processor
    def inject_system_names():
        """Inject system names into all templates"""
        return {
            'system_name': app.config['SYSTEM_NAME'],
            'ticket_system_name': app.config['TICKET_SYSTEM_NAME'],
            'tool_system_name': app.config['TOOL_SYSTEM_NAME'],
            'consumable_system_name': app.config['CONSUMABLE_SYSTEM_NAME']
        }

    # Security context processor
    @app.context_processor
    def security_processor():
        try:
            return {'csp_nonce': getattr(g, 'csp_nonce', '')}
        except Exception:
            return {'csp_nonce': ''}

    # Feature settings context processor
    @app.context_processor
    def feature_processor():
        """Inject feature settings into all templates"""
        try:
            from app.models.mongodb_database import get_feature_settings
            feature_settings = get_feature_settings()
            return {'feature_settings': feature_settings}
        except Exception as e:
            app.logger.warning(f"Error loading feature settings: {e}")
            return {'feature_settings': {}}

    # Permissions context processor
    @app.context_processor
    def permissions_processor():
        """Make has_permission available to templates"""
        try:
            return {'has_permission': has_permission}
        except Exception:
            # Fallback: return false (UI will hide buttons)
            return {'has_permission': lambda *args, **kwargs: False}

    # Status colors context processor
    @app.context_processor
    def utility_processor():
        """Inject colors for status and priorities into all templates"""
        return {
            'status_colors': {
                'offen': 'danger',
                'in_bearbeitung': 'warning',
                'wartet_auf_antwort': 'info',
                'gelöst': 'success',
                'geschlossen': 'secondary'
            },
            'priority_colors': {
                'niedrig': 'secondary',
                'normal': 'primary',
                'hoch': 'error',
                'dringend': 'error'
            }
        }

    logger.info("Context processors initialized")
