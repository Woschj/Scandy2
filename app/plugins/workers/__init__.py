from .routes import bp
from app.core.plugins import Plugin, plugin_manager, MenuItem

plugin_manager.register(Plugin('workers', bp, 'workers', url_prefix='/workers', menu_items=[
    MenuItem('Mitarbeiter', 'workers.index', 'fas fa-users', order=40, group='Personal', feature_name='workers'),
    MenuItem('Wochenberichte', 'workers.timesheet_list', 'fas fa-clock', order=45, group='Personal', feature_name='weekly_reports', badge_count_key='unfilled_timesheet_days')
]))
