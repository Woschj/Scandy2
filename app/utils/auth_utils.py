from functools import wraps
from flask import session, redirect, url_for, flash, request, g
import logging
from werkzeug.security import check_password_hash
from app.models.mongodb_database import get_mongodb
import hashlib
import base64
import os

logger = logging.getLogger(__name__)

def get_mongodb_instance():
    """Lazy initialization der MongoDB-Instanz"""
    return get_mongodb()

def needs_setup():
    """Überprüft, ob ein Admin-Benutzer in der MongoDB existiert.

    Returns:
        bool: True, wenn kein Admin-Benutzer gefunden wurde oder ein Fehler auftrat,
              andernfalls False.
    """
    try:
        # Prüfe, ob mindestens ein Admin existiert
        mongodb = get_mongodb_instance()
        admin_count = mongodb.count_documents('users', {'role': 'admin'})
        return admin_count == 0  # True wenn kein Admin gefunden wurde
    except Exception as e:
        # Wenn Collection oder DB nicht existiert oder anderer Fehler, ist Setup nötig
        print(f"Fehler beim Prüfen auf Admin-Benutzer für Setup: [Interner Fehler]")
        return True

def is_admin_user_present():
    try:
        mongodb = get_mongodb_instance()
        admin_count = mongodb.count_documents('users', {'role': 'admin'})
        return admin_count > 0
    except Exception as e:
        print(f"Fehler beim Prüfen auf Admin-Benutzer: [Interner Fehler]")
        return False

def check_password_compatible(password_hash, password):
    """
    Überprüft ein Passwort gegen verschiedene Hash-Formate.
    
    Unterstützt:
    - werkzeug.security (sha256) - aktuelle Anwendung
    - bcrypt ($2b$) - aus MongoDB-Initialisierung
    - scrypt (aus Backup-Imports)
    
    Args:
        password_hash (str): Der gespeicherte Hash
        password (str): Das zu überprüfende Passwort
        
    Returns:
        bool: True wenn Passwort korrekt ist, False sonst
    """
    try:
        logger.info(f"Passwort-Überprüfung für Hash-Typ: {password_hash[:20]}...")
        
        # Versuche zuerst werkzeug.security (Standard)
        if check_password_hash(password_hash, password):
            logger.info("Passwort mit werkzeug.security verifiziert")
            return True
        
        # Prüfe ob es ein bcrypt-Hash ist ($2b$)
        if password_hash.startswith('$2b$'):
            logger.info("Bcrypt-Hash erkannt")
            return check_bcrypt_password(password_hash, password)
        
        # Prüfe ob es ein scrypt-Hash ist
        if password_hash.startswith('scrypt:'):
            logger.info("Scrypt-Hash erkannt")
            return check_scrypt_password(password_hash, password)
        
        logger.warning(f"Unbekannter Hash-Typ: {password_hash[:20]}...")
        return False
        
    except Exception as e:
        logger.error(f"Fehler bei der Passwort-Überprüfung: [Interner Fehler]")
        return False

def check_bcrypt_password(password_hash, password):
    """
    Überprüft ein bcrypt-gehashtes Passwort.
    
    Args:
        password_hash (str): bcrypt-Hash im Format '$2b$...'
        password (str): Das zu überprüfende Passwort
        
    Returns:
        bool: True wenn Passwort korrekt ist, False sonst
    """
    try:
        import bcrypt
        # bcrypt.compare() überprüft das Passwort gegen den Hash
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        logger.error(f"Fehler bei bcrypt-Passwort-Überprüfung: [Interner Fehler]")
        return False

def check_scrypt_password(password_hash, password):
    """
    Überprüft ein scrypt-gehashtes Passwort.
    
    Args:
        password_hash (str): scrypt-Hash im Format 'scrypt:N:r:p$salt$hash'
        password (str): Das zu überprüfende Passwort
        
    Returns:
        bool: True wenn Passwort korrekt ist, False sonst
    """
    try:
        # Verwende hashlib.scrypt (Python 3.6+) als Alternative zur scrypt-Bibliothek
        import hashlib
        
        # Parse scrypt-Hash
        # Format: scrypt:N:r:p$salt$hash
        parts = password_hash.split('$')
        if len(parts) != 3:
            return False
        
        method_part = parts[0]  # scrypt:N:r:p
        salt = parts[1]
        stored_hash = parts[2]
        
        # Extrahiere Parameter
        method_parts = method_part.split(':')
        if len(method_parts) != 4 or method_parts[0] != 'scrypt':
            return False
        
        N = int(method_parts[1])  # CPU/Memory cost
        r = int(method_parts[2])  # Block size
        p = int(method_parts[3])  # Parallelization
        
        # Verwende hashlib.scrypt (verfügbar ab Python 3.6)
        computed_hash = hashlib.scrypt(
            password.encode('utf-8'),
            salt=salt.encode('utf-8'),
            n=N,
            r=r,
            p=p
        )
        
        # Konvertiere zu hex für Vergleich
        computed_hash_hex = computed_hash.hex()
        
        # Debug-Logging
        logger.info(f"Scrypt-Vergleich: computed={computed_hash_hex[:20]}..., stored={stored_hash[:20]}...")
        
        return computed_hash_hex == stored_hash
        
    except Exception as e:
        logger.error(f"Fehler bei scrypt-Passwort-Überprüfung: [Interner Fehler]")
        # Sicherheitskritisch: Kein permissiver Fallback
        return False

def is_safe_url(target):
    """
    Überprüft, ob eine URL für Redirects sicher ist (verhindert Open Redirect).
    Erlaubt nur relative URLs ohne Scheme und Host.

    Args:
        target (str): Die zu prüfende URL

    Returns:
        bool: True wenn sicher, False sonst
    """
    if not target:
        return False

    from urllib.parse import urlparse
    try:
        parsed = urlparse(target)
        # Nur Pfade ohne Host und Scheme erlauben (relative URLs)
        return not parsed.netloc and not parsed.scheme and parsed.path.startswith('/')
    except Exception:
        return False