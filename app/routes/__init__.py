# app/routes/__init__.py
from flask import Flask
from app.routes.auth import bp as auth_bp
from app.routes.api import bp as api_bp
from app.routes.admin import bp as admin_bp
from app.routes.main import bp as main_bp
from app.routes.dashboard import bp as dashboard_bp
from app.routes.setup import bp as setup_bp
from app.core.plugins import plugin_manager, MenuItem

# Import plugins to register them
import app.plugins.tools
import app.plugins.consumables
import app.plugins.workers
import app.plugins.lending
import app.plugins.tickets
import app.plugins.canteen
import app.plugins.jobs
import app.plugins.media
import app.plugins.mobile
import app.plugins.quick_scan
import app.plugins.history
import app.plugins.backup
import app.plugins.email_templates

def init_app(app):
    """Registriert alle Blueprints mit ihren URL-Präfixen"""
    # Core Blueprints
    app.register_blueprint(main_bp)  # Kein Präfix für main
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(setup_bp)

    # Register Core Menu Items
    plugin_manager.register_menu_item(MenuItem('Dashboard', 'dashboard.index', 'fas fa-th-large', order=10, group='Übersicht'))
    plugin_manager.register_menu_item(MenuItem('Über Scandy', 'main.about', 'fas fa-info-circle', order=100, group='Allgemein'))

    # Register Plugins
    plugin_manager.init_app(app)

__all__ = [
    'auth_bp', 'api_bp', 'admin_bp', 'main_bp', 'dashboard_bp', 'setup_bp'
]
