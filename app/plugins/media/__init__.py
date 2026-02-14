from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('media', bp, 'media_management', url_prefix='/media'))
