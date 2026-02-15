from .routes import bp
from app.core.plugins import Plugin, plugin_manager

plugin_manager.register(Plugin('email_templates', bp, 'email_templates', url_prefix='/admin/email-templates'))
