"""
Middleware module for Flask application.

Handles request processing, performance monitoring, and cross-cutting concerns.
"""

import logging
from flask import Flask, request, g, session, current_app, flash
from datetime import datetime
from flask_login import current_user

logger = logging.getLogger(__name__)


def init_middleware(app):
    """
    Initialize middleware components.

    Args:
        app: Flask application instance
    """
    # Request performance monitoring
    setup_performance_monitoring(app)

    # Department loading
    setup_department_loading(app)

    # Debug session monitoring
    setup_debug_monitoring(app)

    logger.info("Middleware components initialized")


def setup_performance_monitoring(app):
    """
    Set up request performance monitoring.

    Args:
        app: Flask application instance
    """
    from app.utils.performance_optimizer import monitor_request_performance, get_request_performance_summary

    @app.before_request
    def start_performance_monitoring():
        """Start performance monitoring for each request"""
        monitor_request_performance()

    @app.after_request
    def log_performance_summary(response):
        """Log performance summary after each request"""
        try:
            summary = get_request_performance_summary()
            if summary.get('total_request_time', 0) > 1.0:  # Only log slow requests
                logging.info(f"Request Performance: {summary}")
        except Exception as e:
            logging.debug(f"Error logging performance: {e}")
        return response


def setup_department_loading(app):
    """
    Set up department loading middleware.

    Args:
        app: Flask application instance
    """
    from app.core.security import load_current_department

    @app.before_request
    def load_department():
        """Load current department into request context"""
        load_current_department()


def setup_debug_monitoring(app):
    """
    Set up debug monitoring for development.

    Args:
        app: Flask application instance
    """
    @app.after_request
    def debug_session_after_request(response):
        """Debug: Show session status after each request"""
        if request.endpoint == 'auth.login' and response.status_code == 302:
            app.logger.info(f"DEBUG: After login - Session: {dict(session)}")
            app.logger.info(f"DEBUG: Response Headers: {dict(response.headers)}")

            # Check session cookies
            if 'Set-Cookie' in response.headers:
                app.logger.info(f"DEBUG: Session cookies set: {response.headers['Set-Cookie']}")
            else:
                app.logger.warning("DEBUG: No session cookies set!")

        return response


def setup_health_check(app):
    """
    Set up health check endpoint.

    Args:
        app: Flask application instance
    """
    @app.route('/health')
    def health_check():
        """
        Health check for Docker container and monitoring.

        Checks:
        - Database connection (MongoDB ping)
        - Application status

        Returns:
            JSON with status information
        """
        try:
            from app.models.mongodb_database import MongoDBDatabase
            mongodb = MongoDBDatabase()
            # Check database connection by simple query
            mongodb._client.admin.command('ping')
            return {
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now().isoformat()
            }, 200
        except Exception as e:
            app.logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, 503


def setup_system_initialization(app):
    """
    Set up system initialization tasks.

    Args:
        app: Flask application instance
    """
    # Ensure default role permissions
    try:
        from app.utils.permissions import ensure_default_role_permissions
        with app.app_context():
            ensure_default_role_permissions()
    except Exception as e:
        logging.warning(f"Could not ensure default role permissions: {e}")

    # Start automatic backup system
    try:
        from app.utils.auto_backup import start_auto_backup
        with app.app_context():
            start_auto_backup()
            logging.info("Automatic backup system started")
    except Exception as e:
        logging.error(f"Error starting automatic backup system: {e}")

    # Perform comprehensive dashboard repair on startup
    try:
        from app.services.admin_debug_service import AdminDebugService
        with app.app_context():
            fixes = AdminDebugService.fix_dashboard_comprehensive()
            if fixes.get('total', 0) > 0:
                logging.info(f"Automatic dashboard repair on startup: {fixes}")
            else:
                logging.info("Dashboard repair on startup: No issues found")
    except Exception as e:
        logging.error(f"Error during automatic dashboard repair on startup: {e}")

    # Optimize database indexes
    try:
        from app.utils.performance_optimizer import IndexOptimizer
        with app.app_context():
            IndexOptimizer.ensure_indexes()
            logging.info("Database indexes optimized")
    except Exception as e:
        logging.warning(f"Error optimizing indexes: {e}")
