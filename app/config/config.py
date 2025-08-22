"""
Konfigurationsmodul für Scandy - MongoDB-only
"""
import os
from pathlib import Path
import secrets
from datetime import datetime
from flask import request, redirect

# Einfache .env-Ladung (ohne Abhängigkeit), damit ENV-Variablen wie SECRET_KEY
# auch unter systemd/Gunicorn konsistent in allen Workern verfügbar sind
def _load_env_files():
    candidates = [
        Path(__file__).resolve().parents[2] / '.env',  # Projektwurzel/.env
        Path('/opt/scandy/.env')
    ]
    for env_path in candidates:
        try:
            if env_path.exists():
                with env_path.open('r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        key, val = line.split('=', 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        # Nur setzen, wenn nicht bereits im Prozess-ENV vorhanden
                        if key and key not in os.environ:
                            os.environ[key] = val
        except Exception:
            # Silent fallback – ENV bleibt unverändert
            pass

_load_env_files()

class Config:
    """Basis-Konfigurationsklasse"""
    # Basis-Verzeichnis der Anwendung
    BASE_DIR = Path(__file__).parent.parent.parent
    
    # MongoDB Konfiguration
    MONGODB_URI = os.environ.get('MONGODB_URI')
    MONGODB_DB = os.environ.get('MONGODB_DB', 'scandy')
    MONGODB_COLLECTION_PREFIX = os.environ.get('MONGODB_COLLECTION_PREFIX', '')
    
    # Upload-Verzeichnis
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'uploads')
    
    # Backup-Verzeichnis
    BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
    
    # Flask-Session
    SESSION_TYPE = os.environ.get('SESSION_TYPE', 'filesystem')
    SESSION_FILE_DIR = os.environ.get('SESSION_FILE_DIR', os.path.join(BASE_DIR, 'app', 'flask_session'))
    SESSION_PERMANENT = os.environ.get('SESSION_PERMANENT', 'True').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', '604800'))  # 7 Tage (für Intranet)
    SESSION_FILE_MODE = 0o644  # Berechtigungen für Session-Dateien (rw-r--r--)
    SESSION_FILE_THRESHOLD = 500  # Maximale Anzahl Session-Dateien
    
    # Sicherheit
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ENABLE_HTTPS = os.environ.get('ENABLE_HTTPS', 'false').lower() == 'true'
    
    # Server-Einstellungen
    HOST = '0.0.0.0'
    PORT = 5000
    
    # Static Files Konfiguration (für LXC-Container)
    STATIC_FOLDER = os.path.join(BASE_DIR, 'app', 'static')
    STATIC_URL_PATH = '/static'
    
    # LXC-spezifische Einstellungen
    LXC_MODE = os.environ.get('LXC_MODE', 'false').lower() == 'true'
    if LXC_MODE:
        # Deaktiviere HTTPS für LXC-Container
        SESSION_COOKIE_SECURE = False
        REMEMBER_COOKIE_SECURE = False
    
    # Base URL für E-Mails und externe Links
    BASE_URL = os.environ.get('BASE_URL')
    if not BASE_URL:
        # Automatische Erkennung der externen IP
        import socket
        try:
            # Hole die externe IP-Adresse (nicht die Docker-interne)
            # Verwende eine öffentliche DNS-Abfrage um die externe IP zu bekommen
            import requests
            try:
                # Versuche die externe IP über einen öffentlichen Service zu bekommen
                response = requests.get('https://api.ipify.org', timeout=3)
                if response.status_code == 200:
                    external_ip = response.text.strip()
                    BASE_URL = f"http://{external_ip}:{PORT}"
                else:
                    raise Exception("Konnte externe IP nicht abrufen")
            except:
                # Fallback: Verwende die lokale IP-Adresse
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                BASE_URL = f"http://{local_ip}:{PORT}"
        except:
            # Fallback auf localhost
            BASE_URL = f"http://localhost:{PORT}"
    
    # Sicherheitseinstellungen - für HTTP/Proxy-Setups lockerer
    # Für HTTP (Port 80) müssen Cookies ohne Secure-Flag gesetzt werden
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Erlaubt Cross-Site-Requests für Login
    SESSION_COOKIE_DOMAIN = None  # Keine Domain-Beschränkung für Intranet
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', 'False').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'  # Erlaubt Cross-Site-Requests für Login
    REMEMBER_COOKIE_DOMAIN = None  # Keine Domain-Beschränkung für Intranet
    
    # Debug: Zeige aktuelle Cookie-Konfiguration
    print(f"DEBUG: Session-Cookies - SECURE: {SESSION_COOKIE_SECURE}, SAMESITE: {SESSION_COOKIE_SAMESITE}")
    
    # Datumsformat-Konfiguration (Deutsch)
    DATE_FORMAT = '%d.%m.%Y'
    TIME_FORMAT = '%H:%M'
    DATETIME_FORMAT = '%d.%m.%Y %H:%M'
    DATETIME_FULL_FORMAT = '%d.%m.%Y %H:%M:%S'
    
    # Locale-Konfiguration
    LOCALE = 'de_DE'
    TIMEZONE = 'Europe/Berlin'
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    @staticmethod
    def format_datetime(dt, format_type='datetime'):
        """Formatiert ein Datum im deutschen Format"""
        if not dt:
            return ''
        
        if isinstance(dt, str):
            try:
                # Versuche verschiedene Eingabeformate
                for fmt in ['%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M', '%Y-%m-%d']:
                    try:
                        dt = datetime.strptime(dt, fmt)
                        break
                    except ValueError:
                        continue
            except:
                return dt
        
        formats = {
            'date': Config.DATE_FORMAT,
            'time': Config.TIME_FORMAT,
            'datetime': Config.DATETIME_FORMAT,
            'datetime_full': Config.DATETIME_FULL_FORMAT
        }
        
        return dt.strftime(formats.get(format_type, Config.DATETIME_FORMAT))
    
    @staticmethod
    def parse_datetime(date_string, format_type='datetime'):
        """Parst ein Datum aus deutschem Format"""
        if not date_string:
            return None
        
        formats = {
            'date': Config.DATE_FORMAT,
            'time': Config.TIME_FORMAT,
            'datetime': Config.DATETIME_FORMAT,
            'datetime_full': Config.DATETIME_FULL_FORMAT
        }
        
        try:
            return datetime.strptime(date_string, formats.get(format_type, Config.DATETIME_FORMAT))
        except ValueError:
            return None

class DevelopmentConfig(Config):
    """Entwicklungs-Konfiguration"""
    DEBUG = os.environ.get('FLASK_DEBUG', '1') in ('1', 'true', 'True')
    TESTING = False
    SECRET_KEY = 'dev-key-not-for-production'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = False  # Erlaubt JavaScript-Zugriff für Debugging

class TestingConfig(Config):
    """Test-Konfiguration"""
    DEBUG = True
    TESTING = True
    SECRET_KEY = 'test-key-not-for-production'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    # MongoDB für Tests
    MONGODB_DB = 'scandy_test'

class ProductionConfig(Config):
    """Produktions-Konfiguration"""
    DEBUG = os.environ.get('FLASK_DEBUG', '0') in ('1', 'true', 'True')
    TESTING = False
    
    # Erweiterte Sicherheitseinstellungen (an HTTPS koppelbar)
    # Für HTTP (Port 80) müssen Cookies ohne Secure-Flag gesetzt werden
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Erlaubt Cross-Site-Requests für HTTP
    SESSION_COOKIE_DOMAIN = None  # Keine Domain-Beschränkung für Intranet
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'  # Erlaubt Cross-Site-Requests für HTTP
    REMEMBER_COOKIE_DOMAIN = None  # Keine Domain-Beschränkung für Intranet
    
    # Security Headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        # CSP mit Nonce-Unterstützung. Templates sollten nonce="{{ csp_nonce }}" an Script-/Style-Tags setzen.
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        # Kamera zulassen (wichtig für mobile Quickscan). Optional weitere Quellen ergänzen.
        'Permissions-Policy': "geolocation=(), microphone=(), camera=(self)"
    }
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = 'memory://'
    
    @classmethod
    def init_app(cls, app):
        # Produktionsspezifische Initialisierung
        if not app.config['SECRET_KEY']:
            app.config['SECRET_KEY'] = secrets.token_hex(32)

        # Cookie-Sicherheit abhängig von ENABLE_HTTPS steuern
        enable_https = os.environ.get('ENABLE_HTTPS', 'false').lower() == 'true'
        if not enable_https:
            app.config['SESSION_COOKIE_SECURE'] = False
            app.config['REMEMBER_COOKIE_SECURE'] = False
            app.config['SESSION_COOKIE_DOMAIN'] = None
            app.config['REMEMBER_COOKIE_DOMAIN'] = None
        
        # Session-Verzeichnis-Berechtigungen sicherstellen
        session_dir = app.config.get('SESSION_FILE_DIR')
        if session_dir and os.path.exists(session_dir):
            try:
                os.chmod(session_dir, 0o755)  # rwxr-xr-x
                app.logger.info(f"Session-Verzeichnis-Berechtigungen gesetzt: {session_dir}")
            except Exception as e:
                app.logger.warning(f"Konnte Session-Verzeichnis-Berechtigungen nicht setzen: {e}")
        
        # Security Headers hinzufügen (CSP Nonce einsetzen)
        @app.after_request
        def add_security_headers(response):
            for header, value in cls.SECURITY_HEADERS.items():
                if header == 'Content-Security-Policy':
                    try:
                        from flask import g
                        nonce = getattr(g, 'csp_nonce', '')
                        response.headers[header] = value.format(nonce=nonce)
                    except Exception:
                        response.headers[header] = value.replace("{nonce}", "")
                else:
                    response.headers[header] = value
            return response
        
        # HTTPS-Umleitung für Produktion
        if enable_https:
            @app.before_request
            def force_https():
                if not request.is_secure and request.headers.get('X-Forwarded-Proto', 'http') == 'http':
                    url = request.url.replace('http://', 'https://', 1)
                    return redirect(url, code=301)

        # CSP Nonce pro Request erzeugen
        @app.before_request
        def set_csp_nonce():
            try:
                import secrets as _secrets
                from flask import g
                g.csp_nonce = _secrets.token_urlsafe(16)
            except Exception:
                pass

# Konfigurationen
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 