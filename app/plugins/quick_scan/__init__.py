from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('quick_scan', bp, 'quick_scan', url_prefix='/quick_scan'))
