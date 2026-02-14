from flask import Blueprint, render_template, request, redirect, url_for, flash, session
# from app.utils.db_schema import SchemaManager  # entfernt für MongoDB-only
from app.config import config
from werkzeug.security import generate_password_hash
from app.models.mongodb_database import MongoDB
from app.models.mongodb_models import MongoDBUser
import logging
# from app.models.database import Database  # entfernt für MongoDB-only
from flask_login import login_required

# Logger einrichten
logger = logging.getLogger(__name__)

bp = Blueprint('setup', __name__)
mongodb = MongoDB()

@bp.route('/setup/admin', methods=['GET', 'POST'])
def setup_admin():
    current_config = config['default']()
    
    # Prüfe ob bereits ein Admin-Benutzer existiert
    if is_admin_user_present():
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if not username or len(username) < 3:
            return render_template('setup_admin.html', error='Der Benutzername muss mindestens 3 Zeichen lang sein.')
        if len(username) > 50:
            return render_template('setup_admin.html', error='Der Benutzername darf maximal 50 Zeichen lang sein.')
        if len(password) < 8:
            return render_template('setup_admin.html', error='Das Passwort muss mindestens 8 Zeichen lang sein.')
        if password != password_confirm:
            return render_template('setup_admin.html', error='Die Passwörter stimmen nicht überein.')
        # Erstelle den Admin-Benutzer
        success, message = create_admin_user(username, password, 'admin')
        if success:
            return redirect(url_for('setup.settings'))
        else:
            return render_template('setup_admin.html', error=message)
                
    return render_template('setup_admin.html')

@bp.route('/setup/settings', methods=['GET', 'POST'])
def settings():
    """Systemeinstellungen"""
    if request.method == 'POST':
        try:
            # Hole Formulardaten
            label_tools_name = request.form.get('label_tools_name', '').strip()
            label_tools_icon = request.form.get('label_tools_icon', '').strip()
            label_consumables_name = request.form.get('label_consumables_name', '').strip()
            label_consumables_icon = request.form.get('label_consumables_icon', '').strip()
            label_tickets_name = request.form.get('label_tickets_name', '').strip()
            label_tickets_icon = request.form.get('label_tickets_icon', '').strip()
            
            logger.info(f"[SETUP] Formulardaten: label_tools_name={label_tools_name}, label_tools_icon={label_tools_icon}, label_consumables_name={label_consumables_name}, label_consumables_icon={label_consumables_icon}, label_tickets_name={label_tickets_name}, label_tickets_icon={label_tickets_icon}")
            
            # Lösche alte Einstellungen
            mongodb.delete_many('settings', {'key': {'$in': ['label_tools_name', 'label_tools_icon', 'label_consumables_name', 'label_consumables_icon', 'label_tickets_name', 'label_tickets_icon']}})
            
            # Füge neue Einstellungen hinzu (mit upsert=True um Duplikate zu vermeiden)
            settings_data = [
                {'key': 'label_tools_name', 'value': label_tools_name or 'Werkzeuge', 'description': 'Anzeigename für Werkzeuge'},
                {'key': 'label_tools_icon', 'value': label_tools_icon or 'fas fa-tools', 'description': 'Icon für Werkzeuge'},
                {'key': 'label_consumables_name', 'value': label_consumables_name or 'Verbrauchsmaterial', 'description': 'Anzeigename für Verbrauchsmaterial'},
                {'key': 'label_consumables_icon', 'value': label_consumables_icon or 'fas fa-box-open', 'description': 'Icon für Verbrauchsmaterial'},
                {'key': 'label_tickets_name', 'value': label_tickets_name or 'Tickets', 'description': 'Anzeigename für Tickets'},
                {'key': 'label_tickets_icon', 'value': label_tickets_icon or 'fas fa-ticket-alt', 'description': 'Icon für Tickets'}
            ]
            
            for setting in settings_data:
                mongodb.update_one('settings', 
                                 {'key': setting['key']}, 
                                 {'$set': setting}, 
                                 upsert=True)
            
            flash('Einstellungen erfolgreich gespeichert', 'success')
            return redirect(url_for('setup.setup_optional'))
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Einstellungen: {str(e)}")
            flash('Fehler beim Speichern der Einstellungen', 'error')
            return redirect(url_for('setup.settings'))
    
    # GET: Zeige Einstellungen
    try:
        settings = {}
        rows = mongodb.find('settings', {})
        for row in rows:
            settings[row['key']] = row['value']
            
        return render_template('setup_settings.html',
            label_tools_name=settings.get('label_tools_name', 'Werkzeuge'),
            label_tools_icon=settings.get('label_tools_icon', 'fas fa-tools'),
            label_consumables_name=settings.get('label_consumables_name', 'Verbrauchsmaterial'),
            label_consumables_icon=settings.get('label_consumables_icon', 'fas fa-box-open'),
            label_tickets_name=settings.get('label_tickets_name', 'Tickets'),
            label_tickets_icon=settings.get('label_tickets_icon', 'fas fa-ticket-alt'))
            
    except Exception as e:
        logger.error(f"Fehler beim Laden der Einstellungen: {str(e)}")
        flash('Fehler beim Laden der Einstellungen', 'error')
        return redirect(url_for('main.index'))

@bp.route('/setup/optional', methods=['GET', 'POST'])
def setup_optional():
    if request.method == 'POST':
        categories = request.form.getlist('categories[]')
        locations = request.form.getlist('locations[]')
        departments = request.form.getlist('departments[]')
        
        try:
            # Speichere Kategorien
            if categories:
                # Entferne leere Einträge
                categories = [cat.strip() for cat in categories if cat.strip()]
                mongodb.update_one('settings', 
                                 {'key': 'categories'}, 
                                 {'$set': {'value': categories}}, 
                                 upsert=True)
                logger.info(f"[SETUP] Kategorien gespeichert: {categories}")
            
            # Speichere Standorte
            if locations:
                # Entferne leere Einträge
                locations = [loc.strip() for loc in locations if loc.strip()]
                mongodb.update_one('settings', 
                                 {'key': 'locations'}, 
                                 {'$set': {'value': locations}}, 
                                 upsert=True)
                logger.info(f"[SETUP] Standorte gespeichert: {locations}")
            
            # Speichere Abteilungen
            if departments:
                # Entferne leere Einträge
                departments = [dept.strip() for dept in departments if dept.strip()]
                mongodb.update_one('settings', 
                                 {'key': 'departments'}, 
                                 {'$set': {'value': departments}}, 
                                 upsert=True)
                logger.info(f"[SETUP] Abteilungen gespeichert: {departments}")
            
            flash('Optionale Einstellungen wurden gespeichert', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der optionalen Einstellungen: {str(e)}")
            return render_template('setup_optional.html', error='Fehler beim Speichern der Einstellungen')
    
    # GET: Lade vorhandene Einstellungen für die Anzeige
    try:
        # Lade vorhandene Einstellungen
        settings = {}
        rows = mongodb.find('settings', {})
        for row in rows:
            settings[row['key']] = row['value']
        
        # Hole aktuelle Werte
        current_categories = settings.get('categories', [])
        current_locations = settings.get('locations', [])
        current_departments = settings.get('departments', [])
        
        # Stelle sicher, dass es Listen sind
        if isinstance(current_categories, str):
            current_categories = [cat.strip() for cat in current_categories.split(',') if cat.strip()]
        if isinstance(current_locations, str):
            current_locations = [loc.strip() for loc in current_locations.split(',') if loc.strip()]
        if isinstance(current_departments, str):
            current_departments = [dept.strip() for dept in current_departments.split(',') if dept.strip()]
        
        # Füge Standardwerte hinzu, falls keine vorhanden sind
        if not current_categories:
            current_categories = ['Elektrowerkzeuge', 'Handwerkzeug', 'Messwerkzeuge']
        if not current_locations:
            current_locations = ['Lager A', 'Lager B', 'Werkstatt']
        if not current_departments:
            current_departments = ['IT', 'Produktion', 'Verwaltung']
        
        return render_template('setup_optional.html',
                             categories=current_categories,
                             locations=current_locations,
                             departments=current_departments)
                             
    except Exception as e:
        logger.error(f"Fehler beim Laden der optionalen Einstellungen: {str(e)}")
        return render_template('setup_optional.html', error='Fehler beim Laden der Einstellungen')

def is_admin_user_present():
    """Prüft ob ein Admin-Benutzer existiert."""
    count = mongodb.count_documents('users', {'role': 'admin'})
    return count > 0

def create_admin_user(username, password, role):
    hashed_password = generate_password_hash(password)
    try:
        user_data = {
            'username': username,
            'password_hash': hashed_password,
            'role': role,
            'is_active': True
        }
        mongodb.insert_one('users', user_data)
        return True, "Admin-Benutzer erfolgreich erstellt"
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Admin-Benutzers: {str(e)}")
        return False, f"Fehler beim Erstellen des Admin-Benutzers: {str(e)}"