from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('backup', bp, 'backup', url_prefix='/backup'))
