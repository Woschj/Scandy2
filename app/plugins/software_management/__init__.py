from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('software_management', bp, 'software_management', url_prefix='/admin'))
