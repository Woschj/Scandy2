import logging
from flask import Blueprint, g, abort, redirect, url_for, flash
from functools import wraps
from app.models.feature_system import is_feature_enabled

logger = logging.getLogger(__name__)

class Plugin:
    def __init__(self, name, blueprint, feature_name=None, url_prefix=None):
        self.name = name
        self.blueprint = blueprint
        self.feature_name = feature_name or name
        self.url_prefix = url_prefix

def plugin_required(feature_name):
    """Decorator to check if a feature is enabled for the current department"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_feature_enabled(feature_name):
                logger.warning(f"Zugriff auf deaktiviertes Feature verweigert: {feature_name}")
                flash(f"Das Modul '{feature_name}' ist für diese Abteilung nicht aktiviert.", "warning")
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class PluginManager:
    _plugins = {}

    @classmethod
    def register(cls, plugin):
        cls._plugins[plugin.name] = plugin

        # Add a before_request hook to the blueprint to check if it's enabled
        @plugin.blueprint.before_request
        def check_enabled():
            if not is_feature_enabled(plugin.feature_name):
                logger.warning(f"Plugin {plugin.name} ist deaktiviert für dieses Department")
                # Redirect or 404
                return redirect(url_for('dashboard.index'))

    @classmethod
    def init_app(cls, app):
        for plugin in cls._plugins.values():
            if plugin.url_prefix:
                app.register_blueprint(plugin.blueprint, url_prefix=plugin.url_prefix)
            else:
                app.register_blueprint(plugin.blueprint)
            logger.info(f"Plugin registriert: {plugin.name} (Prefix: {plugin.url_prefix})")

plugin_manager = PluginManager()
