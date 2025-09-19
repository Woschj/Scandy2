from flask import Blueprint, render_template, current_app, redirect, url_for, request
from flask_login import current_user
from ..utils.auth_utils import needs_setup
from ..models.mongodb_database import MongoDB, is_feature_enabled
from ..models.mongodb_models import MongoDBTool
from datetime import datetime

# Kein URL-Präfix für den Main-Blueprint
bp = Blueprint('main', __name__, url_prefix='')
mongodb = MongoDB()

@bp.route('/')
def index():
    """Zeigt die Hauptseite mit Statistiken"""
    # Prüfe ob Setup erforderlich ist
    if needs_setup():
        return redirect(url_for('setup.setup_admin'))
    
    # Für eingeloggte Teilnehmer: Keine Weiterleitung - sie können die Startseite sehen
    # if current_user.is_authenticated and current_user.role == 'teilnehmer':
    #     return redirect(url_for('workers.timesheet_list'))
        
    try:
        # Prüfe ob MongoDB verfügbar ist
        try:
            # Teste die Verbindung
            if mongodb._client is not None:
                mongodb._client.admin.command('ping')
            else:
                raise Exception("MongoDB-Verbindung nicht initialisiert")
        except Exception as db_error:
            current_app.logger.error(f"MongoDB-Verbindung nicht verfügbar: {str(db_error)}")
            # Wähle das Template basierend auf der Benutzerrolle
            if not current_user.is_authenticated:
                template_name = 'index_public.html'
            elif current_user.role == 'teilnehmer':
                template_name = 'index_teilnehmer.html'
            else:
                template_name = 'index_normal.html'
            # Bei DB-Problemen keine Timesheet-Quick-Funktion anzeigen
            timesheet_prefill = None
            timesheet_quick_enabled = False
            weekly_reports_enabled = False

            return render_template(template_name,
                               tool_stats={'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
                               consumable_stats={'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
                               worker_stats={'total': 0, 'by_department': []},
                               ticket_stats={'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0},
                               duplicate_barcodes=[],
                               overdue_loans=[],
                               notices=[],
                               timesheet_prefill=timesheet_prefill,
                               timesheet_quick_enabled=timesheet_quick_enabled,
                               weekly_reports_enabled=weekly_reports_enabled)
        
        # Verwende den zentralen Statistics Service
        try:
            from app.services.statistics_service import StatisticsService
            stats = StatisticsService.get_all_statistics()
            tool_stats = stats['tool_stats']
            consumable_stats = stats['consumable_stats']
            worker_stats = stats['worker_stats']
            ticket_stats = stats['ticket_stats']
            duplicate_barcodes = stats['duplicate_barcodes']
            overdue_loans = stats['overdue_loans']
            notices = StatisticsService.get_notices()
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der Statistiken: {str(e)}")
            import traceback
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            tool_stats = {'total': 0, 'available': 0, 'lent': 0, 'defect': 0}
            consumable_stats = {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0}
            worker_stats = {'total': 0, 'by_department': []}
            ticket_stats = {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}
            duplicate_barcodes = []
            overdue_loans = []
            notices = []
        
        # Optional: Prefill für heutige Timesheet-Eingabe ermitteln
        timesheet_prefill = None
        weekly_reports_enabled = False
        timesheet_quick_enabled = False
        try:
            weekly_reports_enabled = is_feature_enabled('weekly_reports')
            if current_user.is_authenticated and getattr(current_user, 'timesheet_enabled', False) and weekly_reports_enabled:
                today = datetime.now()
                current_year = today.isocalendar()[0]
                current_week = today.isocalendar()[1]
                weekday = today.weekday()  # 0=Montag
                days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
                if weekday > 4:
                    weekday = 4
                day_key = days[weekday]
                ts = mongodb.find_one('timesheets', {
                    'user_id': getattr(current_user, 'username', None),
                    'year': current_year,
                    'kw': current_week
                })
                if ts:
                    timesheet_prefill = {
                        'start': ts.get(f'{day_key}_start', ''),
                        'end': ts.get(f'{day_key}_end', ''),
                        'tasks': ts.get(f'{day_key}_tasks', '')
                    }
                else:
                    timesheet_prefill = {'start': '', 'end': '', 'tasks': ''}
                timesheet_quick_enabled = True
        except Exception as _ts_err:
            current_app.logger.warning(f"Timesheet Prefill nicht verfügbar: {_ts_err}")

        # Wähle das Template basierend auf der Benutzerrolle
        if not current_user.is_authenticated:
            template_name = 'index_public.html'
        elif current_user.role == 'teilnehmer':
            template_name = 'index_teilnehmer.html'
        else:
            template_name = 'index_normal.html'
        
        return render_template(template_name,
                           tool_stats=tool_stats,
                           consumable_stats=consumable_stats,
                           worker_stats=worker_stats,
                           ticket_stats=ticket_stats,
                           duplicate_barcodes=duplicate_barcodes,
                           overdue_loans=overdue_loans,
                           notices=notices,
                           timesheet_prefill=timesheet_prefill,
                           timesheet_quick_enabled=timesheet_quick_enabled,
                           weekly_reports_enabled=weekly_reports_enabled)
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Startseite: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return render_template('index_public.html',
                           tool_stats={'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
                           consumable_stats={'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
                           worker_stats={'total': 0, 'by_department': []},
                           ticket_stats={'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0},
                           duplicate_barcodes=[],
                           overdue_loans=[],
                           notices=[],
                           timesheet_prefill=None,
                           timesheet_quick_enabled=False,
                           weekly_reports_enabled=False)

@bp.route('/emergency-admin')
def emergency_admin():
    """
    Notfall-Route zur Erstellung eines Admin-Benutzers
    """
    try:
        import os, secrets
        # Standardmäßig deaktivieren; nur explizit per ENV aktivieren
        if os.environ.get('ENABLE_EMERGENCY_ADMIN', 'false').lower() != 'true':
            return "<h1>403 Forbidden</h1><p>Emergency-Admin ist deaktiviert.</p>", 403
        token_env = os.environ.get('EMERGENCY_ADMIN_TOKEN')
        # Header bevorzugen
        req_token = request.headers.get('X-Emergency-Token') or request.args.get('token')
        if token_env and req_token != token_env:
            return "<h1>403 Forbidden</h1><p>Ungültiger oder fehlender Emergency-Token.</p>", 403
        from werkzeug.security import generate_password_hash
        from datetime import datetime
        
        # Prüfe ob Admin-Benutzer bereits existiert
        admin_user = mongodb.find_one('users', {'role': 'admin'})
        
        if admin_user:
                    return f"""
        <html>
        <head><title>Admin-Benutzer existiert</title></head>
        <body>
            <h1>✅ Admin-Benutzer existiert bereits</h1>
            <p><strong>Benutzername:</strong> admin</p>
            <p><strong>Passwort:</strong> [Standard-Passwort]</p>
            <p><a href="/auth/login">→ Zum Login</a></p>
        </body>
        </html>
        """
        
        # Erstelle Admin-Benutzer mit zufälligem Passwort
        admin_data = {
            'username': 'admin',
            'password_hash': generate_password_hash(secrets.token_urlsafe(16)),
            'role': 'admin',
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'firstname': 'Administrator',
            'lastname': 'System',
            'email': 'admin@scandy.local'
        }
        
        _id = mongodb.insert_one('users', admin_data)
        
        return f"""
        <html>
        <head><title>Admin-Benutzer erstellt</title></head>
        <body>
            <h1>✅ Admin-Benutzer erfolgreich erstellt!</h1>
            <p><strong>Benutzername:</strong> admin</p>
            <p><strong>Passwort:</strong> Wurde zufällig gesetzt. Bitte setzen Sie es per Reset zurück.</p>
            <p><a href="/auth/login">→ Zum Login</a></p>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <head><title>Fehler</title></head>
        <body>
            <h1>❌ Fehler beim Erstellen des Admin-Benutzers</h1>
            <p>Fehler: {str(e)}</p>
        </body>
        </html>
        """

@bp.route('/about')
def about():
    """Zeigt die About-Seite mit Systemdokumentation"""
    return render_template('about.html') 