from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('workers', bp, 'workers', url_prefix='/workers'))
