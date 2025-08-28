#!/usr/bin/env python3
"""
Skript zum Zurücksetzen des Admin-Passworts
Führt das Passwort auf einen bekannten Wert zurück
"""

import sys
import os
sys.path.append('/opt/scandy')

from app.models.mongodb_database import mongodb
from werkzeug.security import generate_password_hash
from datetime import datetime

def reset_admin_password():
    """Setzt das Admin-Passwort zurück"""
    
    # Neues Passwort (kann nach dem Login geändert werden)
    new_password = "Admin123!"
    
    try:
        # Finde Admin-Benutzer
        admin_user = mongodb.find_one('users', {'role': 'admin'})
        
        if not admin_user:
            print("❌ Kein Admin-Benutzer gefunden!")
            return False
        
        # Aktualisiere das Passwort
        result = mongodb.update_one(
            'users', 
            {'_id': admin_user['_id']}, 
            {
                '$set': {
                    'password_hash': generate_password_hash(new_password),
                    'updated_at': datetime.now()
                }
            }
        )
        
        if result:
            print("✅ Admin-Passwort erfolgreich zurückgesetzt!")
            print(f"📧 E-Mail: {admin_user.get('email', 'Nicht gesetzt')}")
            print(f"👤 Benutzername: {admin_user.get('username', 'Nicht gesetzt')}")
            print(f"🔑 Neues Passwort: {new_password}")
            print("\n⚠️  WICHTIG: Ändern Sie das Passwort nach dem Login!")
            return True
        else:
            print("❌ Fehler beim Zurücksetzen des Passworts!")
            return False
            
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Admin-Passwort zurücksetzen...")
    print("=" * 50)
    
    if reset_admin_password():
        print("\n🎉 Passwort erfolgreich zurückgesetzt!")
        print("Sie können sich jetzt mit dem neuen Passwort einloggen.")
    else:
        print("\n💥 Fehler beim Zurücksetzen des Passworts!")
        sys.exit(1)
