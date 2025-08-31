# app/routes/__init__.py
from flask import Flask
from app.routes.auth import bp as auth_bp
from app.routes.tools import bp as tools_bp
from app.routes.workers import bp as workers_bp
from app.routes.consumables import bp as consumables_bp
from app.routes.api import bp as api_bp
from app.routes.admin import bp as admin_bp
from app.routes.quick_scan import bp as quick_scan_bp
from app.routes.history import bp as history_bp
from app.routes.main import bp as main_bp
from app.routes.dashboard import bp as dashboard_bp
from app.routes.lending import bp as lending_bp
from app.routes.tickets import bp as tickets_bp
from app.routes.setup import bp as setup_bp
from app.routes.jobs import bp as jobs_bp
from app.routes.media import bp as media_bp
from app.routes.backup_routes import bp as backup_bp
from app.routes.ticket_history_routes import bp as ticket_history_bp
from app.routes.canteen import bp as canteen_bp
from app.routes.mobile import bp as mobile_bp
from app.routes.admin_email_templates import bp as admin_email_templates_bp
from app.routes.admin_core import bp as admin_core_bp
from app.routes.admin_users import bp as admin_users_bp
from app.routes.admin_content import bp as admin_content_bp
from app.routes.admin_system import bp as admin_system_bp
from app.routes.admin_trash import bp as admin_trash_bp
from app.routes.admin_media import bp as admin_media_bp
from app.routes.admin_tickets import bp as admin_tickets_bp

def init_app(app):
    """Registriert alle Blueprints mit ihren URL-Präfixen"""
    app.register_blueprint(main_bp)  # Kein Präfix für main
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(workers_bp)
    app.register_blueprint(consumables_bp)
    app.register_blueprint(lending_bp, url_prefix='/lending')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(quick_scan_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
    app.register_blueprint(setup_bp)
    app.register_blueprint(jobs_bp, url_prefix='/jobs')
    app.register_blueprint(media_bp, url_prefix='/media')
    app.register_blueprint(backup_bp)  # Backup-Routen mit /backup Präfix
    app.register_blueprint(ticket_history_bp)  # Ticket-History API
    app.register_blueprint(canteen_bp)  # Kantinenplan-Routen
    app.register_blueprint(mobile_bp)  # Mobile Quickscan-App
    app.register_blueprint(admin_email_templates_bp)  # Admin E-Mail-Vorlagen

    # Modulare Admin-Blueprints (ersetzen die große admin.py)
    app.register_blueprint(admin_core_bp)      # Core Admin (Dashboard, etc.)
    app.register_blueprint(admin_users_bp)     # Nutzerverwaltung
    app.register_blueprint(admin_content_bp)   # Content-Management (Tools, Consumables, Workers)
    app.register_blueprint(admin_system_bp)    # Systemverwaltung
    app.register_blueprint(admin_trash_bp)     # Papierkorb
    app.register_blueprint(admin_media_bp)     # Medien-Management
    app.register_blueprint(admin_tickets_bp)   # Ticket-Management

__all__ = [
    'auth_bp', 'tools_bp', 'workers_bp', 'consumables_bp',
    'api_bp', 'admin_bp', 'quick_scan_bp', 'history_bp', 'main_bp', 'dashboard_bp', 'lending_bp', 'tickets_bp', 'setup_bp', 'jobs_bp', 'media_bp', 'backup_bp', 'ticket_history_bp', 'canteen_bp',
    'admin_email_templates_bp', 'admin_core_bp', 'admin_users_bp', 'admin_content_bp', 'admin_system_bp', 'admin_trash_bp', 'admin_media_bp', 'admin_tickets_bp'
]