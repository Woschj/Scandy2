#!/usr/bin/env python3
"""
Skript zum Erstellen des Admin-Benutzers.
"""

import sys
import os
import secrets
import string
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash
from datetime import datetime
from app.models.mongodb_database import MongoDB

def generate_secure_password(length=16):
    """Generiert ein sicheres Passwort"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_admin_user():
    """Erstellt den Admin-Benutzer in der Datenbank"""
    try:
        mongodb = MongoDB()
        
        # Generiere sicheres Passwort
        secure_password = generate_secure_password()
        
        # Admin-Daten
        admin_data = {
            'username': 'Admin',
            'password_hash': generate_password_hash(secure_password),
            'role': 'admin',
            'is_active': True,
            'timesheet_enabled': False,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Prüfe ob Admin bereits existiert
        existing_admin = mongodb.find_one('users', {'username': 'Admin'})
        if existing_admin:
            print("Admin-Benutzer existiert bereits!")
            print("⚠️  WICHTIG: Ändern Sie das Admin-Passwort nach dem ersten Login!")
            return
        
        # Admin erstellen
        result = mongodb.insert_one('users', admin_data)
        print(f"Admin-Benutzer erfolgreich erstellt mit ID: {result.inserted_id}")
        
        # Systemeinstellungen
        settings = [
            {'key': 'label_tickets_name', 'value': 'Tickets'},
            {'key': 'label_tickets_icon', 'value': 'fas fa-ticket-alt'},
            {'key': 'label_tools_name', 'value': 'Werkzeuge'},
            {'key': 'label_tools_icon', 'value': 'fas fa-tools'},
            {'key': 'label_consumables_name', 'value': 'Verbrauchsmaterial'},
            {'key': 'label_consumables_icon', 'value': 'fas fa-box-open'}
        ]
        
        for setting in settings:
            mongodb.update_one('settings', {'key': setting['key']}, {'$set': setting}, upsert=True)
        
        print("Systemeinstellungen gespeichert")
        print("Setup abgeschlossen!")
        print("🔐 SICHERHEITSHINWEIS:")
        print(f"Temporäres Admin-Passwort: {secure_password}")
        print("⚠️  ÄNDERN SIE DIESES PASSWORT NACH DEM ERSTEN LOGIN!")
        print("   Gehen Sie zu: Admin → Profil → Passwort ändern")
        
    except Exception as e:
        print(f"Fehler beim Erstellen des Admin-Benutzers: {e}")

if __name__ == "__main__":
    create_admin_user() 