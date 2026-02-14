from .routes import bp
from app.core.plugins import Plugin, plugin_manager, MenuItem

plugin_manager.register(Plugin('jobs', bp, 'job_board', url_prefix='/jobs', menu_items=[
    MenuItem('Jobbörse', 'jobs.job_list', 'fas fa-briefcase', order=70, group='Allgemein', feature_name='job_board')
]))
