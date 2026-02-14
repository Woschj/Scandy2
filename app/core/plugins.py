import logging
from flask import Blueprint, g, abort, redirect, url_for, flash, current_app
from functools import wraps
from app.models.feature_system import is_feature_enabled

logger = logging.getLogger(__name__)

class MenuItem:
    def __init__(self, label, endpoint, icon, order=100, group=None, required_role=None, feature_name=None, badge_count_key=None, label_is_key=False):
        self.label = label
        self.endpoint = endpoint
        self.icon = icon
        self.order = order
        self.group = group
        self.required_role = required_role
        self.feature_name = feature_name
        self.badge_count_key = badge_count_key
        self.label_is_key = label_is_key # If True, label is a key in app_labels

class Plugin:
    def __init__(self, name, blueprint, feature_name=None, url_prefix=None, menu_items=None):
        self.name = name
        self.blueprint = blueprint
        self.feature_name = feature_name or name
        self.url_prefix = url_prefix
        self.menu_items = menu_items or []

def plugin_required(feature_name):
    """Decorator to check if a feature is enabled for the current department"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_feature_enabled(feature_name):
                logger.warning(f"Zugriff auf deaktiviertes Feature verweigert: {feature_name}")
                flash(f"Das Modul '{feature_name}' ist für diese Abteilung nicht aktiviert.", "warning")
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class PluginManager:
    _plugins = {}
    _core_menu_items = []

    @classmethod
    def register(cls, plugin):
        cls._plugins[plugin.name] = plugin

        # Add a before_request hook to the blueprint to check if it's enabled
        @plugin.blueprint.before_request
        def check_enabled():
            if not is_feature_enabled(plugin.feature_name):
                logger.warning(f"Plugin {plugin.name} ist deaktiviert für dieses Department")
                # Redirect or 404
                return redirect(url_for('dashboard.index'))

    @classmethod
    def register_menu_item(cls, menu_item):
        cls._core_menu_items.append(menu_item)

    @classmethod
    def get_menu_items(cls):
        all_items = list(cls._core_menu_items)
        for plugin in cls._plugins.values():
            all_items.extend(plugin.menu_items)

        # Sort by order
        all_items.sort(key=lambda x: (x.order, x.label))
        return all_items

    @classmethod
    def get_grouped_menu_items(cls):
        items = cls.get_menu_items()
        groups = {}
        for item in items:
            group = item.group or 'Sonstiges'
            if group not in groups:
                groups[group] = []
            groups[group].append(item)

        # Define group order
        group_order = ['Übersicht', 'Inventar', 'Personal', 'Service', 'Allgemein', 'Sonstiges']

        # Sort groups based on group_order, then alphabetically for unknown groups
        sorted_groups = sorted(groups.items(), key=lambda x: (group_order.index(x[0]) if x[0] in group_order else 999, x[0]))
        return sorted_groups

    @classmethod
    def init_app(cls, app):
        for plugin in cls._plugins.values():
            if plugin.url_prefix:
                app.register_blueprint(plugin.blueprint, url_prefix=plugin.url_prefix)
            else:
                app.register_blueprint(plugin.blueprint)
            logger.info(f"Plugin registriert: {plugin.name} (Prefix: {plugin.url_prefix})")

plugin_manager = PluginManager()
