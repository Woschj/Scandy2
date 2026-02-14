import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import warnings

# Unterdrücke lästige Bibliotheks-Warnungen
def suppress_pkg_resources_warnings():
    """Unterdrückt pkg_resources-Warnungen"""
    warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

# Rufe die Funktion beim Import auf
suppress_pkg_resources_warnings()

def setup_logger(name, log_file, level=logging.INFO):
    """Richtet einen spezifischen Logger ein"""
    # Stelle sicher, dass das logs-Verzeichnis existiert
    os.makedirs('logs', exist_ok=True)

    # Handler erstellen
    handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1 MB
        backupCount=5,
        delay=True
    )

    # Formatter erstellen und hinzufügen
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)

    # Logger erstellen und konfigurieren
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    # Konsolen-Handler hinzufügen
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

def init_app_logger(app):
    """Initialisiert den Haupt-Application-Logger"""
    # Stelle sicher, dass das Logs-Verzeichnis existiert
    log_dir = Path(app.root_path) / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Formatter erstellen
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # Entferne alle bestehenden Handler
    app.logger.handlers = []

    # Konsolen-Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    # Datei-Handler
    file_handler = RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=1024 * 1024,
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    # Log-Level setzen
    app.logger.setLevel(logging.INFO)

    # Propagate auf False setzen, um doppelte Meldungen zu vermeiden
    app.logger.propagate = False

# Erstelle spezialisierte Logger für verschiedene Bereiche
def create_specialized_loggers():
    """Erstellt spezialisierte Logger für verschiedene Bereiche"""
    loggers = {}

    # Sicherheits-Logger
    loggers['security'] = setup_logger('scandy.security', 'logs/security.log')

    # Benutzer-Aktionen Logger
    loggers['user_actions'] = setup_logger('scandy.user_actions', 'logs/user_actions.log')

    # Datenbank-Logger
    loggers['database'] = setup_logger('scandy.database', 'logs/database.log')

    # API-Logger
    loggers['api'] = setup_logger('scandy.api', 'logs/api.log')

    # Fehler-Logger
    loggers['errors'] = setup_logger('scandy.errors', 'logs/errors.log')

    # Performance-Logger
    loggers['performance'] = setup_logger('scandy.performance', 'logs/performance.log')

    return loggers

# Globale Logger-Instanz
loggers = create_specialized_loggers()

def log_security_event(event_type, user_id=None, ip_address=None, details=None):
    """Loggt Sicherheitsereignisse"""
    security_logger = loggers['security']

    log_data = {
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': ip_address,
        'details': details,
        'timestamp': logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))
    }

    security_logger.warning(f"SECURITY_EVENT: {log_data}")

    # Bei kritischen Ereignissen auch in Hauptlog
    if event_type in ['login_failed', 'unauthorized_access', 'suspicious_activity']:
        loggers['errors'].error(f"KRITISCHES SICHERHEITSEREIGNIS: {event_type} - User: {user_id}, IP: {ip_address}")

def log_user_action(action, user_id, details=None):
    """Loggt Benutzeraktionen"""
    user_logger = loggers['user_actions']
    user_logger.info(f"USER_ACTION: {action} - User: {user_id} - Details: {details}")

def log_database_operation(operation, collection, duration=None, success=True):
    """Loggt Datenbankoperationen"""
    db_logger = loggers['database']
    status = "SUCCESS" if success else "FAILED"
    duration_str = f" ({duration:.3f}s)" if duration else ""
    db_logger.info(f"DB_OPERATION: {operation} - Collection: {collection} - Status: {status}{duration_str}")

def log_api_request(method, endpoint, user_id=None, status_code=None, duration=None):
    """Loggt API-Anfragen"""
    api_logger = loggers['api']
    user_str = f" - User: {user_id}" if user_id else ""
    status_str = f" - Status: {status_code}" if status_code else ""
    duration_str = f" ({duration:.3f}s)" if duration else ""
    api_logger.info(f"API_REQUEST: {method} {endpoint}{user_str}{status_str}{duration_str}")

def log_performance_metric(metric_name, value, unit=None):
    """Loggt Performance-Metriken"""
    perf_logger = loggers['performance']
    unit_str = f" {unit}" if unit else ""
    perf_logger.info(f"PERFORMANCE: {metric_name}: {value}{unit_str}") 