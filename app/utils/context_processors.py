from flask import current_app, g
from app.constants import Routes
from app.config.version import VERSION
import traceback
import logging
from app.models.mongodb_database import mongodb
from flask_login import current_user
from flask import g
try:
    from flask_wtf.csrf import generate_csrf
except Exception:
    # Optional: CSRF kann global deaktiviert sein
    def generate_csrf():
        return ''

# Import mit try-except um Circular Imports zu vermeiden
try:
    from app.services.custom_fields_service import CustomFieldsService
    CUSTOM_FIELDS_AVAILABLE = True
except ImportError:
    CUSTOM_FIELDS_AVAILABLE = False

logger = logging.getLogger(__name__)

def get_colors():
    """Holt die Farbeinstellungen aus der MongoDB - wird durch inject_colors() ersetzt"""
    # Diese Funktion ist veraltet und wird durch inject_colors() ersetzt
    return inject_colors().get('colors', {})

def inject_colors():
    """Injiziert die Farbeinstellungen aus MongoDB in alle Templates"""
    try:
        color_docs = mongodb.find('settings', {'key': {'$regex': '^color_'}})
        if color_docs:
            color_dict = {}
            for doc in color_docs:
                key = doc['key'].replace('color_', '')
                # Prüfe ob das value Feld existiert
                if 'value' in doc:
                    value = doc['value']
                    color_dict[key] = value
            return {'colors': color_dict}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Farben: {e}")
        logger.debug(traceback.format_exc())
    
    # Fallback-Farben
    return {
        'colors': {
            'primary': '259 94% 51%',
            'primary_content': '0 0% 100%',
            'secondary': '314 100% 47%',
            'secondary_content': '0 0% 100%',
            'accent': '174 60% 51%',
            'accent_content': '0 0% 100%',
            'neutral': '219 14% 28%',
            'neutral_content': '0 0% 100%',
            'base': '0 0% 100%',
            'base_content': '219 14% 28%'
        }
    }

def inject_routes():
    """Fügt die Routen-Konstanten in den Template-Kontext ein"""
    return {'routes': Routes}

def inject_version():
    """Fügt die aktuelle Version zu allen Templates hinzu"""
    try:
        from app.utils.version_checker import get_version_info
        version_info = get_version_info()
        
        return {
            'version': VERSION,
            'version_info': version_info
        }
    except Exception as e:
        logger.error(f"Fehler beim Laden der Versionsinformationen: {str(e)}")
        return {
            'version': VERSION,
            'version_info': {
                'local_version': VERSION,
                'github_version': None,
                'is_up_to_date': None,
                'update_available': False,
                'error': str(e)
            }
        }

def inject_app_labels():
    """Fügt die App-Labels in alle Templates ein"""
    try:
        label_docs = mongodb.find('settings', {'key': {'$regex': '^label_'}})
        app_labels = {
            'tools': {'name': 'Werkzeuge', 'icon': 'fas fa-tools'},
            'consumables': {'name': 'Verbrauchsmaterial', 'icon': 'fas fa-box-open'},
            'tickets': {'name': 'Tickets', 'icon': 'fas fa-ticket-alt'}
        }
        
        # Labels aus der Datenbank laden
        for doc in label_docs:
            key = doc['key'].replace('label_', '')
            # Prüfe ob das value Feld existiert
            if 'value' not in doc:
                continue
            value = doc['value']
            
            # Label-Typ und Attribut extrahieren (z.B. tools_name -> tools.name)
            parts = key.split('_')
            if len(parts) == 2:
                label_type, attr = parts
                if label_type in app_labels:
                    app_labels[label_type][attr] = value
        
        return {'app_labels': app_labels}
    except Exception as e:
        logger.error(f"Fehler beim Laden der App-Labels: {str(e)}")
        return {
            'app_labels': {
                'tools': {'name': 'Werkzeuge', 'icon': 'fas fa-tools'},
                'consumables': {'name': 'Verbrauchsmaterial', 'icon': 'fas fa-box-open'},
                'tickets': {'name': 'Tickets', 'icon': 'fas fa-ticket-alt'}
            }
        }

def inject_unfilled_timesheet_days():
    """Berechnet die Anzahl fehlender Wochenberichte für alle Templates"""
    try:
        from flask import current_app, g
        from flask_login import current_user
        from datetime import datetime, timedelta
        
        # Nur für eingeloggte Nutzende mit aktiviertem Wochenbericht-Feature berechnen
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            return {'unfilled_timesheet_days': 0}
        
        # Prüfe ob Wochenbericht-Feature aktiviert ist
        if not hasattr(current_user, 'timesheet_enabled') or not current_user.timesheet_enabled:
            return {'unfilled_timesheet_days': 0}
        
        # Berechne unausgefüllte Tage für den aktuellen Nutzende
        user_id = current_user.username
        today = datetime.now()
        
        # Hole alle Timesheets des Nutzendes
        timesheets = list(mongodb.find('timesheets', {'user_id': user_id}))
        
        # Berechne unausgefüllte Tage für alle Wochen
        unfilled_days = 0
        for ts in timesheets:
            # Berechne den Wochenstart
            week_start = datetime.fromisocalendar(ts['year'], ts['kw'], 1)  # 1 = Montag
            days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
            
            for i, day in enumerate(days):
                # Berechne das Datum für den aktuellen Tag
                current_day = week_start + timedelta(days=i)
                
                # Prüfe nur vergangene Tage
                if current_day.date() < today.date():
                    has_times = ts.get(f'{day}_start') or ts.get(f'{day}_end')
                    has_tasks = ts.get(f'{day}_tasks')
                    if not (has_times and has_tasks):
                        unfilled_days += 1
        
        return {'unfilled_timesheet_days': unfilled_days}
        
    except Exception as e:
        logger.error(f"Fehler beim Berechnen der fehlenden Wochenberichte: {str(e)}")
        return {'unfilled_timesheet_days': 0}

def inject_feature_settings():
    """Injiziert Feature-Einstellungen in alle Templates für Menü-Kontrolle"""
    try:
        from app.models.mongodb_database import get_feature_settings
        feature_settings = get_feature_settings()
        return {
            'features_enabled': feature_settings,
            'feature_settings': feature_settings
        }
    except Exception as e:
        logger.error(f"Fehler beim Laden der Feature-Einstellungen für Templates: {str(e)}")
        fallback_settings = {
            'tools': True,
            'consumables': True,
            'lending_system': True,
            'ticket_system': True,
            'job_board': False,
            'weekly_reports': False,
            # Werkzeug-Felder (standardmäßig aktiviert)
            'tool_field_serial_number': True,
            'tool_field_invoice_number': True,
            'tool_field_mac_address': True,
            'tool_field_mac_address_wlan': True,
            'tool_field_user_groups': True,
            'tool_field_software': True
        }
        return {
            'features_enabled': fallback_settings,
            'feature_settings': fallback_settings
        }

def inject_custom_fields():
    """
    Injiziert benutzerdefinierte Felder in alle Templates
    
    Lädt alle aktiven benutzerdefinierten Felder für Werkzeuge und Verbrauchsgüter
    und stellt sie als 'custom_fields_tools' und 'custom_fields_consumables' 
    in allen Jinja2-Templates zur Verfügung.
    
    Returns:
        dict: Template-Kontext mit benutzerdefinierten Feldern
    """
    if not CUSTOM_FIELDS_AVAILABLE:
        return {
            'custom_fields_tools': [],
            'custom_fields_consumables': []
        }
    
    try:
        # Lade benutzerdefinierte Felder für beide Typen
        tools_fields = CustomFieldsService.get_custom_fields_for_target('tools')
        consumables_fields = CustomFieldsService.get_custom_fields_for_target('consumables')
        
        return {
            'custom_fields_tools': tools_fields,
            'custom_fields_consumables': consumables_fields
        }
    except Exception as e:
        # Bei Fehlern leere Listen zurückgeben, um Template-Rendering nicht zu stören
        logger.error(f"Fehler beim Laden der benutzerdefinierten Felder: {str(e)}")
        return {
            'custom_fields_tools': [],
            'custom_fields_consumables': []
        }

def register_context_processors(app):
    """Registriert alle Context Processors"""
    app.context_processor(inject_colors)
    app.context_processor(inject_routes)
    app.context_processor(inject_version)
    app.context_processor(inject_app_labels)
    app.context_processor(inject_unfilled_timesheet_days)
    app.context_processor(inject_feature_settings)
    app.context_processor(inject_custom_fields)
    app.context_processor(inject_departments)
    app.context_processor(inject_csrf_token)

def inject_csrf_token():
    """Stellt csrf_token() in allen Templates bereit"""
    try:
        return {'csrf_token': generate_csrf}
    except Exception:
        # Fallback: leere Funktion, um Template-Fehler zu vermeiden
        return {'csrf_token': (lambda: '')}

def inject_departments():
    """Injiziert Departments (Auswahl + aktuelles Department) in Templates.
    Zusätzlich wird eine konfliktfreie Variable `departments_ctx` bereitgestellt,
    um Überschneidungen mit View-Variablen namens `departments` zu vermeiden.
    """
    try:
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            ctx = {'allowed': [], 'current': None}
            return {'departments': ctx, 'departments_ctx': ctx}

        # Nutzende lesen
        user = mongodb.find_one('users', {'username': current_user.username})

        # Globale Departments laden (für Admins nötig)
        all_departments = []
        try:
            depts_setting = mongodb.find_one('settings', {'key': 'departments'})
            if depts_setting and isinstance(depts_setting.get('value'), list):
                all_departments = [d for d in depts_setting['value'] if isinstance(d, str) and d.strip()]
        except Exception:
            all_departments = []

        # Admins: automatisch Zugriff auf alle Abteilungen
        if getattr(current_user, 'role', None) == 'admin' and all_departments:
            allowed = all_departments
        else:
            allowed = user.get('allowed_departments', []) if user else []
        current = getattr(g, 'current_department', None)
        default = user.get('default_department') if user else None
        if not current:
            current = default
        ctx = {'allowed': allowed, 'current': current}
        return {'departments': ctx, 'departments_ctx': ctx}
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Departments Context Fehler: {e}")
        ctx = {'allowed': [], 'current': None}
        return {'departments': ctx, 'departments_ctx': ctx}