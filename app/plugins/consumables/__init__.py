from .routes import bp
from app.core.plugins import Plugin, plugin_manager, MenuItem

plugin_manager.register(Plugin('consumables', bp, 'consumables', url_prefix='/consumables', menu_items=[
    MenuItem('consumables', 'consumables.index', 'fas fa-box-open', order=30, group='Inventar', feature_name='consumables', label_is_key=True)
]))
