from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('mobile', bp, 'mobile', url_prefix='/mobile'))
