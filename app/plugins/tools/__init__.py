from .routes import bp
from app.core.plugins import Plugin, plugin_manager, MenuItem

plugin_manager.register(Plugin('tools', bp, 'tools', url_prefix='/tools', menu_items=[
    MenuItem('tools', 'tools.index', 'fas fa-tools', order=20, group='Inventar', feature_name='tools', label_is_key=True)
]))
