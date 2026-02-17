# app/routes/__init__.py
from flask import Flask
from app.routes.auth import bp as auth_bp
from app.routes.api import bp as api_bp
from app.routes.admin import bp as admin_bp
from app.routes.main import bp as main_bp
from app.routes.dashboard import bp as dashboard_bp
from app.routes.setup import bp as setup_bp
from app.core.plugins import plugin_manager

def init_app(app):
    """Registriert alle Blueprints mit ihren URL-Präfixen"""
    # Core Blueprints
    app.register_blueprint(main_bp)  # Kein Präfix für main
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(setup_bp)

    # Register Plugins (now uses dynamic discovery)
    plugin_manager.init_app(app)

__all__ = [
    'auth_bp', 'api_bp', 'admin_bp', 'main_bp', 'dashboard_bp', 'setup_bp'
]
