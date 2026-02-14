from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('tools', bp, 'tools', url_prefix='/tools'))
