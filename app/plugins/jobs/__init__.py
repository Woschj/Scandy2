from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('jobs', bp, 'job_board', url_prefix='/jobs'))
