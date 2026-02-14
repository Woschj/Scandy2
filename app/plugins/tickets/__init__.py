from .routes import bp
from app.core.plugins import Plugin, plugin_manager, MenuItem

plugin_manager.register(Plugin('tickets', bp, 'ticket_system', url_prefix='/tickets', menu_items=[
    MenuItem('tickets', 'tickets.create', 'fas fa-ticket-alt', order=50, group='Service', feature_name='ticket_system', label_is_key=True, badge_count_key='unread_tickets_count'),
    MenuItem('Auftragserstellung', 'tickets.public_create_order', 'fas fa-file-alt', order=60, group='Service', feature_name='ticket_system')
]))

from .history_routes import bp as history_bp
plugin_manager.register(Plugin('ticket_history', history_bp, 'ticket_system', url_prefix='/api/tickets'))
