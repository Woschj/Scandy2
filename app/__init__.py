"""
Scandy - Werkzeug- und Verbrauchsmaterialverwaltung

Dieses Modul initialisiert die Flask-Anwendung und konfiguriert alle notwendigen
Komponenten wie Datenbankverbindung, Session-Management, Blueprints und Middleware.

Hauptfunktionen:
- Flask-App-Erstellung und Konfiguration
- MongoDB-Verbindung und Index-Erstellung
- Blueprint-Registrierung
- Error-Handling und Logging
- Context-Processor für Template-Variablen
"""

# Unterdrücke lästige Bibliotheks-Warnungen frühzeitig
import app.utils.warning_suppressor

from flask import Flask, jsonify, render_template, redirect, url_for, g, send_from_directory, session, request, flash, current_app
from flask_session import Session  # Session-Management
from .constants import Routes
from app.config.version import VERSION
import os
import secrets
from datetime import datetime, timedelta
from app.utils.filters import register_filters, status_color, priority_color
import logging
from app.utils.error_handler import handle_errors
from flask_compress import Compress
from app.utils.auth_utils import needs_setup
from pathlib import Path
import sys
from flask_login import LoginManager, current_user
from app.utils.context_processors import register_context_processors
from app.config import Config
from app.routes import init_app
from dotenv import load_dotenv
# from flask_wtf.csrf import CSRFProtect  # CSRF deaktiviert
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# .env-Datei laden
load_dotenv()

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)

# Backup-Verzeichnisse erstellen
backup_dir = Path(__file__).parent.parent / 'backups'
backup_dir.mkdir(exist_ok=True)

def normalize_database_ids():
    """
    Normalisiert alle IDs in der Datenbank zu Strings beim Systemstart.
    Dies verhindert Probleme mit gemischten ID-Typen nach Imports.
    """
    try:
        from app.models.mongodb_database import mongodb
        from bson import ObjectId
        
        collections_to_normalize = [
            'tickets', 'users', 'tools', 'consumables', 'workers',
            'ticket_messages', 'ticket_notes', 'auftrag_details',
            'auftrag_material', 'auftrag_arbeit'
        ]
        
        total_updated = 0
        
        for collection_name in collections_to_normalize:
            try:
                documents = mongodb.find(collection_name, {})
                updated_count = 0
                
                for doc in documents:
                    doc_id = doc.get('_id')
                    
                    # Falls die ID ein ObjectId ist, konvertiere sie zu String
                    if isinstance(doc_id, ObjectId):
                        string_id = str(doc_id)
                        
                        # Erstelle ein neues Dokument mit String-ID
                        new_doc = doc.copy()
                        new_doc['_id'] = string_id
                        
                        # Lösche das alte Dokument und füge das neue ein
                        mongodb.delete_one(collection_name, {'_id': doc_id})
                        mongodb.insert_one(collection_name, new_doc)
                        
                        updated_count += 1
                
                if updated_count > 0:
                    logging.info(f"Collection {collection_name}: {updated_count} IDs normalisiert")
                total_updated += updated_count
                
            except Exception as e:
                logging.warning(f"Fehler bei ID-Normalisierung in Collection {collection_name}: {e}")
        
        if total_updated > 0:
            logging.info(f"ID-Normalisierung abgeschlossen: {total_updated} IDs in allen Collections normalisiert")
        else:
            logging.info("ID-Normalisierung: Alle IDs sind bereits normalisiert")
            
    except Exception as e:
        logging.error(f"Fehler bei ID-Normalisierung: {e}")
        # Nicht die Anwendung stoppen, nur loggen

# Flask-Login Manager konfigurieren
login_manager = LoginManager()
# Für HTTP (Port 80) weniger strenge Session-Protection
login_manager.session_protection = "basic"  # Weniger streng für HTTP
login_manager.login_view = 'auth.login'
login_manager.login_message = "Bitte melden Sie sich an, um auf diese Seite zuzugreifen."
login_manager.login_message_category = "info"

class Config:
    """Konfigurationsklasse für verschiedene Umgebungen"""
    
    @staticmethod
    def init_server():
        """Server-Initialisierung (Platzhalter)"""
        pass

    @staticmethod
    def init_client(server_url=None):
        """Client-Initialisierung (Platzhalter)"""
        pass

    @staticmethod
    def is_pythonanywhere():
        """Prüft, ob die Anwendung auf PythonAnywhere läuft"""
        # This is a placeholder implementation. You might want to implement a more robust check for PythonAnywhere
        return False

def ensure_directories_exist():
    """
    Stellt sicher, dass alle benötigten Verzeichnisse existieren.
    
    Erstellt folgende Verzeichnisse falls sie nicht existieren:
    - Backup-Verzeichnis
    - Upload-Verzeichnis
    - Temporäres Verzeichnis
    - Session-Datei-Verzeichnis
    """
    from app.config import config
    current_config = config['default']()
    project_root = Path(current_config.BASE_DIR)

    # Liste der zu erstellenden Verzeichnisse
    directories = [
        current_config.BACKUP_DIR,
        current_config.UPLOAD_FOLDER,
        project_root / 'tmp',
        current_config.SESSION_FILE_DIR
    ]
    
    # Verzeichnisse erstellen
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Verzeichnis erstellt: {dir_path}")
        else:
            logging.info(f"Verzeichnis existiert bereits: {dir_path}")

# CSRF-Schutz deaktiviert (nicht nötig für interne Netzwerke)
csrf = None

# Rate Limiter initialisieren (lazy initialization)
limiter = None

def get_limiter():
    global limiter
    if limiter is None:
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://"
        )
    return limiter

def create_app(test_config=None):
    """
    Erstellt und konfiguriert die Flask-Anwendung.
    
    Args:
        test_config: Konfiguration für Tests (optional)
    
    Returns:
        Flask-App: Konfigurierte Flask-Anwendung
        
    Initialisiert:
    - Flask-App und Konfiguration
    - Systemnamen aus Umgebungsvariablen
    - Logger und Verzeichnisse
    - MongoDB-Verbindung und Indizes
    - Flask-Login und Session-Management
    - Blueprints und Context-Processor
    - Error-Handling und Filter
    - E-Mail-System
    - CSRF-Schutz und Rate Limiting
    """
    app = Flask(__name__)
    
    # ===== KONFIGURATION LADEN =====
    from app.config import config
    # Konfiguration basierend auf FLASK_ENV wählen, Fallback: development
    if test_config is None:
        env_name = os.environ.get('FLASK_ENV', 'development').lower()
    else:
        env_name = test_config
    if env_name not in config:
        env_name = 'development'
    app.config.from_object(config[env_name])
    # Fallback: SECRET_KEY sicher setzen, falls aus Umgebung/Konfig nicht geladen
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = secrets.token_hex(32)
    
    # ===== CSRF-SCHUTZ DEAKTIVIERT =====
    # csrf.init_app(app)  # CSRF-Schutz deaktiviert
    
    # ===== RATE LIMITING AKTIVIEREN =====
    get_limiter().init_app(app)
    
    # ===== SYSTEMNAMEN AUS UMGEBUNGSVARIABLEN =====
    app.config['SYSTEM_NAME'] = os.environ.get('SYSTEM_NAME') or 'Scandy'
    app.config['TICKET_SYSTEM_NAME'] = os.environ.get('TICKET_SYSTEM_NAME') or 'Aufgaben'
    app.config['TOOL_SYSTEM_NAME'] = os.environ.get('TOOL_SYSTEM_NAME') or 'Werkzeuge'
    app.config['CONSUMABLE_SYSTEM_NAME'] = os.environ.get('CONSUMABLE_SYSTEM_NAME') or 'Verbrauchsgüter'
    
    # ===== BASE URL FÜR E-MAILS =====
    from app.config.config import Config
    app.config['BASE_URL'] = Config.BASE_URL
    
    # ===== LOGGER UND VERZEICHNISSE =====
    from app.utils.logger import init_app_logger
    init_app_logger(app)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("\n=== ANWENDUNGSSTART ===")

    # Jinja-Filter früh registrieren, damit sie bereits beim Blueprint-Import verfügbar sind
    register_filters(app)
    
    ensure_directories_exist()
    
    # ===== MONGODB-INITIALISIERUNG =====
    try:
        from app.models.mongodb_models import create_mongodb_indexes
        from app.models.mongodb_database import mongodb

        # Schneller Health Check vor Index-Erstellung
        try:
            mongodb._client.admin.command('ping')
            logging.info("MongoDB-Verbindung erfolgreich getestet")
        except Exception as e:
            logging.warning(f"MongoDB-Health-Check fehlgeschlagen: {e}")
            raise Exception(f"MongoDB nicht verfügbar: {e}")

        with app.app_context():
            create_mongodb_indexes()
            logging.info("MongoDB-Indizes erstellt")
    except Exception as e:
        logging.error(f"Fehler bei MongoDB-Initialisierung: {e}")
        # Bei MongoDB-Fehlern trotzdem fortfahren (App kann ohne DB funktionieren)
        logging.warning("App startet ohne vollständige MongoDB-Initialisierung fort")
    
    # ===== ID-NORMALISIERUNG BEIM START (opt-in) =====
    # Standard: deaktiviert, kann über ENABLE_ID_NORMALIZATION_ON_START=true aktiviert werden
    if os.environ.get('ENABLE_ID_NORMALIZATION_ON_START', 'false').lower() == 'true':
        try:
            with app.app_context():
                normalize_database_ids()
                logging.info("Datenbank-IDs normalisiert")
        except Exception as e:
            logging.error(f"Fehler bei ID-Normalisierung: {e}")
    else:
        logging.info("ID-Normalisierung beim Start ist deaktiviert (ENABLE_ID_NORMALIZATION_ON_START=false)")
    
    # ===== FLASK-LOGIN INITIALISIEREN =====
    login_manager.init_app(app)
    
    # ===== FLASK-SESSION INITIALISIEREN =====
    # Session-Konfiguration: Verwende Werte aus der Config-Klasse
    app.config.setdefault('SESSION_TYPE', 'filesystem')
    app.config.setdefault('SESSION_FILE_DIR', os.path.join(app.root_path, 'flask_session'))
    app.config.setdefault('SESSION_FILE_THRESHOLD', 500)
    app.config.setdefault('SESSION_FILE_MODE', 0o644)  # Berechtigungen für Session-Dateien (rw-r--r--)
    
    # Session-Cookie-Einstellungen für HTTP (Port 80) korrekt setzen
    # Diese überschreiben die Config-Klasse für HTTP-Umgebungen
    if not app.config.get('SESSION_COOKIE_SECURE', False):
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['SESSION_COOKIE_DOMAIN'] = None  # Keine Domain-Beschränkung für Intranet
        app.config['REMEMBER_COOKIE_SECURE'] = False
        app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
        app.config['REMEMBER_COOKIE_DOMAIN'] = None  # Keine Domain-Beschränkung für Intranet
        app.logger.info("Session-Konfiguration für HTTP angepasst")
    
    app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(days=7))  # 7 Tage für Intranet
    
    # Session-Verzeichnis-Berechtigungen sicherstellen
    session_dir = app.config['SESSION_FILE_DIR']
    if os.path.exists(session_dir):
        try:
            # Setze Berechtigungen für Session-Verzeichnis
            os.chmod(session_dir, 0o755)  # rwxr-xr-x
            # Stelle sicher, dass das Verzeichnis dem root-Benutzer gehört (für Gunicorn)
            import pwd
            root_uid = pwd.getpwnam('root').pw_uid
            root_gid = pwd.getpwnam('root').pw_gid
            os.chown(session_dir, root_uid, root_gid)
            app.logger.info(f"Session-Verzeichnis-Berechtigungen und Besitzer gesetzt: {session_dir}")
        except Exception as e:
            app.logger.warning(f"Konnte Session-Verzeichnis-Berechtigungen nicht setzen: {e}")
    
    # Debug: Zeige aktuelle Session-Konfiguration
    app.logger.info(f"Session-Konfiguration: SECURE={app.config.get('SESSION_COOKIE_SECURE')}, "
                   f"SAMESITE={app.config.get('SESSION_COOKIE_SAMESITE')}, "
                   f"HTTPONLY={app.config.get('SESSION_COOKIE_HTTPONLY')}")
    
    Session(app)
    
    # Session-Bereinigung: Lösche alte Session-Dateien beim Start
    def cleanup_old_sessions():
        """Bereinigt alte Session-Dateien"""
        try:
            session_dir = app.config['SESSION_FILE_DIR']
            if not os.path.exists(session_dir):
                return

            current_time = datetime.now()
            session_lifetime = app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(days=7))
            cutoff_time = current_time - session_lifetime

            cleaned_count = 0
            permission_fixed_count = 0
            max_files_to_check = 1000  # Begrenze Anzahl der zu prüfenden Dateien

            try:
                filenames = os.listdir(session_dir)
            except PermissionError:
                app.logger.warning("Keine Berechtigung für Session-Verzeichnis")
                return

            # Begrenze Anzahl der zu verarbeitenden Dateien
            filenames = filenames[:max_files_to_check]

            for filename in filenames:
                file_path = os.path.join(session_dir, filename)
                if not os.path.isfile(file_path):
                    continue

                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        cleaned_count += 1
                except (OSError, PermissionError):
                    # Überspringe Dateien, die nicht gelöscht werden können
                    pass

            if cleaned_count > 0:
                app.logger.info(f"Session-Bereinigung: {cleaned_count} alte Session-Dateien gelöscht")

            # Stelle sicher, dass alle verbleibenden Session-Dateien die richtigen Berechtigungen haben
            # Aber nur für eine begrenzte Anzahl
            remaining_files = os.listdir(session_dir)[:100]  # Max 100 Dateien für Berechtigungskorrektur
            for filename in remaining_files:
                file_path = os.path.join(session_dir, filename)
                if not os.path.isfile(file_path):
                    continue

                try:
                    os.chmod(file_path, 0o644)  # rw-r--r--
                    # Setze Besitzer auf root für Gunicorn (nur wenn möglich)
                    import pwd
                    try:
                        root_uid = pwd.getpwnam('root').pw_uid
                        root_gid = pwd.getpwnam('root').pw_gid
                        os.chown(file_path, root_uid, root_gid)
                    except (KeyError, PermissionError):
                        # Root-Benutzer nicht verfügbar oder keine Berechtigung
                        pass
                    permission_fixed_count += 1
                except (OSError, PermissionError):
                    # Überspringe Dateien mit Berechtigungsproblemen
                    pass

            if permission_fixed_count > 0:
                app.logger.debug(f"Session-Berechtigungen: {permission_fixed_count} Dateien korrigiert")

        except Exception as e:
            app.logger.warning(f"Fehler bei Session-Bereinigung: {e}")

    # Führe Session-Bereinigung beim Start aus
    cleanup_old_sessions()
    
    # Debug: Zeige Session-Status nach dem Login
    @app.after_request
    def debug_session_after_request(response):
        """Debug: Zeige Session-Status nach jeder Request"""
        if request.endpoint == 'auth.login' and response.status_code == 302:
            app.logger.info(f"DEBUG: Nach Login - Session: {dict(session)}")
            app.logger.info(f"DEBUG: Response Headers: {dict(response.headers)}")
            
            # Prüfe Session-Cookies
            if 'Set-Cookie' in response.headers:
                app.logger.info(f"DEBUG: Session-Cookies gesetzt: {response.headers['Set-Cookie']}")
            else:
                app.logger.warning("DEBUG: Keine Session-Cookies gesetzt!")
                
        return response

    # ===== Department aus Session in Request-Context laden =====
    @app.before_request
    def load_current_department():
        """Lädt das aktuelle Department in den Request-Context.
        Fallback: Wenn nichts in der Session steht, verwende die Default‑Abteilung
        des eingeloggten Benutzers (oder die erste erlaubte).
        """
        try:
            dept = session.get('department')
            # Falls kein Department oder ungültig: aus Benutzerprofil ableiten und validieren
            if current_user.is_authenticated:
                from app.models.mongodb_database import mongodb
                try:
                    user = mongodb.find_one('users', {'username': current_user.username})
                except Exception:
                    user = None
                allowed = []
                if getattr(current_user, 'role', None) == 'admin':
                    # Admins: alle globalen Departments
                    try:
                        depts_setting = mongodb.find_one('settings', {'key': 'departments'})
                        if depts_setting and isinstance(depts_setting.get('value'), list):
                            allowed = [d for d in depts_setting['value'] if isinstance(d, str) and d.strip()]
                    except Exception:
                        allowed = []
                else:
                    allowed = (user.get('allowed_departments') if user else []) or []

                user_default = (user.get('default_department') if user else None)

                # Ungültige Session-Abteilung verwerfen
                if not dept or (allowed and dept not in allowed and getattr(current_user, 'role', None) != 'admin'):
                    dept = user_default or (allowed[0] if allowed else None)
                    session['department'] = dept if dept else None

            g.current_department = dept
        except Exception:
            g.current_department = None
    
    @login_manager.user_loader
    def load_user(user_id):
        """
        Lädt einen Benutzer aus der Datenbank für Flask-Login.
        
        Args:
            user_id: ID des zu ladenden Benutzers (immer ein String)
            
        Returns:
            User-Objekt oder None falls nicht gefunden
        """
        try:
            from app.models.mongodb_models import MongoDBUser
            from app.models.user import User
            from app.models.mongodb_database import mongodb
            
            logging.debug(f"load_user aufgerufen für ID: {user_id}")
            
            # Debug: Zeige alle verfügbaren User-IDs
            all_users = MongoDBUser.get_all()
            logging.debug(f"Verfügbare User-IDs: {[str(user.get('_id', 'No ID')) for user in all_users]}")
            
            # WICHTIG: user_id ist immer ein String (von Flask-Login)
            # Suche direkt in der Datenbank mit verschiedenen Methoden
            
            # Methode 1: Direkte String-Suche
            user_data = mongodb.find_one('users', {'_id': user_id})
            if user_data:
                logging.debug(f"User mit String-ID gefunden: {user_data.get('username')}")
                user = User(user_data)
                logging.debug(f"User geladen: {user.username}, ID: {user.id}")
                return user
            
            # Methode 2: ObjectId-Suche
            try:
                from bson import ObjectId
                obj_id = ObjectId(user_id)
                user_data = mongodb.find_one('users', {'_id': obj_id})
                if user_data:
                    logging.debug(f"User mit ObjectId gefunden: {user_data.get('username')}")
                    user = User(user_data)
                    logging.debug(f"User geladen: {user.username}, ID: {user.id}")
                    return user
            except Exception as e:
                logging.debug(f"ObjectId-Konvertierung fehlgeschlagen: {e}")
            
            # Methode 3: Fallback mit MongoDBUser.get_by_id
            user_data = MongoDBUser.get_by_id(user_id)
            if user_data:
                logging.debug(f"User mit MongoDBUser.get_by_id gefunden: {user_data.get('username')}")
                user = User(user_data)
                logging.debug(f"User geladen: {user.username}, ID: {user.id}")
                return user
            
            # Methode 4: Session-Reparatur - versuche Session zu löschen
            logging.debug(f"Kein User gefunden für ID: {user_id} - Session wird zurückgesetzt")
            try:
                from flask import session
                session.clear()
                logging.debug("Session zurückgesetzt")
            except Exception as e:
                logging.debug(f"Fehler beim Zurücksetzen der Session: {e}")
            
            return None
        except Exception as e:
            logging.error(f"Fehler beim Laden des Benutzers {user_id}: {e}")
            # Bei Fehlern Session zurücksetzen
            try:
                from flask import session
                session.clear()
                logging.debug("Session nach Fehler zurückgesetzt")
            except Exception as session_error:
                logging.debug(f"Fehler beim Zurücksetzen der Session: {session_error}")
            return None
    
    # ===== CONTEXT PROCESSORS REGISTRIEREN =====
    register_context_processors(app)
    
    # Context Processor für Systemnamen
    @app.context_processor
    def inject_system_names():
        """Injiziert Systemnamen in alle Templates"""
        return {
            'system_name': app.config['SYSTEM_NAME'],
            'ticket_system_name': app.config['TICKET_SYSTEM_NAME'],
            'tool_system_name': app.config['TOOL_SYSTEM_NAME'],
            'consumable_system_name': app.config['CONSUMABLE_SYSTEM_NAME']
        }
    
    # ===== STANDARD-ROLLENRECHTE SICHERSTELLEN =====
    try:
        from app.utils.permissions import ensure_default_role_permissions
        with app.app_context():
            ensure_default_role_permissions()
    except Exception as e:
        logging.warning(f"Konnte Default-Rollenrechte nicht sicherstellen: {e}")

    # ===== BLUEPRINTS REGISTRIEREN =====
    init_app(app)
    # CSRF-Schutz komplett deaktiviert
    logging.info("CSRF-Schutz deaktiviert - alle Routen ohne CSRF-Validierung")

    
    # ===== AUTOMATISCHES BACKUP-SYSTEM STARTEN (mit sicherer Fehlerbehandlung) =====
    def start_backup_system_safe():
        """Startet das Backup-System mit besserer Fehlerbehandlung"""
        try:
            from app.utils.auto_backup import start_auto_backup
            with app.app_context():
                start_auto_backup()
                logging.info("Automatisches Backup-System gestartet")
        except ImportError:
            logging.warning("Backup-System-Module nicht verfügbar, überspringe Backup-System-Start")
        except Exception as e:
            logging.error(f"Fehler beim Starten des automatischen Backup-Systems: {e}")
            logging.info("App startet trotzdem ohne Backup-System fort")

    # Starte Backup-System in separatem Thread (nicht-blockierend bei Fehlern)
    import threading
    backup_thread = threading.Thread(target=start_backup_system_safe, daemon=True, name="BackupSystem")
    backup_thread.start()
    
    # ===== AUTOMATISCHE DASHBOARD-REPARATUR BEIM START (im Hintergrund) =====
    def run_dashboard_repair():
        """Führt Dashboard-Reparatur in einem separaten Thread aus"""
        try:
            from app.services.admin_debug_service import AdminDebugService
            with app.app_context():
                # Führe umfassende Dashboard-Reparatur aus
                fixes = AdminDebugService.fix_dashboard_comprehensive()
                if fixes.get('total', 0) > 0:
                    logging.info(f"Automatische Dashboard-Reparatur durchgeführt: {fixes}")
                else:
                    logging.info("Dashboard-Reparatur: Keine Probleme gefunden")
        except Exception as e:
            logging.error(f"Fehler bei automatischer Dashboard-Reparatur: {e}")

    # Starte Dashboard-Reparatur in Hintergrund-Thread (nicht-blockierend)
    import threading
    repair_thread = threading.Thread(target=run_dashboard_repair, daemon=True, name="DashboardRepair")
    repair_thread.start()
    logging.info("Dashboard-Reparatur-Thread gestartet")
    
    # ===== HEALTH CHECK ROUTE =====
    @app.route('/health')
    def health_check():
        """
        Health Check für Docker Container und Monitoring.
        
        Prüft:
        - Datenbankverbindung (MongoDB Ping)
        - Anwendungsstatus
        
        Returns:
            JSON mit Status-Informationen
        """
        try:
            from app.models.mongodb_database import MongoDBDatabase
            mongodb = MongoDBDatabase()
            # Prüfe Datenbankverbindung durch einfache Abfrage
            mongodb._client.admin.command('ping')
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now().isoformat()
            }), 200
        except Exception as e:
            app.logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 503
    
    # ===== FEHLERBEHANDLUNG UND FILTER =====
    handle_errors(app)
    register_filters(app)
    
    # Logging-Setup für Gunicorn deaktiviert
    # setup_logging() verursacht Deadlocks mit Gunicorn
    
    # Register custom filters
    app.jinja_env.filters['status_color'] = status_color
    app.jinja_env.filters['priority_color'] = priority_color
    
    # ===== KOMPRIMIERUNG AKTIVIEREN =====
    Compress(app)

    # ===== CSP Nonce für Templates bereitstellen =====
    @app.context_processor
    def security_processor():
        try:
            return {'csp_nonce': getattr(g, 'csp_nonce', '')}
        except Exception:
            return {'csp_nonce': ''}
    
    # ===== E-MAIL-SYSTEM INITIALISIEREN =====
    try:
        from app.utils.email_utils import init_mail
        init_mail(app)
        app.logger.info("E-Mail-System initialisiert")
    except Exception as e:
        app.logger.warning(f"E-Mail-System konnte nicht initialisiert werden: {e}")
    
    # ===== CONTEXT PROCESSOR FÜR TEMPLATE-VARIABLEN =====
    @app.context_processor
    def utility_processor():
        """Injiziert Farben für Status und Prioritäten in alle Templates"""
        return {
            'status_colors': {
                'offen': 'danger',
                'in_bearbeitung': 'warning',
                'wartet_auf_antwort': 'info',
                'gelöst': 'success',
                'geschlossen': 'secondary'
            },
            'priority_colors': {
                'niedrig': 'secondary',
                'normal': 'primary',
                'hoch': 'error',
                'dringend': 'error'
            }
        }
    
    # ===== CONTEXT PROCESSOR FÜR FEATURE-EINSTELLUNGEN =====
    @app.context_processor
    def feature_processor():
        """Injiziert Feature-Einstellungen in alle Templates"""
        try:
            from app.models.mongodb_database import get_feature_settings
            feature_settings = get_feature_settings()
            return {'feature_settings': feature_settings}
        except Exception as e:
            app.logger.warning(f"Fehler beim Laden der Feature-Einstellungen: {e}")
            return {'feature_settings': {}}

    # ===== CONTEXT PROCESSOR FÜR BERECHTIGUNGEN =====
    @app.context_processor
    def permissions_processor():
        """Stellt has_permission für Templates bereit."""
        try:
            from app.utils.permissions import has_permission
            return {'has_permission': has_permission}
        except Exception:
            # Fallback: alles false (UI blendet dann Buttons aus)
            return {'has_permission': lambda *args, **kwargs: False}

    return app