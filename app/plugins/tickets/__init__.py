from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('tickets', bp, 'ticket_system', url_prefix='/tickets'))
from .history_routes import bp as history_bp
plugin_manager.register(Plugin('ticket_history', history_bp, 'ticket_system', url_prefix='/api/tickets'))
