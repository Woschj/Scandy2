"""
Konstanten für die Scandy-Anwendung

Dieses Modul definiert alle Konstanten, um Magic Numbers und Strings zu vermeiden.
"""

# === TICKET KONSTANTEN ===
TICKET_STATUS = {
    'OFFEN': 'offen',
    'IN_BEARBEITUNG': 'in_bearbeitung',
    'WARTET_AUF_ANTWORT': 'wartet_auf_antwort',
    'GELOEST': 'gelöst',
    'GESCHLOSSEN': 'geschlossen'
}

TICKET_PRIORITIES = {
    'NIEDRIG': 'niedrig',
    'NORMAL': 'normal',
    'HOCH': 'hoch',
    'KRITISCH': 'kritisch'
}

# === USER ROLES ===
USER_ROLES = {
    'ADMIN': 'admin',
    'MITARBEITER': 'mitarbeiter',
    'ANWENDER': 'anwender',
    'TEILNEHMER': 'teilnehmer'
}

# === PERMISSION LEVELS ===
PERMISSION_LEVELS = {
    'NONE': 0,
    'READ': 1,
    'WRITE': 2,
    'UPDATE': 3,
    'DELETE': 4,
    'ADMIN': 5
}

# === CACHE KONSTANTEN ===
CACHE_TTL = {
    'VERY_SHORT': 30,      # 30 Sekunden
    'SHORT': 60,           # 1 Minute
    'MEDIUM': 300,         # 5 Minuten
    'LONG': 1800,          # 30 Minuten
    'VERY_LONG': 3600      # 1 Stunde
}

# === DATABASE KONSTANTEN ===
DB_COLLECTIONS = {
    'USERS': 'users',
    'TICKETS': 'tickets',
    'TOOLS': 'tools',
    'WORKERS': 'workers',
    'CONSUMABLES': 'consumables',
    'LENDINGS': 'lendings',
    'TICKET_MESSAGES': 'ticket_messages',
    'TICKET_ASSIGNMENTS': 'ticket_assignments',
    'NOTIFICATIONS': 'notifications',
    'SETTINGS': 'settings'
}

# === PAGINATION KONSTANTEN ===
PAGINATION_DEFAULTS = {
    'PAGE_SIZE': 25,
    'MAX_PAGE_SIZE': 100,
    'DEFAULT_PAGE': 1
}

# === DATE FORMATS ===
DATE_FORMATS = {
    'DISPLAY': '%d.%m.%Y',
    'DISPLAY_WITH_TIME': '%d.%m.%Y %H:%M',
    'ISO': '%Y-%m-%d',
    'ISO_WITH_TIME': '%Y-%m-%dT%H:%M:%S',
    'FILENAME': '%Y%m%d_%H%M%S'
}

# === ERROR CODES ===
ERROR_CODES = {
    'VALIDATION_ERROR': 'VALIDATION_ERROR',
    'PERMISSION_ERROR': 'PERMISSION_ERROR',
    'DATABASE_ERROR': 'DATABASE_ERROR',
    'NOT_FOUND': 'NOT_FOUND',
    'EXTERNAL_SERVICE_ERROR': 'EXTERNAL_SERVICE_ERROR'
}

# === NOTIFICATION TYPES ===
NOTIFICATION_TYPES = {
    'INFO': 'info',
    'SUCCESS': 'success',
    'WARNING': 'warning',
    'ERROR': 'error'
}

# === FILE UPLOAD KONSTANTEN ===
UPLOAD_CONFIG = {
    'MAX_FILE_SIZE': 5 * 1024 * 1024,  # 5MB
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'xlsx'},
    'IMAGE_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif'}
}

# === SESSION KONSTANTEN ===
SESSION_CONFIG = {
    'LIFETIME_DAYS': 7,
    'REMEMBER_ME_DAYS': 30,
    'INACTIVE_TIMEOUT_MINUTES': 60
}

# === API RESPONSE CODES ===
API_RESPONSES = {
    'SUCCESS': 200,
    'CREATED': 201,
    'BAD_REQUEST': 400,
    'UNAUTHORIZED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'CONFLICT': 409,
    'INTERNAL_ERROR': 500
}

# === BUSINESS LOGIC KONSTANTEN ===
BUSINESS_RULES = {
    'MAX_TICKETS_PER_USER': 50,
    'MAX_ASSIGNMENTS_PER_TICKET': 5,
    'AUTO_CLOSE_DAYS': 7,
    'NOTIFICATION_RETRY_ATTEMPTS': 3,
    'CACHE_INVALIDATION_INTERVAL': 300  # Sekunden
}
