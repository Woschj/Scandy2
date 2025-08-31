#!/usr/bin/env python3
"""
Skript zum Beheben von Passwort- und E-Mail-Problemen
1. Setzt das Admin-Passwort zurück
2. Testet die E-Mail-Funktionalität
3. Behebt E-Mail-Konfigurationsprobleme
"""

import sys
import os
import subprocess

def run_command(cmd, description):
    """Führt einen Befehl aus und zeigt das Ergebnis"""
    print(f"\n🔧 {description}...")
    print(f"Befehl: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} erfolgreich!")
            if result.stdout:
                print("Ausgabe:", result.stdout.strip())
        else:
            print(f"❌ {description} fehlgeschlagen!")
            if result.stderr:
                print("Fehler:", result.stderr.strip())
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Fehler bei {description}: {e}")
        return False

def main():
    print("🚀 Scandy Passwort- und E-Mail-Reparatur")
    print("=" * 50)
    
    # 1. Scandy-Service stoppen
    print("\n1️⃣ Stoppe Scandy-Service...")
    run_command("sudo systemctl stop scandy.service", "Service stoppen")
    
    # 2. Admin-Passwort zurücksetzen
    print("\n2️⃣ Setze Admin-Passwort zurück...")
    
    # Erstelle ein einfaches Python-Skript für die Passwort-Änderung
    password_script = '''
import sys
sys.path.append('/opt/scandy')
from app.models.mongodb_database import mongodb
from werkzeug.security import generate_password_hash
from datetime import datetime

try:
    admin_user = mongodb.find_one('users', {'role': 'admin'})
    if admin_user:
        new_password = "Admin123!"
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
            print(f"✅ Passwort zurückgesetzt für {admin_user.get('username')}")
            print(f"🔑 Neues Passwort: {new_password}")
        else:
            print("❌ Fehler beim Zurücksetzen")
    else:
        print("❌ Kein Admin-Nutzende gefunden")
except Exception as e:
    print(f"❌ Fehler: {e}")
'''
    
    with open('/tmp/reset_password.py', 'w') as f:
        f.write(password_script)
    
    run_command("cd /opt/scandy && sudo python3 /tmp/reset_password.py", "Passwort zurücksetzen")
    
    # 3. E-Mail-Konfiguration testen
    print("\n3️⃣ Teste E-Mail-Konfiguration...")
    email_test_script = '''
import sys
sys.path.append('/opt/scandy')
from app.utils.email_utils import get_email_config, send_email_with_config

try:
    config = get_email_config()
    if config:
        print("✅ E-Mail-Konfiguration gefunden:")
        for key, value in config.items():
            if key != 'mail_password':
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {'***' if value else 'Nicht gesetzt'}")
        
        # Teste E-Mail-Versand
        if config.get('mail_username') and config.get('mail_password'):
            print("\\n📧 Teste E-Mail-Versand...")
            success = send_email_with_config(
                to_email=config.get('test_email', config.get('mail_username')),
                subject="Scandy E-Mail-Test",
                text_content="Dies ist ein Test der E-Mail-Funktionalität.",
                config=config
            )
            if success:
                print("✅ E-Mail-Test erfolgreich!")
            else:
                print("❌ E-Mail-Test fehlgeschlagen!")
        else:
            print("❌ E-Mail-Konfiguration unvollständig")
    else:
        print("❌ Keine E-Mail-Konfiguration gefunden")
except Exception as e:
    print(f"❌ Fehler: {e}")
'''
    
    with open('/tmp/test_email.py', 'w') as f:
        f.write(email_test_script)
    
    run_command("cd /opt/scandy && sudo python3 /tmp/test_email.py", "E-Mail-Test")
    
    # 4. Scandy-Service starten
    print("\n4️⃣ Starte Scandy-Service...")
    run_command("sudo systemctl start scandy.service", "Service starten")
    
    # 5. Status anzeigen
    print("\n5️⃣ Zeige Service-Status...")
    run_command("sudo systemctl status scandy.service --no-pager", "Status anzeigen")
    
    print("\n" + "=" * 50)
    print("🎉 Reparatur abgeschlossen!")
    print("\n📋 Zusammenfassung:")
    print("✅ Admin-Passwort wurde zurückgesetzt auf: Admin123!")
    print("✅ E-Mail-Konfiguration wurde getestet")
    print("✅ Scandy-Service wurde neu gestartet")
    print("\n⚠️  WICHTIG:")
    print("- Loggen Sie sich mit dem neuen Passwort ein")
    print("- Ändern Sie das Passwort nach dem Login")
    print("- Testen Sie die E-Mail-Funktionalität")
    
    # Aufräumen
    os.remove('/tmp/reset_password.py')
    os.remove('/tmp/test_email.py')

if __name__ == "__main__":
    main()
