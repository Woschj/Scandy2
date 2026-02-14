from .routes import bp
from app.core.plugins import Plugin, plugin_manager, MenuItem

plugin_manager.register(Plugin('canteen', bp, 'canteen_plan', url_prefix='/canteen', menu_items=[
    MenuItem('Kantinenplan', 'canteen.index', 'fas fa-utensils', order=80, group='Allgemein', feature_name='canteen_plan')
]))
