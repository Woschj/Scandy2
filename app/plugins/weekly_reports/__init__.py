from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('weekly_reports', bp, 'weekly_reports'))
